"""Führt die unterstützten Kalenderprogramme unter einem Dach zusammen.

Bisher: Thunderbird (samt Betterbird) und Evolution. Beide legen ihre
Termine örtlich ab, beide werden nur gelesen. Wer seinen Google-,
Nextcloud- oder sonstigen Kalender in einem der beiden eingebunden hat,
sieht ihn damit auch hier - KALENDERBlick muss keinen dieser Anbieter
selbst kennen.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import evolution, thunderbird
from .modell import Termin

# Werte für die Einstellung `quelle`
AUTOMATISCH = "automatisch"
NUR_THUNDERBIRD = "thunderbird"
NUR_EVOLUTION = "evolution"
QUELLEN = (AUTOMATISCH, NUR_THUNDERBIRD, NUR_EVOLUTION)

QUELLEN_NAMEN = {
    AUTOMATISCH: "Alles, was gefunden wird",
    NUR_THUNDERBIRD: "Nur Thunderbird",
    NUR_EVOLUTION: "Nur Evolution",
}


class KeineQuelle(Exception):
    """Weder Thunderbird noch Evolution gefunden."""


@dataclass
class Lage:
    """Was auf diesem Rechner überhaupt vorhanden ist."""
    thunderbird: bool = False
    evolution: bool = False

    @property
    def irgendwas(self) -> bool:
        return self.thunderbird or self.evolution


def _thunderbird_da(profil_vorgabe: str = "") -> bool:
    try:
        thunderbird.waehle_profil(profil_vorgabe)
        return True
    except Exception:
        return False


def lage(profil_vorgabe: str = "") -> Lage:
    return Lage(thunderbird=_thunderbird_da(profil_vorgabe),
                evolution=evolution.vorhanden())


def _gewaehlt(quelle: str, vorhanden: Lage) -> tuple[bool, bool]:
    """(Thunderbird nutzen, Evolution nutzen)"""
    if quelle == NUR_THUNDERBIRD:
        return True, False
    if quelle == NUR_EVOLUTION:
        return False, True
    return vorhanden.thunderbird, vorhanden.evolution


def lies_termine(quelle: str = AUTOMATISCH, profil_vorgabe: str = "",
                 tage_voraus: int = 14, tage_zurueck: int = 0,
                 versteckt: list[str] | None = None) -> list[Termin]:
    """Termine aus allen gewählten Quellen, zusammengeführt und sortiert."""
    vorhanden = lage(profil_vorgabe)
    nutze_tb, nutze_ev = _gewaehlt(quelle, vorhanden)

    if not (nutze_tb or nutze_ev):
        raise KeineQuelle(_keine_quelle_text())

    alle: list[Termin] = []
    fehler: list[str] = []

    if nutze_tb:
        try:
            profil = thunderbird.waehle_profil(profil_vorgabe)
            alle += thunderbird.lies_termine(
                profil, tage_voraus=tage_voraus, tage_zurueck=tage_zurueck,
                versteckt=versteckt)
        except Exception as f:
            fehler.append(str(f))

    if nutze_ev:
        try:
            alle += evolution.lies_termine(
                tage_voraus=tage_voraus, tage_zurueck=tage_zurueck,
                versteckt=versteckt)
        except Exception as f:
            fehler.append(str(f))

    # Nur wenn gar nichts gelesen werden konnte, soll der Fehler
    # durchschlagen - liefert eine von zwei Quellen Termine, ist das
    # besser als eine Fehlermeldung ohne jeden Inhalt.
    if fehler and not alle:
        raise KeineQuelle("\n\n".join(fehler))

    alle.sort(key=lambda t: (t.beginn, not t.ganztags, t.titel))
    return alle


def lies_kalender(quelle: str = AUTOMATISCH, profil_vorgabe: str = "") -> list:
    """Alle Kalender beider Quellen - für die Übersicht in den Einstellungen."""
    vorhanden = lage(profil_vorgabe)
    nutze_tb, nutze_ev = _gewaehlt(quelle, vorhanden)

    ergebnis: list = []
    if nutze_tb:
        try:
            ergebnis += thunderbird.lies_kalender(
                thunderbird.waehle_profil(profil_vorgabe))
        except Exception:
            pass
    if nutze_ev:
        try:
            ergebnis += evolution.lies_kalender()
        except Exception:
            pass
    return ergebnis


def _keine_quelle_text() -> str:
    return (
        "Es wurde kein Kalenderprogramm gefunden.\n\n"
        "KALENDERBlick zeigt die Termine aus Thunderbird oder Evolution an. "
        "Eines von beiden muss eingerichtet sein und mindestens einen "
        "Kalender enthalten.\n\n"
        "Ist Thunderbird installiert und liegt sein Profil an einer "
        "ungewöhnlichen Stelle, lässt es sich unter\n"
        "„Einstellungen → Kalenderquellen“ von Hand auswählen."
    )
