"""Rahmenloses, durchscheinendes Schreibtischfenster."""

from __future__ import annotations

from PyQt6.QtCore import QEvent, Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

from .. import config as konfig_modul
from ..config import GROESSEN
from ..modell import Termin
from . import position as positions_modul
from .gemeinsam import (
    LadeThread, app_symbol, erscheinungsfarben, erzwinge_fenstereigenschaften, umgebung,
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
        self._erste_ladung_fertig = False

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
            position_fixiert=self._e.desktop.position_fixiert,
            klick_cb=self._oeffne_hauptfenster,
            uhr_groesse=self._e.desktop.groesse,
            klick_aktiv=self._e.desktop.klick_oeffnet,
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
        """Klick öffnet das Hauptfenster, Ziehen verschiebt - dieselbe
        Unterscheidung wie in _UhrAnzeige, hier für die Listenansichten.
        Ohne das wäre ein Klick auf eine Terminzeile nur ein fehlgeschlagener
        Zugversuch gewesen, nie ein Öffnen des Hauptfensters.
        """
        passt = (isinstance(objekt, QWidget) and objekt.window() is self
                 and not self._ausgenommen(objekt))

        if passt and event.type() == QEvent.Type.MouseButtonPress \
                and event.button() == Qt.MouseButton.LeftButton:
            self._zug_start = event.globalPosition().toPoint()
            self._gezogen = False

        elif passt and event.type() == QEvent.Type.MouseMove \
                and not self._e.desktop.position_fixiert \
                and (event.buttons() & Qt.MouseButton.LeftButton):
            start = getattr(self, "_zug_start", None)
            if start is not None:
                from PyQt6.QtWidgets import QApplication
                abstand = (event.globalPosition().toPoint() - start).manhattanLength()
                if abstand > QApplication.instance().startDragDistance():
                    self._gezogen = True
                    self._zug_start = None
                    fenstergriff = self.windowHandle()
                    if fenstergriff is not None:
                        fenstergriff.startSystemMove()
                        return True

        elif passt and event.type() == QEvent.Type.MouseButtonRelease \
                and event.button() == Qt.MouseButton.LeftButton:
            gezogen = getattr(self, "_gezogen", False)
            self._zug_start = None
            if not gezogen:
                self._oeffne_hauptfenster()

        return super().eventFilter(objekt, event)

    def _oeffne_hauptfenster(self) -> None:
        if self._e.desktop.klick_oeffnet and self._hauptfenster_oeffnen_cb:
            self._hauptfenster_oeffnen_cb()

    def _wende_groesse_an(self, zeige_neu: bool = False) -> None:
        """zeige_neu=True erzwingt ein kurzes Aus-/Wiedereinblenden, damit
        KWin eine zweite Größenänderung an einem schon sichtbaren Fenster
        zuverlässig übernimmt (siehe _bei_fertig). Nur beim allerersten
        Nachladen nötig, direkt nach dem Start - dort hat der Nutzer das
        Widget noch nicht gezogen, es gibt also keine Position zu
        verlieren. Bei jeder späteren Größenänderung (z. B. beim
        Speichern der Einstellungen) NICHT neu einblenden, sonst springt
        das längst an die richtige Stelle gezogene Widget unter Wayland
        zurück in die Bildschirmmitte - Wayland kennt keine Methode, die
        Position vorher auszulesen und hinterher wiederherzustellen."""
        breite_max, hoehe_max = GROESSEN.get(self._e.desktop.groesse, (340, 480))
        if self._e.desktop.ansicht == "uhr":
            # Keine feste Breite mehr - der Kasten soll nur knapp um
            # Wochentag/Uhrzeit/Datum liegen. Wie groß das wirkt, steuert
            # stattdessen die Schrift selbst (_UHR_SCHRIFT in liste.py,
            # wächst mit der gewählten "Größe").
            rand = 2 * 8
            hinweis = self._liste._uhr.sizeHint()
            breite = max(150, hinweis.width() + rand)
            hoehe = max(150, hinweis.height() + rand)
        else:
            # Der Kasten soll nur unwesentlich größer sein als der Inhalt -
            # "Größe" ist hier nur noch die Obergrenze, bei wenig Terminen
            # bleibt viel durchscheinende Leerfläche sonst stehen.
            breite = breite_max
            hoehe = self._inhalt_hoehe(hoehe_max)
        self._e.desktop.breite = breite
        self._e.desktop.hoehe = hoehe
        neu_mappen = zeige_neu and self.isVisible()
        if neu_mappen:
            self.hide()
        self.resize(breite, hoehe)
        if neu_mappen:
            self.show()
        if self._env["x11"]:
            self.move(self._e.desktop.x, self._e.desktop.y)

    def _inhalt_hoehe(self, obergrenze: int) -> int:
        rand = 2 * 8 + 8   # Fensterrand oben/unten + etwas Luft
        # Nach dem Austauschen der Terminzeilen hat Qt das Layout noch nicht
        # zwangsläufig neu berechnet - invalidate()+activate() erzwingt das
        # synchron, sonst liefert sizeHint() mitunter noch den alten
        # (kleineren) Wert und der Kasten schneidet neue Zeilen ab.
        inhalt_layout = self._liste._inhalt.layout()
        inhalt_layout.invalidate()
        inhalt_layout.activate()
        gewuenscht = self._liste._inhalt.sizeHint().height() + rand
        return max(80, min(gewuenscht, obergrenze))

    def _wende_transparenz_an(self) -> None:
        alpha = max(0, min(100, self._e.desktop.deckkraft))
        farben = erscheinungsfarben(self._e.desktop.erscheinung)
        self.setStyleSheet(
            f"QWidget {{ background-color: rgba({farben['hintergrund']}, {alpha}%); "
            f"border-radius: 8px; }}"
        )

    def _erzwinge_kwin_eigenschaften(self) -> None:
        erzwinge_fenstereigenschaften(_FENSTERTITEL, self._e.desktop.alle_arbeitsflaechen)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # KWin braucht einen Moment, bis das frisch angezeigte Fenster in
        # workspace.windowList() auftaucht und die Eigenschaften greifen -
        # sofort aufgerufen verpufft es wirkungslos.
        QTimer.singleShot(1000, self._erzwinge_kwin_eigenschaften)

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
        # sizeHint() braucht einen Zwischenstopp im Ereignisumlauf, um die
        # gerade erst eingefügten Terminzeilen mitzuzählen. Nur beim
        # allerersten Laden nach dem Start neu einblenden (zeige_neu) -
        # da hat der Nutzer noch nicht gezogen, spätere Aktualisierungen
        # sollen die inzwischen gewählte Position nicht verwerfen.
        zeige_neu = not self._erste_ladung_fertig
        self._erste_ladung_fertig = True
        QTimer.singleShot(0, lambda: self._wende_groesse_an(zeige_neu=zeige_neu))
        # Bei jeder Aktualisierung gleich mit erneuern - so erholt sich das
        # Widget von selbst, falls Plasma die Eigenschaften je zurücksetzt
        # (z. B. nach dem Ruhezustand), ohne dass man neu einstellen muss.
        self._erzwinge_kwin_eigenschaften()

    def _bei_fehler(self, meldung: str) -> None:
        self._fehler.setText(meldung)
        self._fehler.setVisible(True)

    # ------------------------------------------------------------------

    def aktualisiere_einstellungen(self) -> None:
        """Wird aufgerufen, wenn der Nutzer Einstellungen geändert hat."""
        self._e = konfig_modul.laden()
        self._liste.setze_erscheinung(self._e.desktop.erscheinung)
        self._liste.setze_ansicht(self._e.desktop.ansicht)
        self._liste.setze_schrift(_SCHRIFT_PRO_GROESSE.get(self._e.desktop.groesse, 10))
        self._liste.setze_uhr_groesse(self._e.desktop.groesse)
        self._liste.setze_stunden_format(self._e.desktop.stunden_format)
        self._liste.setze_position_fixiert(self._e.desktop.position_fixiert)
        self._liste.setze_klick_aktiv(self._e.desktop.klick_oeffnet)
        # Erst die Schrift setzen, dann die Fenstergröße danach ausrichten -
        # sizeHint() der Uhr-Ansicht hängt von der gerade gesetzten Schrift ab.
        self._wende_groesse_an()
        self._wende_transparenz_an()
        self._erzwinge_kwin_eigenschaften()
        self._wende_positionssperre_an()
        self._timer.setInterval(self._e.aktualisierung_minuten * 60 * 1000)

    def _wende_positionssperre_an(self) -> None:
        """"Position sperren" heißt auch: über einen Neustart hinweg an
        derselben Stelle - dafür sorgt eine eigene KWin-Regel (siehe
        gui/position.py), da Wayland einer Anwendung weder die eigene
        Position verrät noch erlaubt, sie selbst zu setzen."""
        if self._e.desktop.position_fixiert:
            position = positions_modul.lies_position(_FENSTERTITEL)
            if position is not None:
                positions_modul.speichere_feste_position(_FENSTERTITEL, *position)
        else:
            positions_modul.entferne_feste_position()

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
