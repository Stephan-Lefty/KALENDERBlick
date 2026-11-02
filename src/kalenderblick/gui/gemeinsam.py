"""Geteilt zwischen allen Ansichten: Lade-Thread, Umgebungserkennung, Hilfsfunktionen."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QColor, QIcon

from .. import bilder
from .. import config as konfig_modul
from .. import thunderbird
from ..modell import Termin


class LadeThread(QThread):
    """Liest Thunderbirds Termine im Hintergrund.

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
            profil = thunderbird.waehle_profil(e.profil)
            weiteste_ansicht = max(t for t in ANSICHT_TAGE.values() if t)
            termine = thunderbird.lies_termine(
                profil,
                tage_voraus=max(e.tage_voraus, weiteste_ansicht),
                tage_zurueck=e.tage_zurueck,
                versteckt=e.versteckte_kalender,
            )
            self.fertig.emit(termine)
        except Exception as fehler:
            self.fehler.emit(str(fehler))


def setze_auf_allen_arbeitsflaechen(fenstertitel: str, wert: bool) -> None:
    """Zeigt oder entfernt das Fenster auf allen Arbeitsflächen - nur KDE.

    Qt kennt dafür keine eigene, plattformübergreifende Einstellung; unter
    Wayland gibt es dafür kein Protokoll außerhalb von KWin. Deshalb
    dieselbe Technik, mit der sich KWin-Regeln auch sonst nur über ein
    kurzes Skript live setzen lassen - fehlschlagen darf das, ohne die
    Oberfläche zu stören (anderer Fensterm­anager, qdbus6 fehlt, KWin
    antwortet nicht).
    """
    if not umgebung()["kde"]:
        return
    skript = (
        "var liste = workspace.windowList();\n"
        "for (var i = 0; i < liste.length; i++) {\n"
        "    var f = liste[i];\n"
        f"    if (f.resourceClass === \"kalenderblick\" && f.caption === {json.dumps(fenstertitel)}) {{\n"
        f"        f.onAllDesktops = {'true' if wert else 'false'};\n"
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


def umgebung() -> dict:
    """Erkennt X11/Wayland und KDE/GNOME/Cinnamon zur Laufzeit."""
    session = os.environ.get("XDG_SESSION_TYPE", "").lower()
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    ist_wayland = session == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))
    ist_kde = "kde" in desktop or "plasma" in desktop
    return {
        "wayland": ist_wayland,
        "x11": not ist_wayland,
        "kde": ist_kde,
        "gnome": "gnome" in desktop,
        "cinnamon": "cinnamon" in desktop,
    }


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
