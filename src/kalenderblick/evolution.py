"""Evolutions Kalenderdaten lesen - ohne Evolution zu stören.

Der Evolution Data Server legt jeden Kalender als iCalendar-Datei ab:

    ~/.local/share/evolution/calendar/<kennung>/calendar.ics
    ~/.config/evolution/sources/<kennung>.source     Name, Farbe, Art

Entfernte Kalender - CalDAV, Google, Nextcloud, abonnierte Adressen -
liegen dagegen *nicht* dort, sondern als SQLite-Zwischenspeicher:

    ~/.cache/evolution/calendar/<kennung>/cache.db

Beide Orte werden gelesen. Damit erreicht man alles, was in Evolution
eingebunden ist, ohne einen einzigen dieser Anbieter selbst zu kennen:
Evolution hat die Termine bereits örtlich abgelegt.

Gelesen wird ausschließlich, geschrieben nie - wie bei Thunderbird.
"""

from __future__ import annotations

import configparser
import os
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

from . import ical
from .ical import BibliothekFehlt  # noqa: F401 - für bestehende Importe
from .modell import Termin


class EvolutionFehler(Exception):
    """Daten nicht auffindbar oder unlesbar."""


# ----------------------------------------------------------------------
#  Ablageorte
# ----------------------------------------------------------------------

def _basis(umgebungsname: str, vorgabe: str) -> Path:
    return Path(os.environ.get(umgebungsname) or (Path.home() / vorgabe))


def kalender_ordner() -> list[Path]:
    """Die Orte, an denen Evolution seine Kalender ablegt.

    Neben der gewöhnlichen Installation auch die abgeschottete
    Flatpak-Fassung, die unter einem eigenen Zweig liegt.
    """
    orte = [
        _basis("XDG_DATA_HOME", ".local/share") / "evolution" / "calendar",
        Path.home() / ".var" / "app" / "org.gnome.Evolution" / "data"
        / "evolution" / "calendar",
    ]
    return [o for o in orte if o.is_dir()]


def quellen_ordner() -> list[Path]:
    orte = [
        _basis("XDG_CONFIG_HOME", ".config") / "evolution" / "sources",
        Path.home() / ".var" / "app" / "org.gnome.Evolution" / "config"
        / "evolution" / "sources",
    ]
    return [o for o in orte if o.is_dir()]


def cache_ordner() -> list[Path]:
    """Wo Evolution entfernte Kalender zwischenspeichert.

    Entfernte Kalender landen nicht unter den Daten, sondern im
    Zwischenspeicher - als SQLite statt als iCalendar-Datei. Ohne
    diesen Ort blieben Google-, Nextcloud- und CalDAV-Kalender
    unsichtbar, obwohl Evolution sie längst geholt hat.
    """
    orte = [
        _basis("XDG_CACHE_HOME", ".cache") / "evolution" / "calendar",
        Path.home() / ".var" / "app" / "org.gnome.Evolution" / "cache"
        / "evolution" / "calendar",
    ]
    return [o for o in orte if o.is_dir()]


def cachedateien() -> list[Path]:
    dateien: list[Path] = []
    for ordner in cache_ordner():
        dateien += sorted(ordner.glob("*/cache.db"))
    return dateien


def _kopiere(datei: Path) -> Path:
    """Kopie in einem eigenen Ordner - wie bei Thunderbird, aus
    demselben Grund: Der laufende Dienst hält die Datei offen, und
    zwei gleichzeitige Lesevorgänge dürfen sich nicht überschreiben."""
    from . import paths
    paths.lege_ordner_an()
    eigener = Path(tempfile.mkdtemp(prefix="ev-", dir=paths.arbeits_ordner()))
    ziel = eigener / datei.name
    shutil.copy2(datei, ziel)
    for anhang in ("-wal", "-shm"):
        begleiter = datei.with_name(datei.name + anhang)
        if begleiter.exists():
            shutil.copy2(begleiter, ziel.with_name(ziel.name + anhang))
    return ziel


def _cache_als_ical(datei: Path) -> str:
    """Den Zwischenspeicher in einen iCalendar-Text umschreiben.

    In `ECacheObjects` steht je Zeile ein vollständiger VEVENT, aber
    ohne umgebendes VCALENDAR - das muss hier ergänzt werden, sonst
    versteht es kein Parser. Die Zeitzonendefinitionen stehen in einer
    eigenen Tabelle und gehören mit vorn hinein, sonst lassen sich
    Zeiten mit TZID nicht auflösen.
    """
    kopie = None
    try:
        verbindung = sqlite3.connect(f"file:{datei}?mode=ro", uri=True, timeout=0)
    except sqlite3.Error:
        kopie = _kopiere(datei)
        verbindung = sqlite3.connect(f"file:{kopie}?mode=ro", uri=True, timeout=0)

    teile = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//KALENDERBlick//Cache//DE"]
    try:
        try:
            for (zone,) in verbindung.execute("SELECT zone FROM timezones"):
                if zone:
                    teile.append(zone.strip())
        except sqlite3.Error:
            pass        # ältere Fassungen ohne diese Tabelle
        for (obj,) in verbindung.execute("SELECT ECacheOBJ FROM ECacheObjects"):
            if obj:
                teile.append(obj.strip())
    finally:
        verbindung.close()
        if kopie is not None:
            shutil.rmtree(kopie.parent, ignore_errors=True)

    teile.append("END:VCALENDAR")
    return "\r\n".join(teile)


def vorhanden() -> bool:
    """Ob überhaupt Evolution-Kalender zu finden sind."""
    return bool(kalenderdateien()) or bool(cachedateien())


def kalenderdateien() -> list[Path]:
    dateien: list[Path] = []
    for ordner in kalender_ordner():
        dateien += sorted(ordner.glob("*/calendar.ics"))
    return dateien


