"""Hauptfenster mit zwei Reitern: Termine · Einstellungen."""

from __future__ import annotations

from datetime import datetime

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import config as konfig_modul, thunderbird
from ..config import ANSICHTEN, GROESSEN
from ..modell import Termin
from .gemeinsam import LadeThread, app_symbol
from .liste import TerminListe

_ANSICHT_NAMEN = {
    "uhr":       "Uhr + Datum",
    "naechste3": "Nächste 3 Termine",
    "woche":     "Nächste 7 Tage",
    "14tage":    "Nächste 14 Tage",
}
_GROESSE_NAMEN = {
    "klein":      "Klein (280 × 340)",
    "mittel":     "Mittel (340 × 480)",
    "gross":      "Groß (420 × 600)",
    "sehr_gross": "Sehr groß (520 × 740)",
}


class _KalenderUebersicht(QScrollArea):
    """Zeigt alle Kalender mit Art und Abholfrequenz - rein lesend, sitzt
    im Reiter "Einstellungen". Ein eigener Reiter "Kalender" neben
    "Termine" ließ vermuten, dahinter verberge sich eine Kalenderansicht."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setMinimumHeight(180)
        self._inhalt = QWidget()
        self._layout = QVBoxLayout(self._inhalt)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setWidget(self._inhalt)

    def lade(self, profil_pfad=None) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        try:
            from pathlib import Path
            profil = Path(profil_pfad) if profil_pfad else thunderbird.waehle_profil()
            kalender = thunderbird.lies_kalender(profil)
        except Exception as fehler:
            fehler_label = QLabel(str(fehler))
            fehler_label.setStyleSheet("color: #e66100;")
            fehler_label.setWordWrap(True)
            self._layout.addWidget(fehler_label)
            return

        jetzt = datetime.now()
        for kal in sorted(kalender, key=lambda k: (not k.ist_fern, k.name.lower())):
            box = QGroupBox(kal.name or kal.kennung[:16])
            bl = QFormLayout(box)
            bl.addRow("Art:", QLabel(kal.art))
            bl.addRow("Abholung:", QLabel(kal.abholtext()))
            if kal.zuletzt_geschrieben:
                alter_min = int((jetzt - kal.zuletzt_geschrieben).total_seconds() // 60)
                wann = kal.zuletzt_geschrieben.strftime("%d.%m.%Y %H:%M")
                bl.addRow("Zuletzt:", QLabel(f"{wann}  (vor {alter_min} min)"))
            kennzeichen = []
            if kal.abgeschaltet:
                kennzeichen.append("abgeschaltet")
            if kal.nur_lesen:
                kennzeichen.append("nur lesen")
            if kennzeichen:
                bl.addRow("Status:", QLabel(", ".join(kennzeichen)))
            self._layout.addWidget(box)

        self._layout.addStretch()


class _EinstellungenReiter(QWidget):
    """Einstellungen für das Schreibtischwidget und allgemeine Optionen."""

    def __init__(self, einstellungen_geaendert_cb=None, kalender_uebersicht=None, parent=None):
        super().__init__(parent)
        self._cb = einstellungen_geaendert_cb
        self._kalender_uebersicht = kalender_uebersicht
        self._baue()

    def _baue(self) -> None:
        e = konfig_modul.laden()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # --- Widget-Aussehen ---
        widget_box = QGroupBox("Schreibtisch-Widget")
        wl = QFormLayout(widget_box)

        self._desktop_an = QCheckBox("Schreibtisch-Widget anzeigen")
        self._desktop_an.setChecked(e.desktop_an)
        self._desktop_an.setToolTip(
            "Ob überhaupt ein Fenster auf dem Schreibtisch liegt. Wirkt erst\n"
            "nach einem Neustart von KALENDERBlick - das Leistensymbol bleibt\n"
            "davon unberührt.")
        wl.addRow(self._desktop_an)

        self._groesse = QComboBox()
        for schluessel, name in _GROESSE_NAMEN.items():
            self._groesse.addItem(name, schluessel)
        idx = list(_GROESSE_NAMEN).index(e.desktop.groesse) if e.desktop.groesse in _GROESSE_NAMEN else 1
        self._groesse.setCurrentIndex(idx)
        self._groesse.setToolTip(
            "Breite und Höhe des Schreibtischfensters. Bei der Uhr-Ansicht\n"
            "wird daraus nur die Breite übernommen - die Höhe richtet sich\n"
            "dort nach dem Inhalt, nicht nach dieser Vorgabe.")
        wl.addRow("Größe:", self._groesse)

        self._ansicht = QComboBox()
        for schluessel, name in _ANSICHT_NAMEN.items():
            self._ansicht.addItem(name, schluessel)
        ansicht_idx = list(_ANSICHT_NAMEN).index(e.desktop.ansicht) if e.desktop.ansicht in _ANSICHT_NAMEN else 0
        self._ansicht.setCurrentIndex(ansicht_idx)
        self._ansicht.setToolTip(
            "Was im Schreibtischwidget steht: die nächsten drei Termine,\n"
            "ein Tag, eine Woche, ein Monat - oder nur Wochentag, Uhrzeit\n"
            "und Datum ohne Terminliste.")
        wl.addRow("Ansicht:", self._ansicht)

        transp_zeile = QWidget()
        tl = QHBoxLayout(transp_zeile)
        tl.setContentsMargins(0, 0, 0, 0)
        self._transp_slider = QSlider(Qt.Orientation.Horizontal)
        self._transp_slider.setRange(0, 100)
        self._transp_slider.setValue(e.desktop.deckkraft)
        self._transp_label = QLabel(f"{e.desktop.deckkraft} %")
        self._transp_label.setFixedWidth(40)
        self._transp_slider.valueChanged.connect(
            lambda v: self._transp_label.setText(f"{v} %"))
        transp_tooltip = (
            "Wie durchsichtig der Hintergrund des Schreibtischwidgets ist -\n"
            "0 % ganz unsichtbar (nur Schrift bleibt), 100 % voll deckend.")
        self._transp_slider.setToolTip(transp_tooltip)
        tl.addWidget(self._transp_slider, stretch=1)
        tl.addWidget(self._transp_label)
        wl.addRow("Transparenz:", transp_zeile)

        self._erscheinung = QComboBox()
        self._erscheinung.addItem("Dark-Mode (weiße Schrift)", "dunkel")
        self._erscheinung.addItem("Light-Mode (schwarze Schrift)", "hell")
        erscheinung_idx = 1 if e.desktop.erscheinung == "hell" else 0
        self._erscheinung.setCurrentIndex(erscheinung_idx)
        self._erscheinung.setToolTip(
            "Helle oder dunkle Farben für Hintergrund und Schrift - je\n"
            "nachdem, was zum Hintergrund dahinter passt. Wirkt nur auf\n"
            "das Schreibtischwidget, nicht auf dieses Fenster hier.")
        wl.addRow("Erscheinungsbild:", self._erscheinung)

        self._stunden_format = QComboBox()
        self._stunden_format.addItem("24 Stunden", "24")
        self._stunden_format.addItem("12 Stunden (AM/PM)", "12")
        stunden_idx = 1 if e.desktop.stunden_format == "12" else 0
        self._stunden_format.setCurrentIndex(stunden_idx)
        self._stunden_format.setToolTip(
            "Nur für die Uhr-Ansicht: Uhrzeit mit 24 Stunden oder mit\n"
            "12 Stunden samt AM/PM.")
        wl.addRow("Stundenformat:", self._stunden_format)

        self._klick_oeffnet = QCheckBox("Klick öffnet die Termine")
        self._klick_oeffnet.setChecked(e.desktop.klick_oeffnet)
        self._klick_oeffnet.setToolTip(
            "Ein Klick auf das Widget öffnet das Hauptfenster mit den\n"
            "Terminen. Einmal ausgeschaltet, lässt sich das Widget nur noch\n"
            "über das Leistensymbol öffnen oder verschieben.")
        wl.addRow(self._klick_oeffnet)

        self._position_fixiert = QCheckBox("Position sperren")
        self._position_fixiert.setChecked(e.desktop.position_fixiert)
        self._position_fixiert.setToolTip(
            "Einmal an die richtige Stelle gezogen, lässt sich das Fenster\n"
            "nicht mehr versehentlich verschieben.")
        wl.addRow(self._position_fixiert)

        self._alle_arbeitsflaechen = QCheckBox("Auf allen Arbeitsflächen zeigen")
        self._alle_arbeitsflaechen.setChecked(e.desktop.alle_arbeitsflaechen)
        self._alle_arbeitsflaechen.setToolTip(
            "Das Widget bleibt sichtbar, egal auf welche Arbeitsfläche du\n"
            "wechselst - nur unter KDE/KWin wirksam.")
        wl.addRow(self._alle_arbeitsflaechen)

        layout.addWidget(widget_box)

        # --- Allgemein ---
        # "Vorausblick" (tage_voraus) bewusst nicht hier - wirkt nur auf die
        # Kommandozeile, hätte in dieser Oberfläche nur verwirrt.
        allg_box = QGroupBox("Allgemein")
        al = QFormLayout(allg_box)

        self._interval = QSpinBox()
        self._interval.setRange(1, 240)
        self._interval.setValue(e.aktualisierung_minuten)
        self._interval.setSuffix(" Minuten")
        self._interval.setToolTip(
            "Wie oft die Oberfläche Thunderbirds Kalenderdaten neu einliest.\n"
            "Ersetzt nicht Thunderbirds eigene Abholfrequenz für entfernte\n"
            "Kalender (siehe „Kalenderquellen“ weiter unten) - erst wenn\n"
            "Thunderbird selbst abgeholt hat, gibt es hier etwas Neues zu sehen.")
        al.addRow("Aktualisierung:", self._interval)

        layout.addWidget(allg_box)

        # --- Kalenderübersicht (rein lesend, kein eigener Schalter) ---
        if self._kalender_uebersicht is not None:
            kalender_box = QGroupBox("Kalenderquellen")
            kl = QVBoxLayout(kalender_box)
            kl.addWidget(self._kalender_uebersicht)
            layout.addWidget(kalender_box)

        # --- Speichern ---
        btn = QPushButton("Einstellungen speichern")
        btn.clicked.connect(self._speichern)
        layout.addWidget(btn)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._status)

        layout.addStretch()

    def _speichern(self) -> None:
        e = konfig_modul.laden()
        e.desktop_an = self._desktop_an.isChecked()
        e.desktop.groesse = self._groesse.currentData()
        e.desktop.ansicht = self._ansicht.currentData()
        e.desktop.deckkraft = self._transp_slider.value()
        e.desktop.erscheinung = self._erscheinung.currentData()
        e.desktop.stunden_format = self._stunden_format.currentData()
        e.desktop.klick_oeffnet = self._klick_oeffnet.isChecked()
        e.desktop.position_fixiert = self._position_fixiert.isChecked()
        e.desktop.alle_arbeitsflaechen = self._alle_arbeitsflaechen.isChecked()
        e.aktualisierung_minuten = self._interval.value()
        # Größe auch in Pixel übernehmen
        breite, hoehe = GROESSEN[e.desktop.groesse]
        e.desktop.breite = breite
        e.desktop.hoehe = hoehe
        try:
            e.pruefe()
            e.speichern()
            self._status.setStyleSheet("color: #2ec27e;")
            self._status.setText("Gespeichert.")
        except Exception as fehler:
            self._status.setStyleSheet("color: #e66100;")
            self._status.setText(str(fehler))
            return
        if self._cb:
            self._cb()


class HauptFenster(QMainWindow):
    """Normales Fenster mit drei Reitern."""

    def __init__(self, desktop_fenster=None):
        super().__init__()
        self._desktop = desktop_fenster
        self._thread: LadeThread | None = None
        self._setze_eigenschaften()
        self._baue_reiter()
        self._starte_ladethread()
        e = konfig_modul.laden()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._starte_ladethread)
        self._timer.start(e.aktualisierung_minuten * 60 * 1000)

    # ------------------------------------------------------------------

    def _setze_eigenschaften(self) -> None:
        self.setWindowTitle("KALENDERBlick")
        self.setWindowIcon(app_symbol())
        self.resize(400, 560)
        self.setMinimumSize(300, 400)

    def _baue_reiter(self) -> None:
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        self._termine_liste = TerminListe(ansicht="monat", schrift=10)
        self._tabs.addTab(self._termine_liste, "Termine")

        self._kalender_uebersicht = _KalenderUebersicht()
        einstellungen = _EinstellungenReiter(
            einstellungen_geaendert_cb=self._einstellungen_geaendert,
            kalender_uebersicht=self._kalender_uebersicht)
        self._tabs.addTab(einstellungen, "Einstellungen")

        self._tabs.currentChanged.connect(self._reiter_gewechselt)

    # ------------------------------------------------------------------

    def zeige_termine_reiter(self) -> None:
        """Beim Öffnen aus Widget oder Leistensymbol zählt der schnelle
        Blick auf die Termine - nicht der zuletzt offene Reiter."""
        self._tabs.setCurrentIndex(0)

    def _reiter_gewechselt(self, index: int) -> None:
        if index == 1:
            self._kalender_uebersicht.lade()

    def _starte_ladethread(self) -> None:
        if self._thread and self._thread.isRunning():
            return
        self._thread = LadeThread(self)
        self._thread.fertig.connect(self._bei_fertig)
        self._thread.start()

    def _bei_fertig(self, termine: list[Termin]) -> None:
        self._termine_liste.setze_termine(termine)

    def _einstellungen_geaendert(self) -> None:
        if self._desktop:
            self._desktop.aktualisiere_einstellungen()
        e = konfig_modul.laden()
        self._timer.setInterval(e.aktualisierung_minuten * 60 * 1000)
        self._starte_ladethread()
