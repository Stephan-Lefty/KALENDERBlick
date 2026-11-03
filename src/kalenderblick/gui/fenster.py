"""Hauptfenster mit drei Reitern: Termine · Einstellungen · Hilfe."""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import (
    QDesktopServices, QImage, QPalette, QTextCursor, QTextDocument,
)
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .. import (
    NAME, __version__, autostart, config as konfig_modul,
    hilfe as hilfe_modul, ics_abo, quellen, thunderbird,
)
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
    "sehr_klein": "Sehr klein",
    "klein":      "Klein",
    "mittel":     "Mittel",
    "gross":      "Groß",
    "sehr_gross": "Sehr groß",
}


_REPO = "https://github.com/Stephan-Lefty/KALENDERBlick"


class _AboDialog(QDialog):
    """Name und Adresse eines zu abonnierenden Kalenders erfragen."""

    def __init__(self, parent=None, abo=None):
        super().__init__(parent)
        self.setWindowTitle("Kalender abonnieren")
        self.setMinimumWidth(460)

        layout = QVBoxLayout(self)

        erklaerung = QLabel(
            "Viele Anbieter stellen zu jedem Kalender eine Adresse im "
            "iCalendar-Format bereit - bei Google etwa die „private "
            "Adresse im iCal-Format“ in den Kalendereinstellungen.\n\n"
            "<b>Diese Adresse ist ein Geheimnis:</b> Wer sie kennt, kann "
            "den Kalender lesen. Sie wird nur für dich lesbar gespeichert.")
        erklaerung.setWordWrap(True)
        erklaerung.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(erklaerung)

        formular = QFormLayout()
        self._name = QLineEdit(abo.name if abo else "")
        self._name.setPlaceholderText("z. B. Google – Privat")
        formular.addRow("Name:", self._name)

        self._url = QLineEdit(abo.url if abo else "")
        self._url.setPlaceholderText("https://…/basic.ics")
        formular.addRow("Adresse:", self._url)
        layout.addLayout(formular)

        self._hinweis = QLabel("")
        self._hinweis.setWordWrap(True)
        layout.addWidget(self._hinweis)

        knoepfe = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        knoepfe.button(QDialogButtonBox.StandardButton.Ok).setText("Abonnieren")
        knoepfe.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        knoepfe.accepted.connect(self._pruefen_und_schliessen)
        knoepfe.rejected.connect(self.reject)
        layout.addWidget(knoepfe)

    def _pruefen_und_schliessen(self) -> None:
        """Gleich ausprobieren, statt später eine leere Liste zu zeigen."""
        name = self._name.text().strip()
        url = self._url.text().strip()
        if not url:
            self._hinweis.setStyleSheet("color: #e66100;")
            self._hinweis.setText("Bitte eine Adresse angeben.")
            return

        self._hinweis.setStyleSheet("color: palette(mid);")
        self._hinweis.setText("Wird abgerufen …")
        QApplication.processEvents()

        probe = ics_abo.Abo(name=name or "Abonnierter Kalender", url=url)
        try:
            ics_abo.hole(probe, erzwingen=True)
        except Exception as fehler:
            self._hinweis.setStyleSheet("color: #e66100;")
            self._hinweis.setText(str(fehler))
            return
        self.accept()

    def abo(self):
        return ics_abo.Abo(
            name=self._name.text().strip() or "Abonnierter Kalender",
            url=self._url.text().strip())


