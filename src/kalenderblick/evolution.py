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

from .modell import Termin

try:
    from icalendar import Calendar as _ICalendar
except ImportError:                                    # pragma: no cover
    _ICalendar = None                                  # type: ignore[assignment]

try:
    from dateutil.rrule import rrulestr
except ImportError:                                    # pragma: no cover
    rrulestr = None                                    # type: ignore[assignment]


class EvolutionFehler(Exception):
    """Daten nicht auffindbar oder unlesbar."""


class BibliothekFehlt(EvolutionFehler):
    """Das Paket „icalendar“ ist nicht da.

    Eigene Ausnahme, damit sie nicht zusammen mit kaputten Einzeldateien
    abgefangen wird: Ein unbrauchbarer Termin darf übersprungen werden,
    eine fehlende Bibliothek niemals - sonst stünde da ein Kalender ganz
    ohne Termine, und niemand erführe den Grund.
    """


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
            eintrag.anzahl = sum(
                1 for teil in _oeffne(datei).walk("VEVENT"))
        except BibliothekFehlt:
            raise
        except Exception:
            eintrag.anzahl = 0
        ergebnis.append(eintrag)

    return ergebnis


# ----------------------------------------------------------------------
#  Termine lesen
# ----------------------------------------------------------------------

def _oeffne(datei: Path):
    if _ICalendar is None:
        raise BibliothekFehlt(
            "Zum Lesen der Evolution-Kalender fehlt das Paket „icalendar“.\n"
            "Installation: pamac install python-icalendar  (Arch/Manjaro)\n"
            "              sudo apt install python3-icalendar  (Debian)")
    try:
        return _ICalendar.from_ical(datei.read_bytes())
    except (OSError, ValueError) as fehler:
        raise EvolutionFehler(f"{datei.name} ist unlesbar: {fehler}") from fehler


def _als_naiv(wert):
    """Zeitpunkte auf Ortszeit ohne Zeitzone bringen.

    Der Rest des Programms rechnet durchgehend mit naiven Zeitpunkten in
    Ortszeit; iCalendar liefert je nach Eintrag mit oder ohne Zone.
    """
    if isinstance(wert, datetime):
        if wert.tzinfo is not None:
            return wert.astimezone().replace(tzinfo=None)
        return wert
    # reines Datum = ganztägiger Termin
    return datetime.combine(wert, time(0, 0))


def _termine_eines_eintrags(teil, kalender: Kalender,
                            von: datetime, bis: datetime) -> list[Termin]:
    beginn_feld = teil.get("DTSTART")
    if beginn_feld is None:
        return []
    beginn = _als_naiv(beginn_feld.dt)
    ganztags = not isinstance(beginn_feld.dt, datetime)

    ende_feld = teil.get("DTEND")
    if ende_feld is not None:
        ende = _als_naiv(ende_feld.dt)
    else:
        dauer_feld = teil.get("DURATION")
        ende = beginn + (dauer_feld.dt if dauer_feld is not None else timedelta())
    if ende < beginn:
        ende = beginn
    dauer = ende - beginn

    titel = str(teil.get("SUMMARY", "")).strip() or "(ohne Titel)"
    ort = str(teil.get("LOCATION", "")).strip()
    kennung = str(teil.get("UID", ""))

    zeitpunkte = _entfalte(teil, beginn, von, bis)

    return [
        Termin(
            titel=titel,
            beginn=zeitpunkt,
            ende=zeitpunkt + dauer,
            ganztags=ganztags,
            ort=ort,
            kalender_id=kalender.kennung,
            kalender_name=kalender.name,
            farbe=kalender.farbe,
            kennung=f"{kennung}@{zeitpunkt.isoformat()}",
        )
        for zeitpunkt in zeitpunkte
    ]


def _entfalte(teil, beginn: datetime, von: datetime, bis: datetime) -> list[datetime]:
    """Wiederholungen auflösen, Ausnahmen abziehen."""
    regel = teil.get("RRULE")
    if regel is None or rrulestr is None:
        return [beginn] if von <= beginn <= bis else []

    try:
        satz = rrulestr(regel.to_ical().decode(), dtstart=beginn, forceset=True)
    except (ValueError, TypeError):
        return [beginn] if von <= beginn <= bis else []

    ausnahmen = set()
    exdate = teil.get("EXDATE")
    for eintrag in (exdate if isinstance(exdate, list) else [exdate] if exdate else []):
        for wert in getattr(eintrag, "dts", []):
            ausnahmen.add(_als_naiv(wert.dt).replace(microsecond=0))

    try:
        zeitpunkte = list(satz.between(von, bis, inc=True))
    except (ValueError, TypeError):
        return [beginn] if von <= beginn <= bis else []

    return [z for z in zeitpunkte if z.replace(microsecond=0) not in ausnahmen]


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
            kal = _oeffne(kalender.datei)
        except BibliothekFehlt:
            raise
        except EvolutionFehler:
            continue
        for teil in kal.walk("VEVENT"):
            try:
                alle += _termine_eines_eintrags(teil, kalender, von, bis)
            except Exception:
                # Ein kaputter Eintrag soll nicht die ganze Liste kippen.
                continue

    gefiltert = [t for t in alle if von <= t.beginn <= bis]
    gefiltert.sort(key=lambda t: (t.beginn, not t.ganztags, t.titel))
    return gefiltert
