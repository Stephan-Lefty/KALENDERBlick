"""Kalender direkt abonnieren - ohne Thunderbird oder Evolution.

Gedacht für den Fall, dass gar kein Kalenderprogramm vorhanden ist.
Google, Nextcloud, Proton und viele andere bieten zu jedem Kalender eine
Adresse im iCalendar-Format an; die trägt man hier ein, und
KALENDERBlick holt sie selbst ab.

Zu bedenken: Eine solche Adresse ist ein Geheimnis - wer sie kennt,
sieht den Kalender. Sie steht in der Konfigurationsdatei, die deshalb
nur für den eigenen Benutzer lesbar angelegt wird.

Der bequemere Weg bleibt, den Kalender in Thunderbird oder Evolution
einzubinden: Die kümmern sich um Anmeldung, Erneuerung und
Zwischenspeicher, und KALENDERBlick liest dort ohnehin mit.
"""

from __future__ import annotations

import hashlib
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from pathlib import Path

from . import ical, paths
from .ical import BibliothekFehlt  # noqa: F401 - für bestehende Importe
from .modell import Termin

# Wie lange eine Abschrift als frisch gilt. Darunter wird nicht erneut
# geholt - sonst hinge die Oberfläche bei jeder Aktualisierung am Netz.
FRISCHE_MINUTEN = 30

# Nach dieser Zeit gilt ein Abruf als gescheitert. Lieber die gespeicherte
# Abschrift zeigen als die Oberfläche warten lassen.
ABRUF_TIMEOUT = 10


class AboFehler(Exception):
    """Ein Abo ließ sich nicht abrufen."""


@dataclass
class Abo:
    """Ein abonnierter Kalender."""
    name: str
    url: str
    farbe: str = "#3584e4"
    abgeschaltet: bool = False

    # Felder, die erst beim Lesen gefüllt werden
    anzahl: int = field(default=0, compare=False)
    zuletzt_geschrieben: datetime | None = field(default=None, compare=False)

    @property
    def kennung(self) -> str:
        """Eine stabile Kennung, abgeleitet aus der Adresse.

        Nicht die Adresse selbst, damit sie nicht in Protokollen oder
        Fehlermeldungen auftaucht - sie ist ja ein Geheimnis.
        """
        kurz = hashlib.sha256(self.url.encode("utf-8")).hexdigest()[:12]
        return f"abo-{kurz}"

    @property
    def art(self) -> str:
        return "ics-abo"

    @property
    def ist_fern(self) -> bool:
        return True

    def abholtext(self) -> str:
        return f"Abholung: alle {FRISCHE_MINUTEN} Minuten durch KALENDERBlick"

    def als_dict(self) -> dict:
        return {"name": self.name, "url": self.url, "farbe": self.farbe,
                "abgeschaltet": self.abgeschaltet}

    @classmethod
    def aus_dict(cls, roh: dict) -> "Abo":
        return cls(
            name=str(roh.get("name", "")) or "Abonnierter Kalender",
            url=str(roh.get("url", "")),
            farbe=str(roh.get("farbe", "")) or "#3584e4",
            abgeschaltet=bool(roh.get("abgeschaltet", False)),
        )


# ----------------------------------------------------------------------
#  Zwischenspeicher
# ----------------------------------------------------------------------

def _ablage() -> Path:
    ordner = paths.zustand_ordner() / "abos"
    ordner.mkdir(parents=True, exist_ok=True)
    return ordner


def abschrift(abo: Abo) -> Path:
    return _ablage() / f"{abo.kennung}.ics"


def _ist_frisch(datei: Path) -> bool:
    if not datei.exists():
        return False
    alter = datetime.now() - datetime.fromtimestamp(datei.stat().st_mtime)
    return alter < timedelta(minutes=FRISCHE_MINUTEN)


def hole(abo: Abo, erzwingen: bool = False) -> Path:
    """Die Adresse abrufen und ablegen; gibt die Abschrift zurück.

    Ist die vorhandene Abschrift noch frisch, wird nichts geholt.
    Scheitert der Abruf, aber es liegt eine ältere Abschrift vor, wird
    diese zurückgegeben - ein kurzer Netzausfall soll nicht dazu führen,
    dass plötzlich alle Termine verschwinden.
    """
    ziel = abschrift(abo)
    if not erzwingen and _ist_frisch(ziel):
        return ziel

    if not abo.url.lower().startswith(("http://", "https://", "webcal://")):
        raise AboFehler(f"„{abo.name}“: keine brauchbare Adresse.")

    # webcal:// ist nur eine andere Schreibweise für https://
    adresse = abo.url
    if adresse.lower().startswith("webcal://"):
        adresse = "https://" + adresse[len("webcal://"):]

    try:
        anfrage = urllib.request.Request(
            adresse, headers={"User-Agent": "KALENDERBlick"})
        with urllib.request.urlopen(anfrage, timeout=ABRUF_TIMEOUT) as antwort:
            roh = antwort.read()
    except (urllib.error.URLError, OSError, ValueError) as fehler:
        if ziel.exists():
            return ziel        # lieber alt als gar nichts
        raise AboFehler(
            f"„{abo.name}“ ließ sich nicht abrufen: {fehler}") from fehler

    # Erst prüfen, dann ablegen - sonst überschreibt eine Fehlerseite die
    # brauchbare Abschrift.
    try:
        ical.oeffne_text(roh)
    except BibliothekFehlt:
        raise
    except ical.ICalFehler as fehler:
        if ziel.exists():
            return ziel
        raise AboFehler(
            f"„{abo.name}“ liefert keine Kalenderdaten: {fehler}") from fehler

    vorlaeufig = ziel.with_suffix(".neu")
    vorlaeufig.write_bytes(roh)
    os.replace(vorlaeufig, ziel)
    return ziel


def entferne_abschrift(abo: Abo) -> None:
    abschrift(abo).unlink(missing_ok=True)


# ----------------------------------------------------------------------
#  Lesen
# ----------------------------------------------------------------------

def lies_kalender(abos: list[Abo]) -> list[Abo]:
    """Die Abos mit Anzahl und Stand - für die Übersicht."""
    ergebnis = []
    for abo in abos:
        if not abo.url:
            continue
        try:
            datei = hole(abo)
        except AboFehler:
            ergebnis.append(abo)
            continue
        abo.anzahl = ical.zaehle_termine(datei)
        try:
            abo.zuletzt_geschrieben = datetime.fromtimestamp(datei.stat().st_mtime)
        except OSError:
            pass
        ergebnis.append(abo)
    return ergebnis


def lies_termine(abos: list[Abo], tage_voraus: int = 14, tage_zurueck: int = 0,
                 versteckt: list[str] | None = None) -> list[Termin]:
    versteckt = versteckt or []
    heute = date.today()
    von = datetime.combine(heute - timedelta(days=tage_zurueck), time(0, 0))
    bis = datetime.combine(heute + timedelta(days=tage_voraus), time(23, 59, 59))

    alle: list[Termin] = []
    for abo in abos:
        if abo.abgeschaltet or not abo.url or abo.kennung in versteckt:
            continue
        try:
            datei = hole(abo)
            daten = ical.oeffne_datei(datei)
        except BibliothekFehlt:
            raise
        except (AboFehler, ical.ICalFehler):
            continue
        alle += ical.termine_aus(daten, abo.kennung, abo.name, abo.farbe,
                                 von, bis)

    gefiltert = [t for t in alle if von <= t.beginn <= bis]
    gefiltert.sort(key=lambda t: (t.beginn, not t.ganztags, t.titel))
    return gefiltert
