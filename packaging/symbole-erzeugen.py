#!/usr/bin/env python3
"""Erzeugt aus assets/icon.png und assets/icon-klein.png alle Symbolgrößen
und die Windows-Symboldatei.

16-32 Pixel (Kontrollleiste) kommen aus icon-klein.png (ohne Namenszug -
bei der Größe ohnehin nicht mehr lesbar), 48 Pixel aufwärts aus icon.png
(mit Namenszug). symbol.ico bleibt bei der textlosen Fassung, weil seine
Größen überwiegend klein sind.

    python packaging/symbole-erzeugen.py

Braucht Pillow:  pamac install python-pillow
"""

from pathlib import Path

from PIL import Image

GRENZE_OHNE_TEXT = 32   # bis einschließlich dieser Größe: icon-klein.png
GROESSEN = (16, 22, 24, 32, 48, 64, 128, 256, 512)
ICO = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def main() -> int:
    wurzel = Path(__file__).resolve().parent.parent
    assets = wurzel / "assets"
    gross = Image.open(assets / "icon.png").convert("RGBA")
    klein = Image.open(assets / "icon-klein.png").convert("RGBA")
    ziel = wurzel / "src" / "kalenderblick" / "bilder"
    ziel.mkdir(parents=True, exist_ok=True)
    for groesse in GROESSEN:
        quelle = klein if groesse <= GRENZE_OHNE_TEXT else gross
        quelle.resize((groesse, groesse), Image.LANCZOS).save(ziel / f"symbol-{groesse}.png")
    klein.save(ziel / "symbol.ico", sizes=ICO)
    print(f"{len(GROESSEN)} Größen und symbol.ico geschrieben nach {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
