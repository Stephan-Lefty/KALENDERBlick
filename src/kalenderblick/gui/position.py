"""Feste Fensterposition über Neustarts hinweg - nur KDE/KWin/Wayland.

Wayland lässt eine Anwendung aus Datenschutzgründen weder die eigene
Bildschirmposition abfragen noch sie setzen - das betrifft jede normale
Wayland-Anwendung, nicht nur KALENDERBlick (echte Plasma-Miniprogramme
umgehen das, weil sie gar kein eigenes Fenster sind, sondern Teil von
plasmashell selbst). Der einzige Weg, eine Position über einen Neustart
hinweg festzuhalten, ist eine KWin-Fensterregel mit "Position erzwingen" -
die wird hier erzeugt, sobald "Position sperren" eingeschaltet wird, und
wieder entfernt, sobald sie ausgeschaltet wird.

Zum Lesen der *aktuellen* Position gibt es keine direkte Abfrage, nur den
Umweg über ein kurzes KWin-Skript, das die Position in den systemd-Journal
schreibt (dieselbe Technik wie beim Setzen der übrigen Fenstereigenschaften
in gemeinsam.py) - von dort wird sie zurückgelesen.
"""

from __future__ import annotations

import configparser
import json
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

from .umgebung import umgebung

_ABSCHNITT = "kalenderblick-position"


def _regeldatei() -> Path:
    return Path.home() / ".config" / "kwinrulesrc"


def _qdbus(*argumente: str, timeout: float = 5) -> str:
    ergebnis = subprocess.run(
        ["qdbus6", *argumente], capture_output=True, text=True, timeout=timeout)
    return ergebnis.stdout.strip()


def lies_position(fenstertitel: str) -> tuple[int, int] | None:
    """Liest die tatsächliche Bildschirmposition über ein KWin-Skript.

    Gibt None zurück, wenn nicht unter KDE/KWin, qdbus6 fehlt, journalctl
    nicht lesbar ist, oder das Fenster nicht gefunden wird - der Aufrufer
    muss damit rechnen und darf dann einfach nichts speichern.
    """
    if not umgebung()["kde"]:
        return None
    marke = f"KALENDERBLICK_POS_{uuid.uuid4().hex}"
    skript = (
        "var liste = workspace.windowList();\n"
        "for (var i = 0; i < liste.length; i++) {\n"
        "    var f = liste[i];\n"
        f"    if (f.resourceClass === \"kalenderblick\""
        f" && f.caption.indexOf({json.dumps(fenstertitel)}) !== -1) {{\n"
        f"        print(\"{marke}:\" + Math.round(f.x) + \",\" + Math.round(f.y));\n"
        "    }\n"
        "}\n"
    )
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", suffix=".js", delete=False, encoding="utf-8") as datei:
            datei.write(skript)
            pfad = Path(datei.name)
        try:
            kennung = _qdbus("org.kde.KWin", "/Scripting", "loadScript", str(pfad))
            if not kennung.isdigit():
                return None
            _qdbus("org.kde.KWin", f"/Scripting/Script{kennung}", "run")
        finally:
            pfad.unlink(missing_ok=True)

        # Das Skript schreibt asynchron in den Journal - kurz nachfassen,
        # statt sofort aufzugeben.
        for _ in range(10):
            zeile = subprocess.run(
                ["journalctl", "--user", "-b", "0", "-u", "plasma-kwin_wayland",
                 "--no-pager", "-g", marke],
                capture_output=True, text=True, timeout=3,
            ).stdout.strip().splitlines()
            if zeile:
                rest = zeile[-1].split(marke + ":", 1)[-1]
                x_text, _, y_text = rest.partition(",")
                try:
                    return int(x_text), int(y_text)
                except ValueError:
                    return None
            time.sleep(0.15)
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def _regeln_lesen() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.optionxform = str  # Groß-/Kleinschreibung der Schlüssel erhalten
    datei = _regeldatei()
    if datei.exists():
        parser.read(datei, encoding="utf-8")
    if "General" not in parser:
        parser["General"] = {"count": "0"}
    return parser


def _regeln_schreiben(parser: configparser.ConfigParser) -> None:
    datei = _regeldatei()
    datei.parent.mkdir(parents=True, exist_ok=True)
    vorlaeufig = datei.with_suffix(".neu")
    with open(vorlaeufig, "w", encoding="utf-8") as ziel:
        parser.write(ziel, space_around_delimiters=False)
    os.replace(vorlaeufig, datei)
    try:
        _qdbus("org.kde.KWin", "/KWin", "reconfigure")
    except (OSError, subprocess.SubprocessError):
        pass


def _aktive_regeln(parser: configparser.ConfigParser) -> list[str]:
    roh = parser["General"].get("rules", "")
    return [r for r in roh.split(",") if r]


def speichere_feste_position(fenstertitel: str, x: int, y: int) -> None:
    """Legt eine eigene KWin-Regel an (oder aktualisiert sie), die das
    Schreibtischwidget bei jedem Erscheinen auf (x, y) zwingt - andere,
    bereits vorhandene Regeln bleiben unangetastet."""
    if not umgebung()["kde"]:
        return
    try:
        parser = _regeln_lesen()
        regeln = _aktive_regeln(parser)
        if _ABSCHNITT not in regeln:
            regeln.append(_ABSCHNITT)
        parser["General"]["rules"] = ",".join(regeln)
        parser["General"]["count"] = str(len(regeln))
        parser[_ABSCHNITT] = {
            "Description": "KALENDERBlick – gesperrte Position",
            # Nur die Fensterklasse, nicht "kalenderblick kalenderblick" -
            # KWin vergleicht sonst auch den Instanznamen, der unter
            # Wayland vom tatsächlichen Programmnamen abhängt (z. B.
            # "python3.14") statt "kalenderblick" zu sein. Mit
            # wmclasscomplete=false und einteiligem wmclass zählt nur die
            # Klasse - am Gerät bestätigt, einteilig+complete=false trifft,
            # zweiteilig nicht.
            "wmclass": "kalenderblick",
            "wmclasscomplete": "false",
            "wmclassmatch": "1",
            "title": fenstertitel,
            "titlematch": "2",   # 2 = Enthält, da KWin an den Titel noch "— KALENDERBlick" anhängt
            "position": f"{x},{y}",
            "positionrule": "3",   # 3 = Erzwingen
        }
        _regeln_schreiben(parser)
    except (OSError, configparser.Error):
        pass


def entferne_feste_position() -> None:
    """Entfernt die eigene Positions-Regel wieder, falls vorhanden - andere
    Regeln bleiben unangetastet."""
    if not _regeldatei().exists():
        return
    try:
        parser = _regeln_lesen()
        if _ABSCHNITT not in parser:
            return
        parser.remove_section(_ABSCHNITT)
        regeln = [r for r in _aktive_regeln(parser) if r != _ABSCHNITT]
        parser["General"]["rules"] = ",".join(regeln)
        parser["General"]["count"] = str(len(regeln))
        _regeln_schreiben(parser)
    except (OSError, configparser.Error):
        pass
