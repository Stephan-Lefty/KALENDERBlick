"""Erkennung von X11/Wayland und KDE/GNOME/Cinnamon - ganz ohne Qt, damit
auch Module, die das nur zur Weichenstellung brauchen (z. B. position.py),
in Tests nicht PyQt6 mitziehen müssen."""

from __future__ import annotations

import os


def umgebung() -> dict:
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