class _HilfeReiter(QWidget):
    """Zeigt die mitgelieferte Anleitung - ohne Internet.

    Wer nicht weiterkommt, klickt auf Hilfe und findet dort dieselbe
    Anleitung samt Bildschirmfotos, die auch im Netz steht. Für längeres
    Lesen oder zum Ausdrucken lässt sie sich zusätzlich im Browser
    öffnen, wo die Bildschirmfotos in voller Größe erscheinen.
    """

    _BILDBREITE = 360

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._browser = QTextBrowser()
        self._browser.setOpenExternalLinks(True)
        self._browser.document().setDefaultStyleSheet(
            "h1 { font-size: 15pt; } h2 { font-size: 13pt; } h3 { font-size: 11pt; }")
        layout.addWidget(self._browser, stretch=1)

        self._browser_btn = QPushButton("Anleitung im Browser öffnen")
        self._browser_btn.setToolTip(
            "Öffnet dieselbe Anleitung im Webbrowser - dort erscheinen die\n"
            "Bildschirmfotos in voller Größe und lassen sich ausdrucken.\n"
            "Funktioniert auch ohne Internet.")
        self._browser_btn.clicked.connect(self._im_browser_oeffnen)
        layout.addWidget(self._browser_btn)

        self._zeige_anleitung()

    def _im_browser_oeffnen(self) -> None:
        html = hilfe_modul.als_html()
        if html is None:
            QDesktopServices.openUrl(QUrl(
                f"{_REPO}/blob/main/src/kalenderblick/hilfe/anleitung.md"))
            return
        ziel = Path(tempfile.gettempdir()) / "kalenderblick-anleitung.html"
        try:
            ziel.write_text(html, encoding="utf-8")
        except OSError:
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(ziel)))

    def _zeige_anleitung(self) -> None:
        text = hilfe_modul.anleitung_text()
        if text is None:
            self._browser.setMarkdown(
                f"# {NAME} {__version__}\n\n"
                "Die Anleitung konnte nicht gefunden werden. Online steht sie "
                f"unter <{_REPO}/blob/main/src/kalenderblick/hilfe/anleitung.md>.\n")
            self._browser_btn.setEnabled(False)
            return

        # Reihenfolge ist wesentlich: setMarkdown() räumt das Dokument leer
        # und wirft dabei auch zuvor eingehängte Bilder weg. Erst den Text
        # setzen, dann die Bilder - andersherum bleiben nur leere Stellen.
        self._browser.setMarkdown(text)

        # Die Bildschirmfotos sind breiter als dieses Fenster. Qt verkleinert
        # nicht von selbst, deshalb werden sie vorab verkleinert eingehängt.
        for pfad in hilfe_modul.bild_dateien():
            bild = QImage(str(pfad))
            if bild.isNull():
                continue
            if bild.width() > self._BILDBREITE:
                bild = bild.scaledToWidth(
                    self._BILDBREITE, Qt.TransformationMode.SmoothTransformation)
            self._browser.document().addResource(
                QTextDocument.ResourceType.ImageResource,
                QUrl(f"bilder/{pfad.name}"), bild)

        # Nach dem Nachreichen der Bilder muss der Textfluss neu berechnet
        # werden, sonst bleiben die Stellen auf Höhe null stehen.
        self._browser.document().markContentsDirty(
            0, self._browser.document().characterCount())
        self._browser.moveCursor(QTextCursor.MoveOperation.Start)


