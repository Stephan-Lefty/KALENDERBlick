"""Autostart beim Anmelden - eigene .desktop-Datei in ~/.config/autostart/.

Unabhängig vom Startmenü-Eintrag (packaging/kalenderblick.desktop, landet
über die Paketierung in /usr/share/applications/) - diese Datei hier legt
und entfernt nur die Oberfläche selbst, kein Paketmanager rührt sie an.
"""

from __future__ import annotations

from . import paths

_INHALT = """[Desktop Entry]
Type=Application
Name=KALENDERBlick
Comment=Thunderbirds Termine auf dem Schreibtisch und in der Kontrollleiste
Exec=kalenderblick start
Icon=kalenderblick
Terminal=false
Categories=Office;Calendar;Utility;
StartupNotify=false
X-GNOME-Autostart-enabled=true
X-KDE-autostart-after=panel
"""


def ist_aktiv() -> bool:
    return paths.autostart_datei().exists()


def aktiviere() -> None:
    datei = paths.autostart_datei()
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(_INHALT, encoding="utf-8")


def deaktiviere() -> None:
    paths.autostart_datei().unlink(missing_ok=True)
