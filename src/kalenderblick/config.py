"""Einstellungen."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields

from . import paths


class KonfigFehler(Exception):
    pass


@dataclass
class Fensterlage:
    x: int = 60
    y: int = 60
    breite: int = 340
    hoehe: int = 480
    deckkraft: int = 85          # Prozent
    sichtbar: bool = True


@dataclass
class Einstellungen:
    profil: str = ""                     # leer = selbst suchen
    tage_voraus: int = 14
    tage_zurueck: int = 0
    aktualisierung_minuten: int = 10
    versteckte_kalender: list[str] = field(default_factory=list)
    schriftgroesse: int = 10
    vergangene_zeigen: bool = False
    symbol_an: bool = True
    desktop_an: bool = True
    desktop: Fensterlage = field(default_factory=Fensterlage)

    def pruefe(self) -> None:
        if not 1 <= self.tage_voraus <= 365:
            raise KonfigFehler("Der Vorausblick muss zwischen 1 und 365 Tagen liegen.")
        if not 0 <= self.tage_zurueck <= 31:
            raise KonfigFehler("Der Rückblick muss zwischen 0 und 31 Tagen liegen.")
        if not 1 <= self.aktualisierung_minuten <= 240:
            raise KonfigFehler("Die Aktualisierung muss zwischen 1 und 240 Minuten liegen.")
        if not 20 <= self.desktop.deckkraft <= 100:
            raise KonfigFehler("Die Deckkraft muss zwischen 20 und 100 Prozent liegen.")

    def speichern(self):
        paths.lege_ordner_an()
        ziel = paths.konfig_datei()
        vorlaeufig = ziel.with_suffix(".json.neu")
        vorlaeufig.write_text(
            json.dumps(asdict(self), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(vorlaeufig, ziel)
        return ziel


def laden() -> Einstellungen:
    datei = paths.konfig_datei()
    if not datei.exists():
        return Einstellungen()
    try:
        rohdaten = json.loads(datei.read_text(encoding="utf-8"))
    except (OSError, ValueError) as fehler:
        raise KonfigFehler(f"Die Einstellungen sind unlesbar ({datei}): {fehler}") from fehler
    if not isinstance(rohdaten, dict):
        raise KonfigFehler(f"Unerwartetes Format in {datei}.")

    lage = rohdaten.pop("desktop", {})
    erlaubt = {f.name for f in fields(Einstellungen)}
    werte = {k: v for k, v in rohdaten.items() if k in erlaubt}
    einstellungen = Einstellungen(**werte)
    if isinstance(lage, dict):
        erlaubt_lage = {f.name for f in fields(Fensterlage)}
        einstellungen.desktop = Fensterlage(
            **{k: v for k, v in lage.items() if k in erlaubt_lage})
    return einstellungen
