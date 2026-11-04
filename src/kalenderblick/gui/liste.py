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

ANSICHT_TAGE = {
    "naechste3": None,   # Sonderfall: nur 3 Einträge
    "woche":      7,
    "14tage":    14,
    "monat":     31,     # nur im Hauptfenster - am Widget nicht wählbar
}

# Eigene, deutlich größere Schrift für die Uhr-Ansicht - unabhängig von der
# kleinen Listen-Schrift (9-12pt), sonst bleibt bei größeren "Größe"-Stufen
# viel leere Fläche um den Text stehen, die das Quadrat nicht ausfüllt.
_UHR_SCHRIFT = {
    # "sehr_klein" ist für ältere Geräte mit 1920er Auflösung gedacht, wo
    # schon "klein" viel Platz einnimmt - etwa halb so groß wie "klein".
    "sehr_klein": {"wochentag":  8, "zeit": 22, "datum":  9},
    "klein":      {"wochentag": 14, "zeit": 44, "datum": 16},
    "mittel":     {"wochentag": 18, "zeit": 59, "datum": 19},
    "gross":      {"wochentag": 22, "zeit": 74, "datum": 24},
    "sehr_gross": {"wochentag": 26, "zeit": 88, "datum": 29},
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

    def __init__(self, groesse: str = "mittel", farben: dict = FARBEN_SYSTEM,
                stunden_format: str = "24", position_fixiert: bool = False,
                klick_cb=None, klick_aktiv: bool = True,
                jahr_zeigen: bool = False, parent=None):
        super().__init__(parent)
        self._klick_cb = klick_cb
        self._farben = farben
        self._groesse = groesse
        self._stunden_format = stunden_format
        self._position_fixiert = position_fixiert

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

        # Eigene Zeile unter dem Datum, gleiche Schriftgröße - abschaltbar,
        # weil das Jahr im Alltag meist überflüssig ist.
        self._jahr = QLabel()
        self._jahr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._jahr.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._jahr.setVisible(jahr_zeigen)
        layout.addWidget(self._jahr)

        layout.addStretch()

        self.setze_klick_aktiv(klick_aktiv)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._aktualisiere)
        self._timer.start(1000)
        self.setze_groesse(groesse)

    def setze_groesse(self, groesse: str) -> None:
        self._groesse = groesse
        pt = _UHR_SCHRIFT.get(groesse, _UHR_SCHRIFT["mittel"])
        farbe_haupt = f" color: {self._farben['haupt']};" if self._farben["haupt"] else ""
        self._wochentag.setStyleSheet(
            f"font-size: {pt['wochentag']}pt; font-weight: bold; "
            f"color: {self._farben['gedaempft']}; letter-spacing: 1px;")
        self._zeit.setStyleSheet(f"font-size: {pt['zeit']}pt; font-weight: 300;{farbe_haupt}")
        self._datum.setStyleSheet(f"font-size: {pt['datum']}pt; color: {self._farben['gedaempft']};")
        self._jahr.setStyleSheet(f"font-size: {pt['datum']}pt; color: {self._farben['gedaempft']};")
        self._aktualisiere()

    def setze_farben(self, farben: dict) -> None:
        self._farben = farben
        self.setze_groesse(self._groesse)

    def setze_stunden_format(self, stunden_format: str) -> None:
        self._stunden_format = stunden_format
        self._aktualisiere()

    def setze_position_fixiert(self, wert: bool) -> None:
        self._position_fixiert = wert

    def setze_klick_aktiv(self, wert: bool) -> None:
        if wert and self._klick_cb:
            self.setCursor(Qt.CursorShape.PointingHandCursor)
        else:
            self.unsetCursor()

    def setze_jahr_zeigen(self, wert: bool) -> None:
        self._jahr.setVisible(wert)
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
        self._jahr.setText(str(jetzt.year))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._zug_start = event.globalPosition().toPoint()
            self._gezogen = False
        else:
            event.ignore()

    def mouseMoveEvent(self, event) -> None:
        if self._position_fixiert:
            return
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
    """Zeigt Termine nach Ansicht: uhr / naechste3 / woche / 14tage / monat."""

    def __init__(self, ansicht: str = "naechste3", schrift: int = 10,
                erscheinung: str | None = None, stunden_format: str = "24",
                position_fixiert: bool = False, klick_cb=None,
                uhr_groesse: str = "mittel", klick_aktiv: bool = True,
                jahr_zeigen: bool = False, parent=None):
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
        # Bildlaufleiste stört die ruhige Fläche - Mausrad scrollt trotzdem.
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._stapel.addWidget(self._scroll)

        self._inhalt = QWidget()
        self._inhalt_layout = QVBoxLayout(self._inhalt)
        self._inhalt_layout.setContentsMargins(4, 4, 4, 4)
        self._inhalt_layout.setSpacing(0)
        self._inhalt_layout.addStretch()
        self._scroll.setWidget(self._inhalt)

        self._uhr = _UhrAnzeige(uhr_groesse, farben=self._farben, stunden_format=stunden_format,
                               position_fixiert=position_fixiert, klick_cb=self._klick_cb,
                               klick_aktiv=klick_aktiv, jahr_zeigen=jahr_zeigen)
        self._stapel.addWidget(self._uhr)

        self._stapel.setCurrentWidget(self._uhr if ansicht == "uhr" else self._scroll)

    def setze_ansicht(self, ansicht: str) -> None:
        self._ansicht = ansicht
        self._aktualisiere()

    def setze_schrift(self, groesse: int) -> None:
        self._schrift = groesse
        self._aktualisiere()

    def setze_uhr_groesse(self, groesse: str) -> None:
        self._uhr.setze_groesse(groesse)

    def setze_erscheinung(self, erscheinung: str) -> None:
        self._farben = erscheinungsfarben(erscheinung)
        self._uhr.setze_farben(self._farben)
        self._aktualisiere()

    def setze_stunden_format(self, stunden_format: str) -> None:
        self._uhr.setze_stunden_format(stunden_format)

    def setze_position_fixiert(self, wert: bool) -> None:
        self._uhr.setze_position_fixiert(wert)

    def setze_klick_aktiv(self, wert: bool) -> None:
        self._uhr.setze_klick_aktiv(wert)

    def setze_jahr_zeigen(self, wert: bool) -> None:
        self._uhr.setze_jahr_zeigen(wert)

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
        ende = self._zeitraum_ende()

        if not gefiltert:
            text = ("Keine Termine." if ende is None
                    else f"Bis {ende:%d.%m.} keine Termine.")
            # Ein leeres Feld sagt nichts darüber aus, ob überhaupt noch
            # etwas kommt. Liegt der nächste Termin nur knapp hinter dem
            # Zeitraum, ist genau das die Auskunft, die fehlt.
            weiter = self._naechster_danach(ende)
            if weiter is not None:
                text += f"\n\nNächster Termin am {weiter.tag:%d.%m.}:\n{weiter.titel}"
            leer = QLabel(text)
            leer.setWordWrap(True)
            leer.setStyleSheet(
                f"font-size: {self._schrift}pt; color: {self._farben['gedaempft']}; padding: 8px;")
            leer.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._inhalt_layout.insertWidget(0, leer)
            return

        for tag, eintraege in nach_tagen(gefiltert):
            block = _TagesBlock(tag, eintraege, self._schrift, self._farben)
            self._inhalt_layout.insertWidget(self._inhalt_layout.count() - 1, block)

        # Abschlusszeile mit dem Ende des Zeitraums. Ohne sie wirkt die
        # leere Fläche unter dem letzten Eintrag wie ein Fehler - gerade
        # wenn das Hauptfenster gleichzeitig weiter reicht, weil es dem
        # "Vorausblick" folgt und nicht der hier gewählten Ansicht.
        if ende is not None:
            text = f"bis {ende:%d.%m.} keine weiteren"
            weiter = self._naechster_danach(ende)
            if weiter is not None:
                text += f" · nächster {weiter.tag:%d.%m.}"
            fuss = QLabel(text)
            fuss.setWordWrap(True)
            fuss.setStyleSheet(
                f"font-size: {max(7, self._schrift - 1)}pt; "
                f"color: {self._farben['gedaempft']}; padding: 4px 8px 8px 8px;")
            fuss.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._inhalt_layout.insertWidget(self._inhalt_layout.count() - 1, fuss)

    def _naechster_danach(self, ende: date | None) -> Termin | None:
        """Der erste Termin hinter dem Zeitraum - sofern er überhaupt
        geladen wurde. Geladen wird nach „Vorausblick", mindestens aber
        die weiteste Ansicht; was darüber hinaus liegt, ist hier nicht
        bekannt und bleibt dann unerwähnt.
        """
        if ende is None:
            return None
        spaeter = [t for t in self._termine if t.tag > ende]
        return min(spaeter, key=lambda t: t.beginn) if spaeter else None

    def _zeitraum_ende(self) -> date | None:
        """Letzter Tag, den die gewählte Ansicht abdeckt.

        None bei „nächste 3", weil dort kein Zeitraum gilt, sondern eine
        Anzahl.
        """
        tage = ANSICHT_TAGE.get(self._ansicht)
        if not tage:
            return None
        return date.today() + timedelta(days=tage - 1)

    def _filtere(self) -> list[Termin]:
        jetzt = datetime.now()
        heute = jetzt.date()

        if self._ansicht == "naechste3":
            kommend = [t for t in self._termine if not t.ist_vorbei(jetzt)]
            return kommend[:3]

        tage = ANSICHT_TAGE.get(self._ansicht, 1)
        von = heute
        bis = heute + timedelta(days=tage - 1)
        return [t for t in self._termine if von <= t.tag <= bis]
