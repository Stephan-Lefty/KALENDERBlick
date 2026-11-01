"""Kommandozeile von KALENDERBlick."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from . import NAME, __version__
from . import config as konfig_modul
from . import paths, thunderbird
from .config import KonfigFehler
from .modell import kurzfassung, nach_tagen, naechster, tagesueberschrift

AUFRUF = "kalenderblick"


def _schreib(text: str = "") -> None:
    print(text, flush=True)


def _profil(args) -> Path:
    e = konfig_modul.laden()
    return thunderbird.waehle_profil(getattr(args, "profil", "") or e.profil)


# ----------------------------------------------------------------------

def befehl_pruefen(args) -> int:
    """Zeigt, was vorgefunden wurde - der erste Befehl auf einem neuen Rechner."""
    _schreib(f"{NAME} {__version__}")
    _schreib(f"Python {sys.version.split()[0]}")
    try:
        from dateutil import __version__ as dv
        _schreib(f"dateutil {dv}")
    except ImportError:
        _schreib("dateutil FEHLT - Wiederholungen können nicht berechnet werden")
    _schreib()

    vorschlaege = thunderbird.profil_vorschlaege()
    if not vorschlaege:
        _schreib("Kein Thunderbird-Profil gefunden. Gesucht wurde in:")
        for wurzel in thunderbird.profil_wurzeln():
            _schreib(f"  {wurzel}")
        return 1

    _schreib("Gefundene Profile:")
    for pfad, dateien, termine, bevorzugt in vorschlaege:
        merkmale = [f"{dateien} Kalenderdateien", f"{termine} Termine"]
        if bevorzugt:
            merkmale.append("Startprofil von Thunderbird")
        _schreib(f"  {pfad}")
        _schreib("      " + ", ".join(merkmale))
    _schreib()

    profil = _profil(args)
    _schreib(f"Verwendet wird: {profil}")
    _schreib("Anderes gewünscht:  kalenderblick --profil <PFAD> ...")
    _schreib("Dauerhaft merken:   kalenderblick einstellungen --profil <PFAD>")
    _schreib()

    dateien = thunderbird.kalenderdateien(profil)
    if not dateien:
        _schreib("In diesem Profil liegen keine Kalenderdateien.")
        return 1

    for datei in dateien:
        groesse = datei.stat().st_size // 1024
        stand = datetime.fromtimestamp(datei.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
        _schreib(f"{datei.name}  ({groesse} kB, zuletzt geschrieben {stand})")
        try:
            kopie = thunderbird._kopiere(datei)
            verbindung = sqlite3.connect(f"file:{kopie}?mode=ro", uri=True, timeout=5)
            try:
                tabellen = [z[0] for z in verbindung.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
                _schreib("   Tabellen: " + ", ".join(tabellen))
                for tabelle in ("cal_events", "cal_recurrence", "cal_properties"):
                    if tabelle not in tabellen:
                        _schreib(f"   {tabelle}: FEHLT")
                        continue
                    spalten = sorted(thunderbird._spalten(verbindung, tabelle))
                    menge = verbindung.execute(
                        f"SELECT count(*) FROM {tabelle}").fetchone()[0]
                    _schreib(f"   {tabelle}: {menge} Zeilen")
                    _schreib("      Spalten: " + ", ".join(spalten))
                verteilung = verbindung.execute(
                    "SELECT cal_id, count(*) FROM cal_events GROUP BY cal_id"
                ).fetchall() if "cal_events" in tabellen else []
                if verteilung:
                    _schreib("   Enthaltene Kalender:")
                    for kennung, menge in verteilung:
                        _schreib(f"      {kennung}  -  {menge} Termine")
                if "cal_recurrence" in tabellen and args.beispiele:
                    beispiele = verbindung.execute(
                        "SELECT * FROM cal_recurrence LIMIT 3").fetchall()
                    for zeile in beispiele:
                        _schreib(f"      Beispiel: {tuple(zeile)}")
            finally:
                verbindung.close()
        except sqlite3.Error as fehler:
            _schreib(f"   Nicht lesbar: {fehler}")
        _schreib()

    _schreib("Wenn hier cal_recurrence ohne Spalte icalString auftaucht, sag Bescheid -")
    _schreib("dann legt deine Thunderbird-Fassung Wiederholungen anders ab.")
    return 0


def befehl_kalender(args) -> int:
    """Welche Kalender gibt es, und wie oft wird abgeglichen?"""
    profil = _profil(args)
    kalender = thunderbird.lies_kalender(profil)
    if not kalender:
        _schreib("Keine Kalender gefunden.")
        return 1

    jetzt = datetime.now()
    for eintrag in sorted(kalender, key=lambda k: (not k.ist_fern, k.name.lower())):
        kennzeichen = []
        if eintrag.abgeschaltet:
            kennzeichen.append("abgeschaltet")
        if eintrag.nur_lesen:
            kennzeichen.append("nur lesen")
        zusatz = ("  [" + ", ".join(kennzeichen) + "]") if kennzeichen else ""
        _schreib(f"{eintrag.name or eintrag.kennung}{zusatz}")
        _schreib(f"   Art:      {eintrag.art}")
        _schreib(f"   {eintrag.abholtext()}")
        if eintrag.zuletzt_geschrieben:
            alter = jetzt - eintrag.zuletzt_geschrieben
            minuten = int(alter.total_seconds() // 60)
            wann = eintrag.zuletzt_geschrieben.strftime("%d.%m.%Y %H:%M")
            if minuten < 90:
                _schreib(f"   Zuletzt geschrieben: {wann}  (vor {minuten} Minuten)")
            else:
                _schreib(f"   Zuletzt geschrieben: {wann}  "
                         f"(vor {minuten // 60} Stunden)")
        _schreib(f"   Kennung:  {eintrag.kennung}")
        _schreib()

    _schreib("Hinweis: „zuletzt geschrieben\" ist der Zeitpunkt, an dem Thunderbird")
    _schreib("zuletzt etwas in die Datei geschrieben hat - also der letzte Abgleich,")
    _schreib("bei dem sich auch wirklich etwas geändert hat.")
    return 0


def befehl_liste(args) -> int:
    e = konfig_modul.laden()
    profil = _profil(args)
    termine = thunderbird.lies_termine(
        profil,
        tage_voraus=args.tage or e.tage_voraus,
        tage_zurueck=e.tage_zurueck,
        versteckt=e.versteckte_kalender,
    )
    if not args.alles and not e.vergangene_zeigen:
        jetzt = datetime.now()
        termine = [t for t in termine if not t.ist_vorbei(jetzt)]

    if not termine:
        _schreib("Keine Termine im gewählten Zeitraum.")
        return 0

    for tag, eintraege in nach_tagen(termine):
        _schreib(tagesueberschrift(tag).upper())
        for termin in eintraege:
            zeit = termin.zeitangabe()
            zeile = f"  {zeit:<16}{termin.titel}"
            if args.ausfuehrlich:
                zeile += f"   [{termin.kalender_name}]"
                if termin.ort:
                    zeile += f"   {termin.ort}"
            _schreib(zeile)
        _schreib()
    return 0


def befehl_naechster(args) -> int:
    e = konfig_modul.laden()
    profil = _profil(args)
    termine = thunderbird.lies_termine(
        profil, tage_voraus=e.tage_voraus, versteckt=e.versteckte_kalender)
    _schreib(kurzfassung(naechster(termine)))
    return 0


def befehl_einstellungen(args) -> int:
    e = konfig_modul.laden()
    if args.tage_voraus:
        e.tage_voraus = args.tage_voraus
    if args.aktualisierung:
        e.aktualisierung_minuten = args.aktualisierung
    if args.profil:
        e.profil = args.profil
    if args.verstecken:
        for kennung in args.verstecken:
            if kennung not in e.versteckte_kalender:
                e.versteckte_kalender.append(kennung)
    if args.zeigen:
        e.versteckte_kalender = [k for k in e.versteckte_kalender if k not in args.zeigen]
    try:
        e.pruefe()
    except KonfigFehler as fehler:
        _schreib(str(fehler))
        return 2
    e.speichern()

    _schreib(f"Einstellungen: {paths.konfig_datei()}")
    _schreib(f"  Profil:          {e.profil or '(selbst suchen)'}")
    _schreib(f"  Vorausblick:     {e.tage_voraus} Tage")
    _schreib(f"  Aktualisierung:  alle {e.aktualisierung_minuten} Minuten")
    _schreib(f"  Versteckt:       {', '.join(e.versteckte_kalender) or '(nichts)'}")
    return 0


def befehl_fenster(args=None) -> int:
    from .gui import starte_fenster
    return starte_fenster()


def befehl_start(args=None) -> int:
    from .gui import starte_alles
    return starte_alles()


# ----------------------------------------------------------------------

def baue_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=AUFRUF,
        description=f"{NAME} - zeigt Thunderbirds Kalender auf dem Schreibtisch "
                    "und in der Kontrollleiste.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Zuerst ausprobieren:
  {AUFRUF} pruefen        was wurde gefunden
  {AUFRUF} kalender       welche Kalender, wie oft abgeglichen
  {AUFRUF} liste          die nächsten Termine
""",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    p.add_argument("--profil", default="", help="Thunderbird-Profil von Hand angeben")
    unter = p.add_subparsers(dest="befehl", metavar="BEFEHL")

    s = unter.add_parser("pruefen", help="Profile, Dateien und Schema zeigen")
    s.add_argument("--beispiele", action="store_true",
                   help="auch ein paar Zeilen aus cal_recurrence")
    s.set_defaults(funktion=befehl_pruefen)

    s = unter.add_parser("kalender", help="Kalender mit Art und Abholfrequenz")
    s.set_defaults(funktion=befehl_kalender)

    s = unter.add_parser("liste", help="kommende Termine als Text")
    s.add_argument("--tage", type=int, default=0, help="Vorausblick in Tagen")
    s.add_argument("--alles", action="store_true", help="auch vergangene Termine")
    s.add_argument("--ausfuehrlich", action="store_true", help="mit Kalender und Ort")
    s.set_defaults(funktion=befehl_liste)

    s = unter.add_parser("naechster", help="nur der nächste Termin, eine Zeile")
    s.set_defaults(funktion=befehl_naechster)

    s = unter.add_parser("einstellungen", help="Einstellungen ansehen und ändern")
    s.add_argument("--tage-voraus", type=int, dest="tage_voraus")
    s.add_argument("--aktualisierung", type=int, help="Minuten zwischen zwei Blicken")
    s.add_argument("--verstecken", nargs="+", help="Kennungen von Kalendern")
    s.add_argument("--zeigen", nargs="+", help="Kennungen wieder einblenden")
    s.set_defaults(funktion=befehl_einstellungen)

    s = unter.add_parser("fenster", help="Fenster öffnen (braucht PyQt6)")
    s.set_defaults(funktion=befehl_fenster)

    s = unter.add_parser("start", help="Symbol und Schreibtischfenster starten")
    s.set_defaults(funktion=befehl_start)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = baue_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "funktion", None):
        parser.print_help()
        return 0
    try:
        return args.funktion(args)
    except KeyboardInterrupt:
        _schreib("\nAbgebrochen.")
        return 130
    except thunderbird.ThunderbirdFehler as fehler:
        _schreib(str(fehler))
        return 1
    except KonfigFehler as fehler:
        _schreib(str(fehler))
        return 2
