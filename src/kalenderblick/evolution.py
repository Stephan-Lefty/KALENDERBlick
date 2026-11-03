"""Evolutions Kalenderdaten lesen - ohne Evolution zu stören.

Der Evolution Data Server legt jeden Kalender als iCalendar-Datei ab:

    ~/.local/share/evolution/calendar/<kennung>/calendar.ics
    ~/.config/evolution/sources/<kennung>.source     Name, Farbe, Art

Damit erreicht man auch alles, was in Evolution eingebunden ist -
Google, Nextcloud, CalDAV-Konten -, ohne einen einzigen dieser Anbieter
selbst zu kennen: Evolution hat die Termine bereits örtlich abgelegt.

Gelesen wird ausschließlich, geschrieben nie - wie bei Thunderbird.
"""

from __future__ import annotations

import configparser
import os
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


def vorhanden() -> bool:
    """Ob überhaupt Evolution-Kalender zu finden sind."""
    return bool(kalenderdateien())


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


def lies_kalender() -> list[Kalender]:
    """Alle Kalender mit Name, Farbe, Art und Datei."""
    quellen = lies_quellen()
    ergebnis: list[Kalender] = []

    for datei in kalenderdateien():
        kennung = datei.parent.name
        eintrag = quellen.get(kennung) or Kalender(
            kennung=kennung, name=f"(ohne Namen, {kennung[:8]})")
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
        if kalender.datei is None:
            continue
        try:
            daten = ical.oeffne_datei(kalender.datei)
        except BibliothekFehlt:
            raise
        except ical.ICalFehler:
            continue
        alle += ical.termine_aus(daten, kalender.kennung, kalender.name,
                                 kalender.farbe, von, bis)

    gefiltert = [t for t in alle if von <= t.beginn <= bis]
    gefiltert.sort(key=lambda t: (t.beginn, not t.ganztags, t.titel))
    return gefiltert
