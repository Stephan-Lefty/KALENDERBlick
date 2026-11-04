"""Baut eine Evolution-Ablage nach, wie sie auf der Platte aussieht.

Zwei Ablageorte, weil Evolution zwei benutzt: örtliche Kalender als
iCalendar-Datei unter den Daten, entfernte als SQLite-Zwischenspeicher
unter dem Cache. Beide Formen wurden an Evolution 3.60.2 abgeglichen.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path


class EvolutionAblage:
    def __init__(self, wurzel: Path):
        self.wurzel = wurzel
        self.kalender = wurzel / ".local" / "share" / "evolution" / "calendar"
        self.quellen = wurzel / ".config" / "evolution" / "sources"
        self.cache = wurzel / ".cache" / "evolution" / "calendar"
        self.kalender.mkdir(parents=True, exist_ok=True)
        self.quellen.mkdir(parents=True, exist_ok=True)

    def lege_kalender_an(self, kennung: str, name: str, farbe: str = "#becedd",
                         art: str = "local", abgeschaltet: bool = False) -> Path:
        """Erzeugt die .source-Datei und den Kalenderordner."""
        (self.quellen / f"{kennung}.source").write_text(
            "[Data Source]\n"
            f"DisplayName={name}\n"
            f"Enabled={'false' if abgeschaltet else 'true'}\n"
            "Parent=local-stub\n"
            "\n"
            "[Calendar]\n"
            f"BackendName={art}\n"
            f"Color={farbe}\n"
            "Selected=true\n",
            encoding="utf-8",
        )
        ordner = self.kalender / kennung
        ordner.mkdir(parents=True, exist_ok=True)
        datei = ordner / "calendar.ics"
        if not datei.exists():
            datei.write_text(
                "BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Test//DE\nEND:VCALENDAR\n",
                encoding="utf-8")
        return datei

    def termin(self, kennung: str, uid: str, titel: str,
               beginn: datetime, ende: datetime, ort: str = "",
               ganztags: bool = False, rrule: str | None = None,
               exdate: str | None = None) -> None:
        datei = self.kalender / kennung / "calendar.ics"
        inhalt = datei.read_text(encoding="utf-8")

        if ganztags:
            zeilen = [
                f"DTSTART;VALUE=DATE:{beginn.strftime('%Y%m%d')}",
                f"DTEND;VALUE=DATE:{ende.strftime('%Y%m%d')}",
            ]
        else:
            zeilen = [
                f"DTSTART:{beginn.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{ende.strftime('%Y%m%dT%H%M%S')}",
            ]
        if rrule:
            zeilen.append(f"RRULE:{rrule}")
        if exdate:
            zeilen.append(f"EXDATE:{exdate}")
        if ort:
            zeilen.append(f"LOCATION:{ort}")

        eintrag = (
            "BEGIN:VEVENT\n"
            f"UID:{uid}\n"
            f"SUMMARY:{titel}\n"
            + "\n".join(zeilen) + "\n"
            "END:VEVENT\n"
        )
        datei.write_text(
            inhalt.replace("END:VCALENDAR", eintrag + "END:VCALENDAR"),
            encoding="utf-8")

    def lege_fernkalender_an(self, kennung: str, name: str,
                             farbe: str = "#2ec27e", art: str = "caldav",
                             abgeschaltet: bool = False) -> Path:
        """Entfernter Kalender: .source wie sonst, Termine aber in einer
        cache.db unter ~/.cache - so legt Evolution CalDAV, Google und
        abonnierte Adressen ab."""
        self.lege_kalender_an(kennung, name, farbe, art, abgeschaltet)
        # Die .ics-Datei gibt es bei entfernten Kalendern nicht
        (self.kalender / kennung / "calendar.ics").unlink(missing_ok=True)
        (self.kalender / kennung).rmdir()

        ordner = self.cache / kennung
        ordner.mkdir(parents=True, exist_ok=True)
        db = ordner / "cache.db"
        with sqlite3.connect(db) as c:
            c.execute("CREATE TABLE IF NOT EXISTS ECacheObjects ("
                      "ECacheUID TEXT PRIMARY KEY, ECacheREV TEXT, "
                      "ECacheOBJ TEXT, ECacheState INTEGER)")
            c.execute("CREATE TABLE IF NOT EXISTS timezones ("
                      "tzid TEXT PRIMARY KEY, zone TEXT, refs INTEGER)")
        return db

    def fern_termin(self, kennung: str, uid: str, titel: str,
                    beginn: datetime, ende: datetime, ort: str = "",
                    ganztags: bool = False) -> None:
        """Ein Termin im Zwischenspeicher - als nackter VEVENT ohne
        VCALENDAR-Hülle, genau wie Evolution ihn dort ablegt."""
        if ganztags:
            zeiten = (f"DTSTART;VALUE=DATE:{beginn:%Y%m%d}\r\n"
                      f"DTEND;VALUE=DATE:{ende:%Y%m%d}")
        else:
            zeiten = (f"DTSTART:{beginn:%Y%m%dT%H%M%S}\r\n"
                      f"DTEND:{ende:%Y%m%dT%H%M%S}")
        teile = ["BEGIN:VEVENT", f"UID:{uid}", f"SUMMARY:{titel}", zeiten]
        if ort:
            teile.append(f"LOCATION:{ort}")
        teile.append("END:VEVENT")
        with sqlite3.connect(self.cache / kennung / "cache.db") as c:
            c.execute("INSERT OR REPLACE INTO ECacheObjects "
                      "(ECacheUID, ECacheREV, ECacheOBJ, ECacheState) "
                      "VALUES (?, ?, ?, 0)", (uid, "1", "\r\n".join(teile)))

    def lege_goa_kalender_an(self, kennung: str, name: str, konto: str,
                             farbe: str = "#3584e4") -> Path:
        """Ein Kalender aus den GNOME Online-Konten.

        Der Data Server kennt kein eigenes Google-Backend - solche
        Kalender laufen über CalDAV, GOA steuert nur die Zugangsdaten
        bei (module-credentials-goa.so). In der .source-Datei steht
        dafür ein zusätzlicher Abschnitt, der uns nicht stören darf.
        """
        self.lege_fernkalender_an(kennung, name, farbe, art="caldav")
        datei = self.quellen / f"{kennung}.source"
        datei.write_text(
            datei.read_text(encoding="utf-8")
            + f"\n[GNOME Online Accounts]\nId={konto}\nCalendarEnabled=true\n",
            encoding="utf-8")
        return datei
