"""Leistensymbol (System Tray) für KALENDERBlick."""

from __future__ import annotations

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from .. import config as konfig_modul, thunderbird
from ..modell import Termin, kurzfassung, naechster
from .gemeinsam import LadeThread, app_symbol, symbol_mit_naechstem_termin


class KalenderSymbol(QSystemTrayIcon):
    """Sitzt in der Kontrollleiste; Hinweis = nächster Termin, Klick = Terminliste."""

    def __init__(self, fenster_zeigen_cb=None, beenden_cb=None, parent=None):
        super().__init__(app_symbol(), parent)
        self._fenster_zeigen_cb = fenster_zeigen_cb
        self._beenden_cb = beenden_cb
        self._termine: list[Termin] = []
        self._thread: LadeThread | None = None

        self._baue_menue()
        self.activated.connect(self._bei_klick)
        self._starte_ladethread()

        e = konfig_modul.laden()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._starte_ladethread)
        self._timer.start(e.aktualisierung_minuten * 60 * 1000)

    # ------------------------------------------------------------------

    def _baue_menue(self) -> None:
        menue = QMenu()
        menue.addAction("Termine anzeigen", self._oeffne_fenster)
        menue.addSeparator()
        menue.addAction("Jetzt aktualisieren", self._starte_ladethread)
        menue.addSeparator()
        menue.addAction("KALENDERBlick beenden", self._beenden)
        self.setContextMenu(menue)

    # ------------------------------------------------------------------

    def _starte_ladethread(self) -> None:
        if self._thread and self._thread.isRunning():
            return
        self._thread = LadeThread(self)
        self._thread.fertig.connect(self._bei_fertig)
        self._thread.fehler.connect(self._bei_fehler)
        self._thread.start()

    def _bei_fertig(self, termine: list[Termin]) -> None:
        self._termine = termine
        naechster_termin = naechster(termine)
        hinweis = kurzfassung(naechster_termin)
        self.setToolTip(f"KALENDERBlick\n{hinweis}")
        self.setIcon(symbol_mit_naechstem_termin(naechster_termin))

    def _bei_fehler(self, meldung: str) -> None:
        self.setToolTip(f"KALENDERBlick\nFehler: {meldung}")

    # ------------------------------------------------------------------

    def _bei_klick(self, grund: QSystemTrayIcon.ActivationReason) -> None:
        if grund == QSystemTrayIcon.ActivationReason.Trigger:
            self._oeffne_fenster()

    def _oeffne_fenster(self) -> None:
        if self._fenster_zeigen_cb:
            self._fenster_zeigen_cb()

    def _beenden(self) -> None:
        if self._beenden_cb:
            self._beenden_cb()
