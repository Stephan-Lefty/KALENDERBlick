"""Findet die mitgelieferten Symbole - ohne Qt, damit auch Tests darankommen."""

from __future__ import annotations

from pathlib import Path

ORDNER = Path(__file__).resolve().parent / "bilder"
GROESSEN = (16, 22, 24, 32, 48, 64, 128, 256, 512)


def symbol_datei(groesse: int = 64) -> Path | None:
    """Die passende Symboldatei, oder die nächstgrößere."""
    passend = [g for g in GROESSEN if g >= groesse] or [GROESSEN[-1]]
    datei = ORDNER / f"symbol-{passend[0]}.png"
    return datei if datei.exists() else None


def alle_symbole() -> list[Path]:
    return [ORDNER / f"symbol-{g}.png" for g in GROESSEN
            if (ORDNER / f"symbol-{g}.png").exists()]


def windows_symbol() -> Path | None:
    datei = ORDNER / "symbol.ico"
    return datei if datei.exists() else None
