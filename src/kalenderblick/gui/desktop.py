"""Rahmenloses, durchscheinendes Schreibtischfenster."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from .. import config as konfig_modul
from ..config import GROESSEN
from ..modell import Termin
from .gemeinsam import LadeThread, app_symbol, erscheinungsfarben, umgebung
from .liste import TerminListe

_SCHRIFT_PRO_GROESSE = {
    "klein":      9,
    "mittel":     10,
    "gross":      11,
    "sehr_gross": 12,
}


class SchreibtischFenster(QWidget):
    """Liegt hinter allen anderen Fenstern; zeigt Termine aus Thunderbird."""

    def __init__(self, hauptfenster_oeffnen_cb=None):
        super().__init__()
        self._e = konfig_modul.laden()
        self._env = umgebung()
        self._thread: LadeThread | None = None
        self._hauptfenster_oeffnen_cb = hauptfenster_oeffnen_cb

        self._baue_fenster()
        self._wende_groesse_an()
        self._wende_transparenz_an()
        self._starte_ladethread()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._starte_ladethread)
        self._timer.start(self._e.aktualisierung_minuten * 60 * 1000)

    # ------------------------------------------------------------------

    def _baue_fenster(self) -> None:
        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnBottomHint
        )
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("KALENDERBlick")
        self.setWindowIcon(app_symbol())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        self._kopf = QLabel("KALENDERBlick")
        layout.addWidget(self._kopf)

        self._liste = TerminListe(
            ansicht=self._e.desktop.ansicht,
            schrift=_SCHRIFT_PRO_GROESSE.get(self._e.desktop.groesse, 10),
            erscheinung=self._e.desktop.erscheinung,
            stunden_format=self._e.desktop.stunden_format,
            klick_cb=self._hauptfenster_oeffnen_cb,
        )
        layout.addWidget(self._liste, stretch=1)

        self._fehler = QLabel("")
        self._fehler.setStyleSheet("color: #e66100; font-size: 9pt; padding: 4px;")
        self._fehler.setWordWrap(True)
        self._fehler.setVisible(False)
        layout.addWidget(self._fehler)

        # Schwebt frei über dem Fenster, nicht im Layout - bei der Uhr-Ansicht
        # tritt es an die Stelle der Kopfzeile, die dort stört.
        self._einstellungen_knopf = QPushButton(self)
        self._einstellungen_knopf.setIcon(app_symbol())
        self._einstellungen_knopf.setIconSize(QSize(18, 18))
        self._einstellungen_knopf.setFixedSize(26, 26)
        self._einstellungen_knopf.setFlat(True)
        self._einstellungen_knopf.setToolTip("Einstellungen öffnen")
        self._einstellungen_knopf.setCursor(Qt.CursorShape.PointingHandCursor)
        self._einstellungen_knopf.setStyleSheet(
            "QPushButton { background: transparent; border: none; } "
            "QPushButton:hover { background: rgba(128, 128, 128, 60); border-radius: 13px; }"
        )
        if self._hauptfenster_oeffnen_cb:
            self._einstellungen_knopf.clicked.connect(self._hauptfenster_oeffnen_cb)
        self._positioniere_knopf()

        self._wende_kopfzeile_an()

    def _positioniere_knopf(self) -> None:
        rand = 6
        self._einstellungen_knopf.move(
            self.width() - self._einstellungen_knopf.width() - rand, rand)

    def _wende_kopfzeile_an(self) -> None:
        uhr_ansicht = self._e.desktop.ansicht == "uhr"
        self._kopf.setVisible(not uhr_ansicht)
        self._einstellungen_knopf.setVisible(uhr_ansicht and bool(self._hauptfenster_oeffnen_cb))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._positioniere_knopf()

    def _wende_groesse_an(self) -> None:
        breite, hoehe = GROESSEN.get(self._e.desktop.groesse, (340, 480))
        if self._e.desktop.ansicht == "uhr":
            breite = hoehe = breite   # Uhr + Datum wirkt als Quadrat am klarsten
        self._e.desktop.breite = breite
        self._e.desktop.hoehe = hoehe
        self.resize(breite, hoehe)
        if self._env["x11"]:
            self.move(self._e.desktop.x, self._e.desktop.y)

    def _wende_transparenz_an(self) -> None:
        alpha = max(20, min(100, self._e.desktop.deckkraft))
        farben = erscheinungsfarben(self._e.desktop.erscheinung)
        self.setStyleSheet(
            f"QWidget {{ background-color: rgba({farben['hintergrund']}, {alpha}%); "
            f"border-radius: 8px; }}"
        )
        self._kopf.setStyleSheet(
            f"font-weight: bold; font-size: 9pt; color: {farben['gedaempft']}; padding: 0 2px;"
        )

    # ------------------------------------------------------------------

    def _starte_ladethread(self) -> None:
        if self._thread and self._thread.isRunning():
            return
        self._thread = LadeThread(self)
        self._thread.fertig.connect(self._bei_fertig)
        self._thread.fehler.connect(self._bei_fehler)
        self._thread.start()

    def _bei_fertig(self, termine: list[Termin]) -> None:
        self._fehler.setVisible(False)
        self._liste.setze_termine(termine)

    def _bei_fehler(self, meldung: str) -> None:
        self._fehler.setText(meldung)
        self._fehler.setVisible(True)

    # ------------------------------------------------------------------

    def aktualisiere_einstellungen(self) -> None:
        """Wird aufgerufen, wenn der Nutzer Einstellungen geändert hat."""
        self._e = konfig_modul.laden()
        self._wende_groesse_an()
        self._wende_transparenz_an()
        self._wende_kopfzeile_an()
        self._liste.setze_erscheinung(self._e.desktop.erscheinung)
        self._liste.setze_ansicht(self._e.desktop.ansicht)
        self._liste.setze_schrift(_SCHRIFT_PRO_GROESSE.get(self._e.desktop.groesse, 10))
        self._liste.setze_stunden_format(self._e.desktop.stunden_format)
        self._timer.setInterval(self._e.aktualisierung_minuten * 60 * 1000)

    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        # Lage merken, damit beim nächsten Start wiederhergestellt werden kann
        pos = self.pos()
        self._e.desktop.x = pos.x()
        self._e.desktop.y = pos.y()
        self._e.desktop.sichtbar = False
        self._e.speichern()
        event.accept()
