#!/usr/bin/env python3
"""Erzeugt aus assets/icon.png alle Symbolgrößen und die Windows-Symboldatei.

    python packaging/symbole-erzeugen.py

Braucht Pillow:  pamac install python-pillow
"""

from pathlib import Path

from PIL import Image

GROESSEN = (16, 22, 24, 32, 48, 64, 128, 256, 512)
ICO = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> int:
    wurzel = Path(__file__).resolve().parent.parent
    symbol = Image.open(wurzel / "assets" / "icon.png").convert("RGBA")
    ziel = wurzel / "src" / "kalenderblick" / "bilder"
    ziel.mkdir(parents=True, exist_ok=True)
    for groesse in GROESSEN:
        symbol.resize((groesse, groesse), Image.LANCZOS).save(ziel / f"symbol-{groesse}.png")
    symbol.save(ziel / "symbol.ico", sizes=ICO)
    print(f"{len(GROESSEN)} Größen und symbol.ico geschrieben nach {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