class _KalenderUebersicht(QScrollArea):
    """Zeigt alle Kalender mit Art und Abholfrequenz - rein lesend, sitzt
    im Reiter "Einstellungen". Ein eigener Reiter "Kalender" neben
    "Termine" ließ vermuten, dahinter verberge sich eine Kalenderansicht."""

    def __init__(self, parent=None, nach_aenderung=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.setMinimumHeight(180)
        self._nach_aenderung = nach_aenderung
        self._haken: dict = {}
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
            e = konfig_modul.laden()
            kalender = quellen.lies_kalender(
                quelle=e.quelle,
                profil_vorgabe=profil_pfad or e.profil)
            if not kalender:
                raise quellen.KeineQuelle(quellen._keine_quelle_text())
        except Exception as fehler:
            fehler_label = QLabel(str(fehler))
            fehler_label.setStyleSheet("color: #e66100;")
            fehler_label.setWordWrap(True)
            self._layout.addWidget(fehler_label)
            return

        jetzt = datetime.now()
        versteckt = set(konfig_modul.laden().versteckte_kalender)
        self._haken = {}

        # Eine Zeile je Kalender statt eines Rahmens mit vier Angaben:
        # Bei einem Dutzend Kalendern wäre das sonst eine endlose Rolle.
        # Die Einzelheiten stehen im Tooltip.
        nach_herkunft: dict[str, list] = {}
        for kal in kalender:
            nach_herkunft.setdefault(self._herkunft(kal), []).append(kal)

        for herkunft in sorted(nach_herkunft):
            gruppe = QGroupBox(herkunft)
            gl = QVBoxLayout(gruppe)
            gl.setSpacing(2)
            for kal in sorted(nach_herkunft[herkunft],
                              key=lambda k: (not k.ist_fern, k.name.lower())):
                gl.addWidget(self._zeile(kal, versteckt, jetzt))
            self._layout.addWidget(gruppe)

        self._layout.addStretch()

    @staticmethod
    def _herkunft(kal) -> str:
        """Aus welchem Programm der Kalender stammt."""
        modul = type(kal).__module__
        if modul.endswith("ics_abo"):
            return "Abonniert"
        if modul.endswith("evolution"):
            return "Evolution / GNOME Kalender"
        return "Thunderbird"

    def _zeile(self, kal, versteckt: set, jetzt: datetime) -> QWidget:
        zeile = QWidget()
        wl = QHBoxLayout(zeile)
        wl.setContentsMargins(2, 1, 2, 1)
        wl.setSpacing(6)

        haken = QCheckBox()
        haken.setChecked(kal.kennung not in versteckt)
        self._haken[kal.kennung] = haken
        wl.addWidget(haken)

        punkt = QLabel("●")
        punkt.setStyleSheet(f"color: {kal.farbe}; font-size: 13pt;")
        wl.addWidget(punkt)

        name = QLabel(kal.name or kal.kennung[:16])
        if kal.abgeschaltet:
            name.setStyleSheet("font-style: italic; color: palette(mid);")
        wl.addWidget(name, stretch=1)

        # Einzelheiten nur auf Nachfrage - sonst wird die Liste wieder lang.
        teile = [f"Art: {kal.art}", kal.abholtext()]
        if getattr(kal, "zuletzt_geschrieben", None):
            alter = int((jetzt - kal.zuletzt_geschrieben).total_seconds() // 60)
            teile.append(kal.zuletzt_geschrieben.strftime("Zuletzt: %d.%m.%Y %H:%M")
                         + f"  (vor {alter} min)")
        kennzeichen = []
        if kal.abgeschaltet:
            kennzeichen.append("im Kalenderprogramm abgeschaltet")
        if getattr(kal, "nur_lesen", False):
            kennzeichen.append("nur lesen")
        if kennzeichen:
            teile.append(", ".join(kennzeichen))
        teile.append("")
        teile.append("Haken entfernen, um diesen Kalender in KALENDERBlick\n"
                     "auszublenden - im Kalenderprogramm bleibt er sichtbar.")
        hinweis = "\n".join(teile)
        for widget in (zeile, haken, name, punkt):
            widget.setToolTip(hinweis)

        # Abonnierte Kalender hat der Nutzer selbst eingetragen - also
        # soll er sie auch wieder loswerden können.
        if self._herkunft(kal) == "Abonniert":
            weg = QPushButton("✕")
            weg.setFixedWidth(28)
            weg.setToolTip("Dieses Abonnement entfernen.")
            weg.clicked.connect(lambda _, k=kal: self._abo_entfernen(k))
            wl.addWidget(weg)
        return zeile

    def _abo_entfernen(self, abo) -> None:
        antwort = QMessageBox.question(
            self, "Abonnement entfernen",
            f"„{abo.name}“ nicht mehr abonnieren?\n\n"
            "Der Kalender beim Anbieter bleibt unberührt - nur "
            "KALENDERBlick ruft ihn nicht mehr ab.")
        if antwort != QMessageBox.StandardButton.Yes:
            return
        e = konfig_modul.laden()
        e.ics_abos = [roh for roh in e.ics_abos if roh.get("url") != abo.url]
        e.speichern()
        ics_abo.entferne_abschrift(abo)
        self.lade()
        if self._nach_aenderung:
            self._nach_aenderung()

    def versteckte_kalender(self) -> list[str]:
        """Die abgewählten Kalender - oder None, wenn noch nichts geladen
        wurde; dann darf die bestehende Auswahl nicht überschrieben
        werden."""
        if not getattr(self, "_haken", None):
            return None
        return sorted(kennung for kennung, box in self._haken.items()
                      if not box.isChecked())


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
            "Ob überhaupt ein Fenster auf dem Schreibtisch liegt. Wirkt\n"
            "sofort beim Speichern - das Leistensymbol bleibt davon\n"
            "unberührt.")
        wl.addRow(self._desktop_an)

        self._groesse = QComboBox()
        for schluessel, name in _GROESSE_NAMEN.items():
            self._groesse.addItem(name, schluessel)
        idx = list(_GROESSE_NAMEN).index(e.desktop.groesse) if e.desktop.groesse in _GROESSE_NAMEN else 1
        self._groesse.setCurrentIndex(idx)
        self._groesse.setToolTip(
            "Breite des Schreibtischfensters. Die Höhe richtet sich immer\n"
            "nach dem Inhalt - sie reicht so weit, wie Termine da sind,\n"
            "höchstens aber bis zum Bildschirmrand. Bei der Uhr-Ansicht\n"
            "steuert die Größe stattdessen die Schriftgröße.")
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

        self._jahr_zeigen = QCheckBox("Jahreszahl anzeigen")
        self._jahr_zeigen.setChecked(e.desktop.jahr_zeigen)
        self._jahr_zeigen.setToolTip(
            "Nur für die Uhr-Ansicht: zeigt die Jahreszahl als eigene\n"
            "Zeile unter dem Datum.")
        wl.addRow(self._jahr_zeigen)

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
            "nicht mehr versehentlich verschieben - und bleibt auch über\n"
            "einen Neustart von KALENDERBlick an dieser Stelle (nur\n"
            "KDE/KWin).")
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

        self._autostart = QCheckBox("Beim Anmelden automatisch starten")
        self._autostart.setChecked(autostart.ist_aktiv())
        self._autostart.setToolTip(
            "Legt eine .desktop-Datei in ~/.config/autostart/ an (oder\n"
            "entfernt sie) - unabhängig vom Startmenü-Eintrag.")
        al.addRow(self._autostart)

        layout.addWidget(allg_box)

        # --- Kalenderquellen: Profilwahl und Übersicht ---
        if self._kalender_uebersicht is not None:
            kalender_box = QGroupBox("Kalenderquellen")
            kl = QVBoxLayout(kalender_box)

            # Normalerweise findet KALENDERBlick das Profil von selbst.
            # Liegt es an einer ungewöhnlichen Stelle - eigene Partition,
            # verschobener Benutzerordner, fremde Thunderbird-Fassung -,
            # ging das bisher nur über die Kommandozeile.
            self._quelle = QComboBox()
            for schluessel in quellen.QUELLEN:
                self._quelle.addItem(quellen.QUELLEN_NAMEN[schluessel], schluessel)
            jetzige = e.quelle if e.quelle in quellen.QUELLEN else quellen.AUTOMATISCH
            self._quelle.setCurrentIndex(list(quellen.QUELLEN).index(jetzige))
            self._quelle.setToolTip(
                "Aus welchen Programmen die Termine kommen. „Alles, was\n"
                "gefunden wird“ nimmt Thunderbird und Evolution zusammen -\n"
                "wer beide nutzt, sieht alle Termine in einer Liste.")
            quelle_zeile = QFormLayout()
            quelle_zeile.addRow("Terminquelle:", self._quelle)
            kl.addLayout(quelle_zeile)

            self._profil_text = QLabel()
            self._profil_text.setWordWrap(True)
            self._profil_text.setStyleSheet("font-size: 9pt;")
            kl.addWidget(self._profil_text)

            knoepfe = QHBoxLayout()
            waehlen = QPushButton("Profilordner auswählen …")
            waehlen.setToolTip(
                "Den Ordner angeben, in dem Thunderbird seine Daten ablegt -\n"
                "zu erkennen an einem Unterordner namens „calendar-data“.")
            waehlen.clicked.connect(self._profil_waehlen)
            knoepfe.addWidget(waehlen)

            self._profil_zuruecksetzen = QPushButton("Wieder automatisch suchen")
            self._profil_zuruecksetzen.setToolTip(
                "Die eigene Angabe verwerfen und das Profil wieder selbst\n"
                "suchen lassen.")
            self._profil_zuruecksetzen.clicked.connect(self._profil_automatisch)
            knoepfe.addWidget(self._profil_zuruecksetzen)
            kl.addLayout(knoepfe)

            abonnieren = QPushButton("Kalender abonnieren …")
            abonnieren.setToolTip(
                "Einen Kalender unmittelbar über seine Internetadresse\n"
                "einbinden - etwa die private Adresse eines Google-\n"
                "Kalenders. Nützlich, wenn gar kein Kalenderprogramm\n"
                "eingerichtet ist.")
            abonnieren.clicked.connect(self._abo_hinzufuegen)
            kl.addWidget(abonnieren)

            kl.addWidget(self._kalender_uebersicht)
            layout.addWidget(kalender_box)
            self._zeige_profil()

        layout.addStretch()

        # "Einstellungen speichern" und die Statuszeile gehören nicht in
        # dieses (scrollbare) Widget, sondern werden vom Hauptfenster
        # darunter angeheftet - sonst verschwindet der Speichern-Knopf
        # beim Scrollen und man sieht nicht, ob gespeichert wurde.
        self._speichern_btn = QPushButton("Einstellungen speichern")
        self._speichern_btn.clicked.connect(self._speichern)

        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Sichtbare Versionsnummer - bei Rückfragen muss niemand erst auf
        # der Kommandozeile nachsehen, ein Bildschirmfoto genügt.
        self._version = QLabel(f"{NAME} {__version__}")
        self._version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Gedämpft, aber lesbar: "palette(mid)" ist eine Rahmenfarbe und
        # je nach Thema kaum vom Hintergrund zu unterscheiden. Stattdessen
        # die echte Textfarbe mit etwas weniger Deckkraft - das wirkt in
        # hellen wie dunklen Themen.
        farbe = self.palette().color(QPalette.ColorRole.WindowText)
        self._version.setStyleSheet(
            f"font-size: 9pt; color: rgba({farbe.red()}, {farbe.green()}, "
            f"{farbe.blue()}, 170);")
        self._version.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)

    def _abo_hinzufuegen(self) -> None:
        dialog = _AboDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        neu = dialog.abo()
        e = konfig_modul.laden()
        if any(roh.get("url") == neu.url for roh in e.ics_abos):
            self._status.setStyleSheet("color: #e66100;")
            self._status.setText("Dieser Kalender ist bereits abonniert.")
            return
        e.ics_abos = list(e.ics_abos) + [neu.als_dict()]
        e.speichern()
        self._kalender_uebersicht.lade()
        self._status.setStyleSheet("color: #2ec27e;")
        self._status.setText(f"„{neu.name}“ abonniert.")
        if self._cb:
            self._cb()

    def _zeige_profil(self) -> None:
        """Woher die Termine kommen - und ob das eine eigene Angabe ist."""
        e = konfig_modul.laden()
        if e.profil:
            self._profil_text.setText(
                f"Von Hand gewählt: <code>{e.profil}</code>")
            self._profil_zuruecksetzen.setEnabled(True)
            return
        self._profil_zuruecksetzen.setEnabled(False)
        try:
            gefunden = thunderbird.waehle_profil()
            self._profil_text.setText(
                f"Selbst gefunden: <code>{gefunden}</code>")
        except Exception:
            self._profil_text.setText(
                "<b>Kein Thunderbird-Profil gefunden.</b> Ist Thunderbird "
                "eingerichtet und liegt das Profil an einer ungewöhnlichen "
                "Stelle, lässt es sich hier von Hand auswählen.")

    def _profil_waehlen(self) -> None:
        start = str(Path.home())
        ordner = QFileDialog.getExistingDirectory(
            self, "Thunderbird-Profilordner auswählen", start)
        if not ordner:
            return

        pfad = Path(ordner)
        # Ein Profilordner erkennt man an „calendar-data“; wer sich
        # vergreift, bekommt lieber gleich Bescheid als später eine leere
        # Terminliste. Vielleicht wurde auch eine Ebene zu hoch gewählt.
        if not (pfad / "calendar-data").is_dir():
            treffer = sorted(pfad.glob("*/calendar-data"))
            if len(treffer) == 1:
                pfad = treffer[0].parent
            else:
                self._status.setStyleSheet("color: #e66100;")
                self._status.setText(
                    "Dort liegt kein Thunderbird-Profil (kein Ordner "
                    "„calendar-data“ darin).")
                return

        e = konfig_modul.laden()
        e.profil = str(pfad)
        e.speichern()
        self._zeige_profil()
        self._kalender_uebersicht.lade(str(pfad))
        self._status.setStyleSheet("color: #2ec27e;")
        self._status.setText("Profil übernommen.")
        if self._cb:
            self._cb()

    def _profil_automatisch(self) -> None:
        e = konfig_modul.laden()
        e.profil = ""
        e.speichern()
        self._zeige_profil()
        self._kalender_uebersicht.lade(None)
        self._status.setStyleSheet("color: #2ec27e;")
        self._status.setText("Es wird wieder selbst gesucht.")
        if self._cb:
            self._cb()

    def _speichern(self) -> None:
        e = konfig_modul.laden()
        e.desktop_an = self._desktop_an.isChecked()
        e.desktop.groesse = self._groesse.currentData()
        e.desktop.ansicht = self._ansicht.currentData()
        e.desktop.deckkraft = self._transp_slider.value()
        e.desktop.erscheinung = self._erscheinung.currentData()
        e.desktop.stunden_format = self._stunden_format.currentData()
        e.desktop.jahr_zeigen = self._jahr_zeigen.isChecked()
        e.desktop.klick_oeffnet = self._klick_oeffnet.isChecked()
        e.desktop.position_fixiert = self._position_fixiert.isChecked()
        e.desktop.alle_arbeitsflaechen = self._alle_arbeitsflaechen.isChecked()
        e.aktualisierung_minuten = self._interval.value()
        e.quelle = self._quelle.currentData()
        if self._kalender_uebersicht is not None:
            abgewaehlt = self._kalender_uebersicht.versteckte_kalender()
            if abgewaehlt is not None:
                e.versteckte_kalender = abgewaehlt
        # Größe auch in Pixel übernehmen
        breite, hoehe = GROESSEN[e.desktop.groesse]
        e.desktop.breite = breite
        e.desktop.hoehe = hoehe
        try:
            e.pruefe()
            e.speichern()
            if self._autostart.isChecked():
                autostart.aktiviere()
            else:
                autostart.deaktiviere()
            self._status.setStyleSheet("color: #2ec27e;")
            self._status.setText("Gespeichert.")
        except Exception as fehler:
            self._status.setStyleSheet("color: #e66100;")
            self._status.setText(str(fehler))
            return
        if self._cb:
            self._cb()


