"""Rahmenloses, durchscheinendes Schreibtischfenster."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from .. import config as konfig_modul
from ..config import GROESSEN
from ..modell import Termin
from .gemeinsam import (
    LadeThread, app_symbol, erscheinungsfarben, setze_auf_allen_arbeitsflaechen, umgebung,
)
from .liste import TerminListe

_SCHRIFT_PRO_GROESSE = {
    "klein":      9,
    "mittel":     10,
    "gross":      11,
    "sehr_gross": 12,
}

# Eigener, unsichtbarer Titel (kein Rahmen, also nie zu sehen) - nötig, um
# dieses Fenster von außen (KWin-Skript) eindeutig vom Hauptfenster zu
# unterscheiden, das denselben wmclass trägt, aber "KALENDERBlick" heißt.
_FENSTERTITEL = "KALENDERBlick-Schreibtisch"


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
        # Rahmenlos heißt: kein Titelbalken zum Ziehen. Ein Filter auf der
        # ganzen Anwendung fängt Klicks auf eigene, sonst untätige Flächen
        # ab (Kopfzeile, Terminzeilen, Leerraum) und verschiebt stattdessen
        # das Fenster - auch neu nachgeladene Terminzeilen sind so erfasst,
        # ohne den Filter nach jeder Aktualisierung neu einzuhängen.
        QApplication.instance().installEventFilter(self)
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
        self.setWindowTitle(_FENSTERTITEL)
        self.setWindowIcon(app_symbol())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

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

    # ------------------------------------------------------------------

    def _ausgenommen(self, objekt) -> bool:
        """Eigene Widgets mit eigener Klickbedeutung - dort nicht ziehen."""
        ausnahmen = (
            self._liste._uhr,
            self._liste._scroll.verticalScrollBar(),
            self._liste._scroll.horizontalScrollBar(),
        )
        for ausnahme in ausnahmen:
            if objekt is ausnahme or ausnahme.isAncestorOf(objekt):
                return True
        return False

    def eventFilter(self, objekt, event) -> bool:
        if (not self._e.desktop.position_fixiert
                and event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
                and isinstance(objekt, QWidget)
                and objekt.window() is self
                and not self._ausgenommen(objekt)):
            fenstergriff = self.windowHandle()
            if fenstergriff is not None:
                fenstergriff.startSystemMove()
                return True
        return super().eventFilter(objekt, event)

    def _wende_groesse_an(self) -> None:
        breite, hoehe = GROESSEN.get(self._e.desktop.groesse, (340, 480))
        if self._e.desktop.ansicht == "uhr":
            # Drei Zeilen Text brauchen nicht die volle Listen-Höhe - sonst
            # bleibt oben und unten nur durchscheinende Leerfläche stehen.
            hoehe = round(breite * 0.42)
        self._e.desktop.breite = breite
        self._e.desktop.hoehe = hoehe
        self.resize(breite, hoehe)
        if self._env["x11"]:
            self.move(self._e.desktop.x, self._e.desktop.y)

    def _wende_transparenz_an(self) -> None:
        alpha = max(0, min(100, self._e.desktop.deckkraft))
        farben = erscheinungsfarben(self._e.desktop.erscheinung)
        self.setStyleSheet(
            f"QWidget {{ background-color: rgba({farben['hintergrund']}, {alpha}%); "
            f"border-radius: 8px; }}"
        )

    def _wende_arbeitsflaechen_an(self) -> None:
        setze_auf_allen_arbeitsflaechen(_FENSTERTITEL, self._e.desktop.alle_arbeitsflaechen)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self._wende_arbeitsflaechen_an()

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
        self._wende_arbeitsflaechen_an()
        self._liste.setze_erscheinung(self._e.desktop.erscheinung)
        self._liste.setze_ansicht(self._e.desktop.ansicht)
        self._liste.setze_schrift(_SCHRIFT_PRO_GROESSE.get(self._e.desktop.groesse, 10))
        self._liste.setze_stunden_format(self._e.desktop.stunden_format)
        self._timer.setInterval(self._e.aktualisierung_minuten * 60 * 1000)

    # ------------------------------------------------------------------

    def closeEvent(self, event) -> None:
        QApplication.instance().removeEventFilter(self)
        # Lage merken, damit beim nächsten Start wiederhergestellt werden kann
        pos = self.pos()
        self._e.desktop.x = pos.x()
        self._e.desktop.y = pos.y()
        self._e.desktop.sichtbar = False
        self._e.speichern()
        event.accept()