# ----------------------------------------------------------------------
#  Namen, Farben, Art aus den .source-Dateien
# ----------------------------------------------------------------------

@dataclass
class Kalender:
    kennung: str
    name: str = ""
    farbe: str = "#3584e4"
    art: str = "local"
    abgeschaltet: bool = False
    datei: Path | None = None
    cache: Path | None = None       # entfernte Kalender: SQLite statt .ics
    anzahl: int = 0
    zuletzt_geschrieben: datetime | None = None

    @property
    def ist_fern(self) -> bool:
        return self.art not in ("local", "contacts", "weather")

    def abholtext(self) -> str:
        if not self.ist_fern:
            return "örtlich gespeichert, kein Abgleich nötig"
        return "Abholung: von Evolution gesteuert"


def lies_quellen() -> dict[str, Kalender]:
    """Die .source-Dateien auswerten - sie sind im INI-Format gehalten."""
    kalender: dict[str, Kalender] = {}
    for ordner in quellen_ordner():
        for datei in sorted(ordner.glob("*.source")):
            leser = configparser.ConfigParser()
            leser.optionxform = str
            try:
                leser.read(datei, encoding="utf-8")
            except (OSError, configparser.Error):
                continue
            if not leser.has_section("Calendar"):
                continue      # Adressbuch, Aufgabenliste, Konto - nicht unser Fall

            eintrag = Kalender(kennung=datei.stem)
            if leser.has_section("Data Source"):
                quelle = leser["Data Source"]
                eintrag.name = quelle.get("DisplayName", "") or datei.stem
                eintrag.abgeschaltet = quelle.get("Enabled", "true").lower() == "false"
            kal = leser["Calendar"]
            eintrag.art = kal.get("BackendName", "local")
            farbe = kal.get("Color", "").strip()
            if farbe.startswith("#"):
                eintrag.farbe = farbe
            kalender[eintrag.kennung] = eintrag
    return kalender


# Evolutions eingebaute Kalender haben keine .source-Datei - ihr Name
# steht allein im Data Server, den wir nicht befragen (das zöge die
# GObject-Bindings als Abhängigkeit nach). Ohne diese Zuordnung hieße
# der Standardkalender "(ohne Namen, system)" statt "Persönlich", so
# wie Evolution selbst ihn zeigt.
EINGEBAUTE_NAMEN = {
    "system": "Persönlich",
}


def lies_kalender() -> list[Kalender]:
    """Alle Kalender mit Name, Farbe, Art und Ablageort.

    Örtliche Kalender liegen als iCalendar-Datei, entfernte als
    SQLite-Zwischenspeicher an einem ganz anderen Ort - beide gehören
    in dieselbe Liste.
    """
    quellen = lies_quellen()
    ergebnis: list[Kalender] = []

    def _eintrag(kennung: str) -> Kalender:
        return quellen.get(kennung) or Kalender(
            kennung=kennung,
            name=EINGEBAUTE_NAMEN.get(kennung, f"(ohne Namen, {kennung[:8]})"))

    for datei in kalenderdateien():
        eintrag = _eintrag(datei.parent.name)
        eintrag.datei = datei
        try:
            eintrag.zuletzt_geschrieben = datetime.fromtimestamp(datei.stat().st_mtime)
        except OSError:
            pass
        try:
            eintrag.anzahl = ical.zaehle_termine(datei)
        except BibliothekFehlt:
            raise
        except Exception:
            eintrag.anzahl = 0
        ergebnis.append(eintrag)

    gesehen = {k.kennung for k in ergebnis}
    for datei in cachedateien():
        kennung = datei.parent.name
        if kennung in gesehen:
            continue        # derselbe Kalender hat beides - die Datei gewinnt
        eintrag = _eintrag(kennung)
        eintrag.cache = datei
        try:
            eintrag.zuletzt_geschrieben = datetime.fromtimestamp(datei.stat().st_mtime)
        except OSError:
            pass
        try:
            verbindung = sqlite3.connect(f"file:{datei}?mode=ro", uri=True, timeout=0)
            try:
                eintrag.anzahl = verbindung.execute(
                    "SELECT count(*) FROM ECacheObjects").fetchone()[0]
            finally:
                verbindung.close()
        except sqlite3.Error:
            eintrag.anzahl = 0
        ergebnis.append(eintrag)

    return ergebnis


# ----------------------------------------------------------------------
#  Termine lesen
# ----------------------------------------------------------------------

def lies_termine(tage_voraus: int = 14, tage_zurueck: int = 0,
                 versteckt: list[str] | None = None) -> list[Termin]:
    versteckt = versteckt or []
    heute = date.today()
    von = datetime.combine(heute - timedelta(days=tage_zurueck), time(0, 0))
    bis = datetime.combine(heute + timedelta(days=tage_voraus), time(23, 59, 59))

    alle: list[Termin] = []
    for kalender in lies_kalender():
        if kalender.abgeschaltet or kalender.kennung in versteckt:
            continue
        try:
            if kalender.datei is not None:
                daten = ical.oeffne_datei(kalender.datei)
            elif kalender.cache is not None:
                daten = ical.oeffne_text(_cache_als_ical(kalender.cache))
            else:
                continue
        except BibliothekFehlt:
            raise
        except (ical.ICalFehler, sqlite3.Error, OSError):
            continue
        alle += ical.termine_aus(daten, kalender.kennung, kalender.name,
                                 kalender.farbe, von, bis)

    gefiltert = [t for t in alle if von <= t.beginn <= bis]
    gefiltert.sort(key=lambda t: (t.beginn, not t.ganztags, t.titel))
    return gefiltert
