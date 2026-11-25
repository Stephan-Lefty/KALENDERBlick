#!/usr/bin/env python3
"""Legt ein Thunderbird-Profil mit erfundenen Terminen für drei Wochen an.

Zum Ausprobieren auf einem Rechner, auf dem keine echten Termine
liegen - etwa in einer frisch aufgesetzten virtuellen Maschine. Ohne
Termine bleiben alle Ansichten leer, und gerade die 14-Tage-Ansicht
sagt dann nichts über das Verhalten des Widgets aus.

    python3 testkalender.py [zielordner]

Läuft **eigenständig**: nur Python-Standardbibliothek, kein
KALENDERBlick, kein Thunderbird, keine Zusatzpakete. Deshalb lässt es
sich einzeln herunterladen:

    wget https://raw.githubusercontent.com/Stephan-Lefty/KALENDERBlick/main/werkzeuge/testkalender.py
    python3 testkalender.py

Danach in KALENDERBlick unter „Einstellungen → Kalenderquellen" auf
„Profilordner auswählen …" gehen und den angezeigten Pfad eintragen.
Mit „Wieder automatisch suchen" geht es zurück zum echten Profil.

**Alle Namen, Orte und Termine sind frei erfunden.** Nichts davon darf
aus einem echten Kalender stammen; Bildschirmfotos daraus landen
erfahrungsgemäß irgendwann öffentlich.
"""

import sqlite3
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
    ZONE = ZoneInfo("Europe/Berlin")
except Exception:                                    # pragma: no cover
    ZONE = timezone.utc

TZ_NAME = "/mozilla.org/20050126_1/Europe/Berlin"
FLAG_GANZTAGS = 8

SCHEMA = """
CREATE TABLE cal_events (
  cal_id TEXT, id TEXT, time_created INTEGER, last_modified INTEGER,
  title TEXT, priority INTEGER, privacy TEXT, ical_status TEXT,
  flags INTEGER, event_start INTEGER, event_start_tz TEXT,
  event_end INTEGER, event_end_tz TEXT, event_stamp INTEGER,
  alarm_last_ack INTEGER, recurrence_id INTEGER, recurrence_id_tz TEXT,
  offline_journal INTEGER);
CREATE TABLE cal_recurrence (
  item_id TEXT, cal_id TEXT, icalString TEXT, is_negative BOOLEAN);
CREATE TABLE cal_properties (
  item_id TEXT, cal_id TEXT, recurrence_id INTEGER, recurrence_id_tz TEXT,
  key TEXT, value BLOB);
CREATE TABLE cal_todos (cal_id TEXT, id TEXT, title TEXT);
"""


def _mikro(zeitpunkt: datetime, ortszeit: bool = True) -> int:
    """Wie Thunderbird speichert: Mikrosekunden seit 1970 in UTC."""
    if zeitpunkt.tzinfo is None:
        zeitpunkt = zeitpunkt.replace(tzinfo=ZONE if ortszeit else timezone.utc)
    return int(zeitpunkt.timestamp() * 1_000_000)


class Profil:
    def __init__(self, wurzel: Path):
        self.wurzel = wurzel
        self.profil = wurzel / ".thunderbird" / "test.default"
        (self.profil / "calendar-data").mkdir(parents=True)
        (wurzel / ".thunderbird" / "profiles.ini").write_text(
            "[Install0000000000000000]\n"
            "Default=test.default\n"
            "Locked=1\n\n"
            "[Profile0]\n"
            "Name=default\n"
            "IsRelative=1\n"
            "Path=test.default\n"
            "Default=1\n",
            encoding="utf-8")
        self.prefs: list[str] = []

    def kalender(self, kennung: str, name: str, farbe: str):
        self.prefs += [
            f'user_pref("calendar.registry.{kennung}.name", "{name}");',
            f'user_pref("calendar.registry.{kennung}.color", "{farbe}");',
            f'user_pref("calendar.registry.{kennung}.type", "storage");',
        ]
        verbindung = sqlite3.connect(
            self.profil / "calendar-data" / f"{kennung}.sqlite")
        verbindung.executescript(SCHEMA)
        verbindung.commit()
        return verbindung

    def fertig(self) -> None:
        (self.profil / "prefs.js").write_text(
            "// Mozilla User Preferences\n\n" + "\n".join(self.prefs) + "\n",
            encoding="utf-8")


def termin(verbindung, cal_id, kennung, titel, beginn, ende,
           ganztags=False, ort="") -> None:
    verbindung.execute(
        "INSERT INTO cal_events (cal_id, id, title, flags, event_start,"
        " event_start_tz, event_end, event_end_tz, privacy, ical_status)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (cal_id, kennung, titel, FLAG_GANZTAGS if ganztags else 0,
         _mikro(beginn, not ganztags), None if ganztags else TZ_NAME,
         _mikro(ende, not ganztags), None if ganztags else TZ_NAME,
         "PUBLIC", "CONFIRMED"))
    if ort:
        verbindung.execute(
            "INSERT INTO cal_properties (item_id, cal_id, key, value)"
            " VALUES (?,?,?,?)", (kennung, cal_id, "LOCATION", ort))
    verbindung.commit()


# --------------------------------------------------------------------
# Die erfundenen Termine. Über drei Wochen verteilt, mit mehreren pro
# Tag - damit auch die 14-Tage-Ansicht einen hohen Kasten ergibt.
# --------------------------------------------------------------------