class HauptFenster(QMainWindow):
    """Normales Fenster mit drei Reitern.

    Verwaltet bei Bedarf (verwalte_desktop=True) auch das
    Schreibtischwidget selbst: legt es an oder entfernt es live, sobald
    der Schalter "Schreibtisch-Widget anzeigen" umgelegt wird - ohne
    Neustart von KALENDERBlick.
    """

    def __init__(self, verwalte_desktop: bool = True):
        super().__init__()
        self._verwalte_desktop = verwalte_desktop
        self._desktop = None
        self._thread: LadeThread | None = None
        self._setze_eigenschaften()
        self._baue_reiter()
        self._starte_ladethread()
        e = konfig_modul.laden()
        if self._verwalte_desktop and e.desktop_an:
            from .desktop import SchreibtischFenster
            self._desktop = SchreibtischFenster(hauptfenster_oeffnen_cb=self.fenster_umschalten)
            self._desktop.show()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._starte_ladethread)
        self._timer.start(e.aktualisierung_minuten * 60 * 1000)

    # ------------------------------------------------------------------

    def _setze_eigenschaften(self) -> None:
        self.setWindowTitle("KALENDERBlick")
        self.setWindowIcon(app_symbol())
        self.resize(400, 680)
        self.setMinimumSize(300, 400)

    def _baue_reiter(self) -> None:
        self._tabs = QTabWidget()
        self.setCentralWidget(self._tabs)

        self._termine_liste = TerminListe(ansicht="monat", schrift=10)

        # Meldungen (etwa "kein Thunderbird-Profil gefunden") gehören
        # über die Liste, sonst bliebe nur ein unverfängliches "Keine
        # Termine im gewählten Zeitraum" stehen.
        self._fehler = QLabel("")
        self._fehler.setStyleSheet(
            "color: #e66100; padding: 8px; font-weight: bold;")
        self._fehler.setWordWrap(True)
        self._fehler.setVisible(False)

        termine_seite = QWidget()
        tl = QVBoxLayout(termine_seite)
        tl.setContentsMargins(0, 0, 0, 0)
        tl.addWidget(self._fehler)
        tl.addWidget(self._termine_liste, stretch=1)
        self._tabs.addTab(termine_seite, "Termine")

        self._kalender_uebersicht = _KalenderUebersicht(
            nach_aenderung=self._einstellungen_geaendert)
        self._einstellungen = _EinstellungenReiter(
            einstellungen_geaendert_cb=self._einstellungen_geaendert,
            kalender_uebersicht=self._kalender_uebersicht)
        # Mit "Klick öffnet", Autostart und den Kalenderquellen passt der
        # Inhalt bei kleinerer Fensterhöhe nicht mehr ohne zu quetschen -
        # in einer Scroll-Fläche bleibt jede Zeile lesbar. "Einstellungen
        # speichern" und die Statuszeile bleiben außerhalb der Scroll-
        # Fläche angeheftet, damit sie immer sichtbar sind.
        einstellungen_scroll = QScrollArea()
        einstellungen_scroll.setWidgetResizable(True)
        einstellungen_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        einstellungen_scroll.setWidget(self._einstellungen)

        einstellungen_seite = QWidget()
        el = QVBoxLayout(einstellungen_seite)
        el.setContentsMargins(0, 0, 0, 0)
        el.addWidget(einstellungen_scroll, stretch=1)
        el.addWidget(self._einstellungen._speichern_btn)
        el.addWidget(self._einstellungen._status)
        el.addWidget(self._einstellungen._version)
        self._tabs.addTab(einstellungen_seite, "Einstellungen")

        self._tabs.addTab(_HilfeReiter(), "Hilfe")

        self._tabs.currentChanged.connect(self._reiter_gewechselt)

    # ------------------------------------------------------------------

    def zeige_termine_reiter(self) -> None:
        """Beim Öffnen aus Widget oder Leistensymbol zählt der schnelle
        Blick auf die Termine - nicht der zuletzt offene Reiter."""
        self._tabs.setCurrentIndex(0)

    def fenster_umschalten(self) -> None:
        """Vom Leistensymbol und vom Schreibtischwidget aus aufgerufen."""
        if self.isVisible():
            self.hide()
        else:
            self.zeige_termine_reiter()
            self.show()
            self.raise_()
            self.activateWindow()

    def _reiter_gewechselt(self, index: int) -> None:
        if index == 1:
            e = konfig_modul.laden()
            self._kalender_uebersicht.lade(e.profil or None)

    def _starte_ladethread(self) -> None:
        if self._thread and self._thread.isRunning():
            return
        self._thread = LadeThread(self)
        self._thread.fertig.connect(self._bei_fertig)
        self._thread.fehler.connect(self._bei_fehler)
        self._thread.start()

    def _bei_fertig(self, termine: list[Termin]) -> None:
        self._fehler.setVisible(False)
        self._termine_liste.setze_termine(termine)

    def _bei_fehler(self, meldung: str) -> None:
        """Ohne das stünde im Reiter „Termine“ nur „Keine Termine im
        gewählten Zeitraum" - als wäre alles in Ordnung und bloß nichts
        eingetragen. Tatsächlich wurde aber etwa gar kein
        Thunderbird-Profil gefunden."""
        self._fehler.setText(meldung)
        self._fehler.setVisible(True)

    def _einstellungen_geaendert(self) -> None:
        e = konfig_modul.laden()
        if self._verwalte_desktop:
            if e.desktop_an and self._desktop is None:
                from .desktop import SchreibtischFenster
                self._desktop = SchreibtischFenster(hauptfenster_oeffnen_cb=self.fenster_umschalten)
                self._desktop.show()
            elif not e.desktop_an and self._desktop is not None:
                self._desktop.close()
                self._desktop.deleteLater()
                self._desktop = None
            elif self._desktop is not None:
                self._desktop.aktualisiere_einstellungen()
        self._timer.setInterval(e.aktualisierung_minuten * 60 * 1000)
        self._starte_ladethread()
