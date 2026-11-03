"""Baut eine Evolution-Ablage nach, wie sie auf der Platte aussieht."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class EvolutionAblage:
    def __init__(self, wurzel: Path):
        self.wurzel = wurzel
        self.kalender = wurzel / ".local" / "share" / "evolution" / "calendar"
        self.quellen = wurzel / ".config" / "evolution" / "sources"
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
