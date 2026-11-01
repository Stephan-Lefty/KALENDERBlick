"""Oberfläche von KALENDERBlick - noch nicht gebaut.

Der Entwurf steht in uebergabe-kalenderblick.md.
"""

from __future__ import annotations

import sys

HINWEIS = (
    "Die Oberfläche ist noch nicht gebaut.\n"
    "Bis dahin gibt es die Kommandozeile:\n"
    "  kalenderblick liste\n"
    "  kalenderblick kalender"
)


def _pyqt_da() -> bool:
    try:
        import PyQt6.QtWidgets  # noqa: F401
    except ImportError:
        return False
    return True


def starte_fenster() -> int:
    print(HINWEIS, file=sys.stderr)
    return 4


def starte_symbol() -> int:
    print(HINWEIS, file=sys.stderr)
    return 4


def starte_alles() -> int:
    print(HINWEIS, file=sys.stderr)
    return 4
