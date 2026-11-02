"""TerminListe – wiederverwendbares Widget für alle Ansichten."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..modell import MONATE, Termin, WOCHENTAGE, nach_tagen, tagesueberschrift
from .gemeinsam import FARBEN_SYSTEM, erscheinungsfarben, farbe_als_qt

_ANSICHT_TAGE = {
    "naechste3": None,   # Sonderfall: nur 3 Einträge
    "tag":        1,
    "woche":      7,
    "monat":     31,
}


class _Punkt(QWidget):
    """Kleiner farbiger Kreis für die Kalenderfarbe."""

    def __init__(self, hex_farbe: str, parent=None):
        super().__init__(parent)
        self._farbe = farbe_als_qt(hex_farbe)
        self.setFixedSize(10, 10)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(self._farbe)
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, 9, 9)


class _TerminZeile(QWidget):
    """Eine Zeile: Farbpunkt · Zeitangabe · Titel."""

    def __init__(self, termin: Termin, schrift: int = 10, farben: dict = FARBEN_SYSTEM, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 1, 4, 1)
        layout.setSpacing(0)

        zeile = QWidget()
        zl = QVBoxLayout(zeile)
        zl.setContentsMargins(0, 0, 0, 0)
        zl.setSpacing(0)

        from PyQt6.QtWidgets import QHBoxLayout
        h = QHBoxLayout()
        h.setSpacing(6)

        punkt = _Punkt(termin.farbe)
        h.addWidget(punkt, alignment=Qt.AlignmentFlag.AlignVCenter)

        zeit = QLabel(termin.zeitangabe())
        zeit.setStyleSheet(f"font-size: {schrift - 1}pt; color: {farben['gedaempft']};")
        zeit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        h.addWidget(zeit)

        titel = QLabel(termin.titel)
        titel_stil = f"font-size: {schrift}pt;"
        if farben["haupt"]:
            titel_stil += f" color: {farben['haupt']};"
        titel.setStyleSheet(titel_stil)
        titel.setWordWrap(True)
        h.addWidget(titel, stretch=1)

        zl.addLayout(h)

        if termin.ort:
            ort_label = QLabel(f"  {termin.ort}")
            ort_label.setStyleSheet(
                f"font-size: {schrift - 2}pt; color: {farben['schwach']}; padding-left: 16px;")
            zl.addWidget(ort_label)

        layout.addWidget(zeile)


class _TagesBlock(QWidget):
    """Tagesüberschrift + darunter die Terminzeilen."""

    def __init__(self, tag: date, termine: list[Termin], schrift: int,
                farben: dict = FARBEN_SYSTEM, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 2)
        layout.setSpacing(1)

        ueberschrift = QLabel(tagesueberschrift(tag).upper())
        ueberschrift.setStyleSheet(
            f"font-size: {schrift - 1}pt; font-weight: bold; "
            f"color: {farben['gedaempft']}; padding-left: 4px;"
        )
        layout.addWidget(ueberschrift)

        trenn = QFrame()
        trenn.setFrameShape(QFrame.Shape.HLine)
        trenn.setStyleSheet(f"color: {farben['schwach']};")
        layout.addWidget(trenn)

        for termin in termine:
            layout.addWidget(_TerminZeile(termin, schrift, farben))


class _UhrAnzeige(QWidget):
    """Wochentag über, Uhrzeit, Datum darunter. Anklicken ruft klick_cb auf."""

    def __init__(self, schrift: int = 10, farben: dict = FARBEN_SYSTEM,
                stunden_format: str = "24", klick_cb=None, parent=None):
        super().__init__(parent)
        self._klick_cb = klick_cb
        self._farben = farben
        self._schrift = schrift
        self._stunden_format = stunden_format

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addStretch()

        # Klicks müssen beim Elternwidget ankommen - Qt reicht ignorierte
        # Mausereignisse nicht automatisch vom Kind an den Elternteil weiter.
        self._wochentag = QLabel()
        self._wochentag.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wochentag.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._wochentag)

        self._zeit = QLabel()
        self._zeit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._zeit.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._zeit)

        self._datum = QLabel()
        self._datum.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._datum.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self._datum)

        layout.addStretch()

        if klick_cb:
            self.setCursor(Qt.CursorShape.PointingHandCursor)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._aktualisiere)
        self._timer.start(1000)
        self.setze_schrift(schrift)

    def setze_schrift(self, schrift: int) -> None:
        self._schrift = schrift
        farbe_haupt = f" color: {self._farben['haupt']};" if self._farben["haupt"] else ""
        self._wochentag.setStyleSheet(
            f"font-size: {schrift + 2}pt; font-weight: bold; "
            f"color: {self._farben['gedaempft']}; letter-spacing: 1px;")
        self._zeit.setStyleSheet(f"font-size: {schrift + 20}pt; font-weight: 300;{farbe_haupt}")
        self._datum.setStyleSheet(f"font-size: {schrift + 4}pt; color: {self._farben['gedaempft']};")
        self._aktualisiere()

    def setze_farben(self, farben: dict) -> None:
        self._farben = farben
        self.setze_schrift(self._schrift)

    def setze_stunden_format(self, stunden_format: str) -> None:
        self._stunden_format = stunden_format
        self._aktualisiere()

    def _aktualisiere(self) -> None:
        jetzt = datetime.now()
        self._wochentag.setText(WOCHENTAGE[jetzt.weekday()].upper())
        if self._stunden_format == "12":
            # %p verlässt sich auf die Locale - unter de_DE/de_AT bleibt es
            # leer, weil Deutsch kein AM/PM kennt. Deshalb selbst gerechnet.
            suffix = "AM" if jetzt.hour < 12 else "PM"
            self._zeit.setText(f"{jetzt.strftime('%I:%M')} {suffix}")
        else:
            self._zeit.setText(jetzt.strftime("%H:%M"))
        self._datum.setText(f"{jetzt.day}. {MONATE[jetzt.month - 1]}")

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._zug_start = event.globalPosition().toPoint()
            self._gezogen = False
        else:
            event.ignore()

    def mouseMoveEvent(self, event) -> None:
        start = getattr(self, "_zug_start", None)
        if start is None or not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        from PyQt6.QtWidgets import QApplication
        abstand = (event.globalPosition().toPoint() - start).manhattanLength()
        if abstand > QApplication.startDragDistance():
            self._gezogen = True
            self._zug_start = None
            fenstergriff = self.window().windowHandle()
            if fenstergriff is not None:
                fenstergriff.startSystemMove()

    def mouseReleaseEvent(self, event) -> None:
        if (event.button() == Qt.MouseButton.LeftButton
                and not getattr(self, "_gezogen", False) and self._klick_cb):
            self._klick_cb()
        self._zug_start = None


class TerminListe(QWidget):
    """Zeigt Termine nach Ansicht: naechste3 / tag / woche / monat / uhr."""

    def __init__(self, ansicht: str = "naechste3", schrift: int = 10,
                erscheinung: str | None = None, stunden_format: str = "24",
                klick_cb=None, parent=None):
        super().__init__(parent)
        self._ansicht = ansicht
        self._schrift = schrift
        self._klick_cb = klick_cb
        self._farben = erscheinungsfarben(erscheinung) if erscheinung else FARBEN_SYSTEM
        self._termine: list[Termin] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._stapel = QStackedWidget()
        layout.addWidget(self._stapel)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._stapel.addWidget(self._scroll)

        self._inhalt = QWidget()
        self._inhalt_layout = QVBoxLayout(self._inhalt)
        self._inhalt_layout.setContentsMargins(4, 4, 4, 4)
        self._inhalt_layout.setSpacing(0)
        self._inhalt_layout.addStretch()
        self._scroll.setWidget(self._inhalt)

        self._uhr = _UhrAnzeige(schrift, farben=self._farben,
                               stunden_format=stunden_format, klick_cb=self._klick_cb)
        self._stapel.addWidget(self._uhr)

        self._stapel.setCurrentWidget(self._uhr if ansicht == "uhr" else self._scroll)

    def setze_ansicht(self, ansicht: str) -> None:
        self._ansicht = ansicht
        self._aktualisiere()

    def setze_schrift(self, groesse: int) -> None:
        self._schrift = groesse
        self._uhr.setze_schrift(groesse)
        self._aktualisiere()

    def setze_erscheinung(self, erscheinung: str) -> None:
        self._farben = erscheinungsfarben(erscheinung)
        self._uhr.setze_farben(self._farben)
        self._aktualisiere()

    def setze_stunden_format(self, stunden_format: str) -> None:
        self._uhr.setze_stunden_format(stunden_format)

    def setze_termine(self, termine: list[Termin]) -> None:
        self._termine = termine
        self._aktualisiere()

    def _aktualisiere(self) -> None:
        if self._ansicht == "uhr":
            self._stapel.setCurrentWidget(self._uhr)
            return
        self._stapel.setCurrentWidget(self._scroll)

        while self._inhalt_layout.count() > 1:
            item = self._inhalt_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        gefiltert = self._filtere()
        if not gefiltert:
            leer = QLabel("Keine Termine im gewählten Zeitraum.")
            leer.setStyleSheet(
                f"font-size: {self._schrift}pt; color: {self._farben['gedaempft']}; padding: 8px;")
            leer.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._inhalt_layout.insertWidget(0, leer)
            return

        for tag, eintraege in nach_tagen(gefiltert):
            block = _TagesBlock(tag, eintraege, self._schrift, self._farben)
            self._inhalt_layout.insertWidget(self._inhalt_layout.count() - 1, block)

    def _filtere(self) -> list[Termin]:
        jetzt = datetime.now()
        heute = jetzt.date()

        if self._ansicht == "naechste3":
            kommend = [t for t in self._termine if not t.ist_vorbei(jetzt)]
            return kommend[:3]

        tage = _ANSICHT_TAGE.get(self._ansicht, 1)
        von = heute
        bis = heute + timedelta(days=tage - 1)
        return [t for t in self._termine if von <= t.tag <= bis]
