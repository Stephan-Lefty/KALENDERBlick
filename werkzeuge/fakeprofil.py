"""Baut ein Thunderbird-Profil mit erfundenen Terminen für die
Bildschirmfotos der Anleitung.

    python3 werkzeuge/fakeprofil.py [zielordner]

Danach in den Einstellungen unter „Kalenderquellen" den Profilordner
darauf zeigen lassen (…/.thunderbird/abc123.default), die Bilder
aufnehmen und hinterher „Wieder automatisch suchen" drücken.

Alle Namen, Orte und Termine sind frei erfunden. Nichts davon darf aus
Stephans echtem Kalender stammen - die Bilder liegen später öffentlich
im Repo.

Die Termine liegen relativ zu heute, damit alle Ansichten etwas zu
zeigen haben: heute, morgen, über die Woche verteilt und bis in die
zweite Woche hinein.
"""

import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
from hilfe import Profil, termin

ZIEL = Path(sys.argv[1]) if len(sys.argv) > 1 else (
    Path.home() / "KALENDERBlick-Fakeprofil")
if ZIEL.exists():
    raise SystemExit(f"Es gibt schon etwas unter {ZIEL} - bitte von Hand "
                     "entfernen oder einen anderen Ort angeben.")
ZIEL.mkdir(parents=True)

p = Profil(ZIEL)
heute = date.today()


def _tag(versatz, werktag=False):
    """Tag relativ zu heute. Mit werktag=True wird auf den nächsten
    Montag bis Freitag vorgerückt - eine Schulung am Sonntag würde auf
    den Bildschirmfotos sofort als erfunden auffallen."""
    tag = heute + timedelta(days=versatz)
    while werktag and tag.weekday() >= 5:
        tag += timedelta(days=1)
    return tag


def t(tag_versatz, stunde, minute=0, werktag=False):
    return datetime.combine(_tag(tag_versatz, werktag), time(stunde, minute))


def ganztag(tag_versatz, werktag=False):
    return datetime.combine(_tag(tag_versatz, werktag), time(0, 0))


# ----------------------------------------------------------------------
#  Vier Kalender, wie sie typisch nebeneinander stehen
# ----------------------------------------------------------------------

privat = p.kalender("aaaa1111", "Privat", farbe="#3584e4")
arbeit = p.kalender("bbbb2222", "Arbeit", farbe="#e66100", art="caldav")
familie = p.kalender("cccc3333", "Familie", farbe="#2ec27e")
feier = p.kalender("dddd4444", "Feiertage", farbe="#9141ac",
                   art="ics", abholung=1440)

# --- heute ------------------------------------------------------------
termin(arbeit, "bbbb2222", "e01", "Wochenbesprechung",
       t(0, 9, 30), t(0, 10, 30), ort="Besprechungsraum 2")
termin(privat, "aaaa1111", "e02", "Zahnarzt Dr. Berger",
       t(0, 14, 0), t(0, 15, 0), ort="Lindenallee 12")
termin(familie, "cccc3333", "e03", "Lena von der Musikschule abholen",
       t(0, 17, 15), t(0, 17, 45))

# --- morgen -----------------------------------------------------------
termin(familie, "cccc3333", "e04", "Opa hat Geburtstag",
       ganztag(1), ganztag(1), ganztags=True)
termin(arbeit, "bbbb2222", "e05", "Angebot Firma Sonnental abgeben",
       t(1, 11, 0, werktag=True), t(1, 11, 30, werktag=True))

# --- diese Woche ------------------------------------------------------
termin(privat, "aaaa1111", "e06", "Schwimmbad mit Jonas",
       t(2, 16, 0), t(2, 18, 0), ort="Stadtbad")
termin(arbeit, "bbbb2222", "e07", "Schulung Datenschutz",
       t(3, 9, 0, werktag=True), t(3, 16, 0, werktag=True),
       ort="Haus der Wirtschaft")
termin(privat, "aaaa1111", "e08", "Autowerkstatt: Inspektion",
       t(6, 8, 0, werktag=True), t(6, 9, 0, werktag=True),
       ort="Werkstatt Keller")
termin(familie, "cccc3333", "e09", "Elternabend Grundschule",
       t(5, 19, 30, werktag=True), t(5, 21, 0, werktag=True))

# --- nächste Woche ----------------------------------------------------
termin(feier, "dddd4444", "e10", "Brückentag",
       ganztag(7, werktag=True), ganztag(7, werktag=True), ganztags=True)
termin(privat, "aaaa1111", "e11", "Kinoabend mit Martina",
       t(8, 20, 0), t(8, 22, 30), ort="Filmpalast")
termin(arbeit, "bbbb2222", "e12", "Quartalsgespräch",
       t(9, 10, 0, werktag=True), t(9, 11, 30, werktag=True),
       ort="Büro 1. Stock")
termin(familie, "cccc3333", "e13", "Besuch bei Tante Hilde",
       ganztag(11), ganztag(11), ganztags=True)
termin(privat, "aaaa1111", "e14", "Rückengymnastik",
       t(12, 18, 0), t(12, 19, 0),
       rrule="FREQ=WEEKLY;BYDAY=TU")
termin(arbeit, "bbbb2222", "e15", "Messe Hannover",
       ganztag(13, werktag=True), ganztag(14, werktag=True), ganztags=True)

p.schreibe_prefs()

print(f"  Profil angelegt: {ZIEL}")
print(f"  Thunderbird-Ordner: {p.profil}")
print(f"  Kalender: 4   Termine: 15")
