"""Oberfläche von KALENDERBlick."""

from __future__ import annotations

import sys


def _pyqt_da() -> bool:
    try:
        import PyQt6.QtWidgets  # noqa: F401
    except ImportError:
        return False
    return True


def _app():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("kalenderblick")
    app.setApplicationDisplayName("KALENDERBlick")
    app.setDesktopFileName("kalenderblick")   # Wayland: Fensterklasse für KWin-Regel
    return app


def starte_fenster() -> int:
    if not _pyqt_da():
        print("PyQt6 fehlt. Installation: pip install PyQt6", file=sys.stderr)
        return 4
    from .fenster import HauptFenster
    app = _app()
    fenster = HauptFenster()
    fenster.show()
    return app.exec()


def starte_symbol() -> int:
    if not _pyqt_da():
        print("PyQt6 fehlt. Installation: pip install PyQt6", file=sys.stderr)
        return 4
    from PyQt6.QtWidgets import QApplication
    from .symbol import KalenderSymbol
    app = _app()
    if not QApplication.instance().style().standardIcon(
            __import__("PyQt6.QtWidgets", fromlist=["QStyle"]).QStyle.StandardPixmap.SP_ComputerIcon
    ):
        pass
    symbol = KalenderSymbol(beenden_cb=app.quit)
    symbol.show()
    return app.exec()


def starte_alles() -> int:
    """Symbol in der Leiste + Schreibtischfenster + Hauptfenster auf Anfrage."""
    if not _pyqt_da():
        print("PyQt6 fehlt. Installation: pip install PyQt6", file=sys.stderr)
        return 4

    from PyQt6.QtWidgets import QApplication
    from .desktop import SchreibtischFenster
    from .fenster import HauptFenster
    from .symbol import KalenderSymbol

    app = _app()

    hauptfenster = None

    def fenster_umschalten():
        if hauptfenster is None:
            return
        if hauptfenster.isVisible():
            hauptfenster.hide()
        else:
            hauptfenster.show()
            hauptfenster.raise_()
            hauptfenster.activateWindow()

    desktop = SchreibtischFenster(hauptfenster_oeffnen_cb=fenster_umschalten)
    desktop.show()

    hauptfenster = HauptFenster(desktop_fenster=desktop)

    symbol = KalenderSymbol(
        fenster_zeigen_cb=fenster_umschalten,
        beenden_cb=app.quit,
    )
    symbol.show()

    return app.exec()
