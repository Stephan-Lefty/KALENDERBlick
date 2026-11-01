"""Ablageorte für Einstellungen und Zwischenstände."""

from __future__ import annotations

import os
from pathlib import Path

ANWENDUNG = "kalenderblick"


def konfig_ordner() -> Path:
    basis = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(basis) / ANWENDUNG


def zustand_ordner() -> Path:
    basis = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(basis) / ANWENDUNG


def konfig_datei() -> Path:
    return konfig_ordner() / "einstellungen.json"


def arbeits_ordner() -> Path:
    """Hierhin werden Thunderbirds Datenbanken zum Lesen kopiert."""
    return zustand_ordner() / "kopien"


def autostart_datei() -> Path:
    basis = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(basis) / "autostart" / f"{ANWENDUNG}.desktop"


def lege_ordner_an() -> None:
    for ordner in (konfig_ordner(), zustand_ordner(), arbeits_ordner()):
        ordner.mkdir(parents=True, exist_ok=True)
