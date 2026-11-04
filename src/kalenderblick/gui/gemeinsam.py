"""Geteilt zwischen allen Ansichten: Lade-Thread, Umgebungserkennung, Hilfsfunktionen."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from PyQt6.QtCore import QRect, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap

from .. import bilder
from .. import config as konfig_modul
from .. import quellen
from ..modell import Termin
from .umgebung import umgebung  # noqa: F401 - re-exportiert für bestehende Importe


class LadeThread(QThread):
    """Liest die Termine im Hintergrund - aus allen gewählten Quellen.

    Holt immer so viele Tage, wie die weiteste Ansicht (Monat) braucht -
    "Vorausblick" in den Einstellungen ist eine Kommandozeilen-Angabe und
    soll nicht heimlich die Wochen- oder Monatsansicht der Oberfläche
    verkürzen.
    """

    fertig = pyqtSignal(list)
    fehler = pyqtSignal(str)

    def run(self) -> None:
        try:
            from .liste import ANSICHT_TAGE
            e = konfig_modul.laden()
            weiteste_ansicht = max(t for t in ANSICHT_TAGE.values() if t)
            termine = quellen.lies_termine(
                quelle=e.quelle,
                profil_vorgabe=e.profil,
                tage_voraus=max(e.tage_voraus, weiteste_ansicht),
                tage_zurueck=e.tage_zurueck,
                versteckt=e.versteckte_kalender,
            )
            self.fertig.emit(termine)
        except Exception as fehler:
            self.fehler.emit(str(fehler))


def erzwinge_fenstereigenschaften(fenstertitel: str, alle_arbeitsflaechen: bool) -> None:
    """Erzwingt die Eigenschaften, die das Schreibtischwidget nie in der
    Taskleiste oder beim Fensterwechsel zeigen sollen, sowie "auf allen
    Arbeitsflächen" - nur KDE.

    Die statische Fensterregel (packaging/kalenderblick.kwinrule) greift
    beim wmclass-Abgleich nicht mehr zuverlässig, sobald der tatsächliche
    Programmname von "kalenderblick" abweicht (z. B. "python3.14" bei
    manuellem Start) - deshalb hier bei jedem Anzeigen live über das
    KWin-Skript neu gesetzt, statt sich auf die Regel zu verlassen. Qt
    kennt für "auf allen Arbeitsflächen" ohnehin keine eigene,
    plattformübergreifende Einstellung; unter Wayland gibt es dafür kein
    Protokoll außerhalb von KWin. Fehlschlagen darf das, ohne die
    Oberfläche zu stören (anderer Fenstermanager, qdbus6 fehlt, KWin
    antwortet nicht).
    """
    if not umgebung()["kde"]:
        return
    # f.caption ist nicht immer exakt der gesetzte Fenstertitel - KWin hängt
    # unter Wayland mitunter einen Zusatz an ("Titel — App-Name"). Deshalb
    # ein Enthalten-Vergleich statt Gleichheit.
    skript = (
        "var liste = workspace.windowList();\n"
        "for (var i = 0; i < liste.length; i++) {\n"
        "    var f = liste[i];\n"
        f"    if (f.resourceClass === \"kalenderblick\""
        f" && f.caption.indexOf({json.dumps(fenstertitel)}) !== -1) {{\n"
        "        f.skipTaskbar = true;\n"
        "        f.skipSwitcher = true;\n"
        "        f.keepBelow = true;\n"
        "        f.minimized = false;\n"
        f"        f.onAllDesktops = {'true' if alle_arbeitsflaechen else 'false'};\n"
        "    }\n"
        "}\n"
    )
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".js", delete=False, encoding="utf-8") as datei:
            datei.write(skript)
            pfad = Path(datei.name)
        try:
            geladen = subprocess.run(
                ["qdbus6", "org.kde.KWin", "/Scripting", "loadScript", str(pfad)],
                capture_output=True, text=True, timeout=5)
            kennung = geladen.stdout.strip()
            if kennung.isdigit():
                subprocess.run(
                    ["qdbus6", "org.kde.KWin", f"/Scripting/Script{kennung}", "run"],
                    capture_output=True, text=True, timeout=5)
        finally:
            pfad.unlink(missing_ok=True)
    except (OSError, subprocess.SubprocessError):
        pass


# Größen, die eine Kontrollleiste üblicherweise anfordert. Für jede wird
# ein eigenes Bild erzeugt, damit nichts hoch- oder heruntergerechnet
# werden muss: Ein Symbol mit nur einer Auflösung wird von der Leiste
# skaliert und die Linien werden matschig - unter Cinnamon/X11 deutlich
# zu sehen gewesen. Die mitgelieferten Vorlagen bis 32 Pixel kommen
# zudem ohne Schriftzug aus; den wählt app_symbol() nur dann aus, wenn
# auch wirklich in dieser Größe gemalt wird.
_LEISTENGROESSEN = (16, 22, 24, 32, 48, 64, 128)

# Unterhalb dieser Kantenlänge wäre die Stundenzahl im Abzeichen nur noch
# ein Fleck - dort bleibt es bei einem schlichten Punkt.
_ABZEICHEN_MIT_TEXT_AB = 32


def symbol_mit_naechstem_termin(termin: Termin | None) -> QIcon:
    """Leistensymbol mit der Startstunde des nächsten Termins als
    Abzeichen unten rechts - ganztägige Termine und "kein Termin" bleiben
    ohne Abzeichen.
    """
    icon = QIcon()
    zeigt_abzeichen = termin is not None and not termin.ganztags
    text = termin.beginn.strftime("%H") if zeigt_abzeichen else ""

    for groesse in _LEISTENGROESSEN:
        bild = QPixmap(groesse, groesse)
        bild.fill(Qt.GlobalColor.transparent)
        maler = QPainter(bild)
        maler.setRenderHint(QPainter.RenderHint.Antialiasing)
        app_symbol().paint(maler, 0, 0, groesse, groesse)

        if zeigt_abzeichen:
            durchmesser = max(6, round(groesse * 0.47))
            rand = max(1, round(groesse * 0.03))
            x = groesse - durchmesser - rand
            y = groesse - durchmesser - rand
            maler.setBrush(QColor("#c01c28"))
            maler.setPen(Qt.PenStyle.NoPen)
            maler.drawEllipse(x, y, durchmesser, durchmesser)
            if groesse >= _ABZEICHEN_MIT_TEXT_AB:
                maler.setPen(QColor("#ffffff"))
                schrift = maler.font()
                schrift.setPixelSize(max(6, round(groesse * 0.31)))
                schrift.setBold(True)
                maler.setFont(schrift)
                maler.drawText(QRect(x, y, durchmesser, durchmesser),
                               Qt.AlignmentFlag.AlignCenter, text)

        maler.end()
        icon.addPixmap(bild)

    return icon


def farbe_als_qt(hex_farbe: str) -> QColor:
    farbe = QColor(hex_farbe)
    return farbe if farbe.isValid() else QColor("#3584e4")


def app_symbol() -> QIcon:
    icon = QIcon()
    for pfad in bilder.alle_symbole():
        icon.addFile(str(pfad))
    return icon


FARBEN_SYSTEM = {"haupt": None, "gedaempft": "#888888", "schwach": "#aaaaaa"}


def erscheinungsfarben(erscheinung: str) -> dict:
    """Hintergrund- und Textfarben für Hell/Dunkel.

    Das Schreibtischwidget liegt durchscheinend über wechselnden Hintergründen
    und folgt nicht automatisch dem Systemthema - deshalb eine eigene Wahl.
    """
    if erscheinung == "hell":
        return {
            "hintergrund": "250, 250, 250",
            "haupt": "#1a1a1a",
            "gedaempft": "rgba(0, 0, 0, 160)",
            "schwach": "rgba(0, 0, 0, 110)",
        }
    return {
        "hintergrund": "30, 30, 30",
        "haupt": "#f0f0f0",
        "gedaempft": "rgba(255, 255, 255, 160)",
        "schwach": "rgba(255, 255, 255, 110)",
    }


class AbholTakt:
    """Öffnet in festem Abstand ein kurzes Abholfenster für Thunderbird.

    Kein Dauerbetrieb: Ein laufender kopfloser Thunderbird hält die
    Profilsperre, und dann öffnet ein Klick auf Thunderbird kein
    Fenster mehr. Deshalb nur kurz starten, abholen lassen, beenden.

    Gewartet wird mit Zeitgebern statt mit sleep - sonst stünde die
    Oberfläche anderthalb Minuten still.
    """

    def __init__(self, parent=None):
        from PyQt6.QtCore import QTimer
        self._parent = parent
        self._takt = QTimer(parent)
        self._takt.timeout.connect(self.oeffne_fenster)
        self._schliesser = QTimer(parent)
        self._schliesser.setSingleShot(True)
        self._schliesser.timeout.connect(self._schliesse_fenster)

    def an(self) -> None:
        from .. import tb_dienst
        if self._takt.isActive():
            return
        self._takt.start(int(tb_dienst.ABSTAND_MINUTEN * 60 * 1000))
        # Nicht erst in einer halben Stunde anfangen - wer den Schalter
        # umlegt, möchte jetzt aktuelle Termine.
        self.oeffne_fenster()

    def aus(self) -> None:
        from .. import tb_dienst
        self._takt.stop()
        self._schliesser.stop()
        tb_dienst.beende()

    def oeffne_fenster(self) -> None:
        from .. import tb_dienst
        if tb_dienst.offen_ohne_uns():
            return      # Thunderbird ist auf, holt also selbst ab
        geklappt, _ = tb_dienst.starte()
        if geklappt:
            self._schliesser.start(int(tb_dienst.FENSTER_SEKUNDEN * 1000))

    def _schliesse_fenster(self) -> None:
        from .. import tb_dienst
        tb_dienst.beende()