ARBEIT = [
    (0, 9, 0, 10, 0, "Wochenbesprechung", "Besprechungsraum 2"),
    (0, 14, 30, 15, 30, "Angebot durchgehen", ""),
    (1, 8, 30, 9, 15, "Kurzabstimmung Technik", ""),
    (1, 11, 0, 12, 30, "Kundengespräch Nordbau", "Lindenstraße 14"),
    (2, 10, 0, 11, 0, "Lieferantentermin", ""),
    (3, 9, 0, 9, 45, "Monatszahlen ansehen", ""),
    (3, 16, 0, 17, 0, "Einweisung neue Kollegin", "Schulungsraum"),
    (4, 13, 0, 14, 0, "Planung kommende Woche", ""),
    (7, 9, 0, 10, 0, "Wochenbesprechung", "Besprechungsraum 2"),
    (7, 15, 0, 16, 30, "Werkstattbegehung", ""),
    (8, 10, 30, 12, 0, "Angebotspräsentation", "Lindenstraße 14"),
    (9, 14, 0, 15, 0, "Schulung Warenwirtschaft", ""),
    (10, 8, 45, 9, 30, "Abstimmung Versand", ""),
    (11, 11, 0, 12, 0, "Jahresgespräch", "Büro oben"),
    (14, 9, 0, 10, 0, "Wochenbesprechung", "Besprechungsraum 2"),
    (15, 13, 30, 15, 0, "Inventurvorbereitung", "Lager"),
    (16, 10, 0, 11, 30, "Messeplanung", ""),
    (17, 9, 30, 10, 15, "Rücksprache Einkauf", ""),
    (18, 14, 0, 16, 0, "Quartalsrunde", "Besprechungsraum 1"),
    (20, 11, 0, 12, 0, "Abschluss Projektphase", ""),
]

PRIVAT = [
    (0, 18, 30, 20, 0, "Sport", "Turnhalle am Park"),
    (2, 19, 0, 22, 0, "Kinoabend", "Lichtspiele"),
    (4, 17, 30, 19, 0, "Einkaufen für das Wochenende", ""),
    (5, 10, 0, 12, 0, "Fahrradtour", "Treffpunkt Brücke"),
    (6, 15, 0, 17, 0, "Kaffee bei Familie Weber", "Rosenweg 8"),
    (8, 18, 30, 20, 0, "Sport", "Turnhalle am Park"),
    (11, 19, 30, 21, 0, "Chorprobe", "Gemeindehaus"),
    (13, 11, 0, 13, 0, "Brunch", "Café Morgenrot"),
    (15, 18, 30, 20, 0, "Sport", "Turnhalle am Park"),
    (18, 19, 0, 21, 0, "Spieleabend", ""),
    (19, 9, 30, 11, 0, "Werkstatttermin Fahrrad", "Radhaus Süd"),
]

GANZTAGS = [
    (3, "Kassandra hat Geburtstag", ""),
    (6, "Flohmarkt", "Marktplatz"),
    (12, "Urlaubstag", ""),
    (13, "Urlaubstag", ""),
    (17, "Betriebsausflug", "Seepark"),
    (21, "Markus hat Geburtstag", ""),
]


def main() -> int:
    ziel = Path(sys.argv[1]) if len(sys.argv) > 1 else (
        Path.home() / "KALENDERBlick-Testkalender")
    if ziel.exists():
        print(f"Es gibt schon etwas unter {ziel}.\n"
              f"Bitte von Hand entfernen oder einen anderen Ort angeben:\n"
              f"    python3 {Path(sys.argv[0]).name} /pfad/zum/ordner",
              file=sys.stderr)
        return 1

    heute = date.today()
    p = Profil(ziel)

    arbeit = p.kalender("aaaa1111", "Arbeit", "#e66100")
    for nr, (tag, h1, m1, h2, m2, titel, ort) in enumerate(ARBEIT):
        wann = heute + timedelta(days=tag)
        termin(arbeit, "aaaa1111", f"a{nr}", titel,
               datetime.combine(wann, time(h1, m1)),
               datetime.combine(wann, time(h2, m2)), ort=ort)

    privat = p.kalender("bbbb2222", "Privat", "#3584e4")
    for nr, (tag, h1, m1, h2, m2, titel, ort) in enumerate(PRIVAT):
        wann = heute + timedelta(days=tag)
        termin(privat, "bbbb2222", f"p{nr}", titel,
               datetime.combine(wann, time(h1, m1)),
               datetime.combine(wann, time(h2, m2)), ort=ort)

    familie = p.kalender("cccc3333", "Familie", "#2ec27e")
    for nr, (tag, titel, ort) in enumerate(GANZTAGS):
        wann = heute + timedelta(days=tag)
        termin(familie, "cccc3333", f"g{nr}", titel,
               datetime.combine(wann, time(0, 0)),
               datetime.combine(wann + timedelta(days=1), time(0, 0)),
               ganztags=True, ort=ort)

    p.fertig()

    anzahl = len(ARBEIT) + len(PRIVAT) + len(GANZTAGS)
    print(f"Angelegt: {ziel}")
    print(f"Profilordner: {p.profil}")
    print(f"3 Kalender, {anzahl} Termine von heute bis "
          f"{heute + timedelta(days=21):%d.%m.%Y}")
    print()
    print("In KALENDERBlick unter „Einstellungen → Kalenderquellen“ auf")
    print("„Profilordner auswählen …“ gehen und diesen Pfad eintragen:")
    print(f"    {p.profil}")
    print()
    print("Zurück zum echten Profil: „Wieder automatisch suchen“.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
