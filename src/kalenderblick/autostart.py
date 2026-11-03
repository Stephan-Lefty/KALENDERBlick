"""Autostart beim Anmelden - eigene .desktop-Datei in ~/.config/autostart/.

Unabhängig vom Startmenü-Eintrag (packaging/kalenderblick.desktop, landet
über die Paketierung in /usr/share/applications/) - diese Datei hier legt
und entfernt nur die Oberfläche selbst, kein Paketmanager rührt sie an.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from . import paths

_VORLAGE = """[Desktop Entry]
Type=Application
Name=KALENDERBlick
Comment=Thunderbirds Termine auf dem Schreibtisch und in der Kontrollleiste
Exec={befehl} start
Icon=kalenderblick
Terminal=false
Categories=Office;Calendar;Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
"""


def startbefehl() -> str:
    """Möglichst der volle Pfad zum Programm, nicht nur sein Name.

    Beim Anmelden erzeugt systemd aus den Dateien in ~/.config/autostart/
    eigene Einheiten - und löst `Exec=` dabei gegen einen noch sehr
    kargen Suchpfad auf, in dem ~/.local/bin fehlt. Steht dort nur
    `kalenderblick`, lautet das Ergebnis:

        Exec binary 'kalenderblick' does not exist: No such file or directory
        ... not generating unit, executable specified in Exec= does not exist.

    Die Einheit wird dann gar nicht erst angelegt, und der Autostart
    bleibt wirkungslos - auch wenn der Pfad in der fertigen Sitzung
    längst stimmt. Mit vollem Pfad kann das nicht passieren.
    """
    gefunden = shutil.which("kalenderblick")
    if gefunden:
        return gefunden

    # Keine Ableitung über den Suchpfad möglich (etwa weil das Programm
    # aus einer Umgebung heraus läuft, die ihn nicht enthält): dann neben
    # dem gerade laufenden Startskript nachsehen.
    eigenes = Path(sys.argv[0]).resolve().parent / "kalenderblick"
    if eigenes.exists() and os.access(eigenes, os.X_OK):
        return str(eigenes)

    # Letzter Ausweg - besser als gar keine Datei, greift aber nur, wenn
    # der Suchpfad beim Anmelden doch passt.
    return "kalenderblick"


def ist_aktiv() -> bool:
    return paths.autostart_datei().exists()


def aktiviere() -> None:
    datei = paths.autostart_datei()
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(_VORLAGE.format(befehl=startbefehl()), encoding="utf-8")


def deaktiviere() -> None:
    paths.autostart_datei().unlink(missing_ok=True)
