"""Findet die mitgelieferte Anleitung - ohne Qt, damit auch Tests darankommen.

Die Anleitung liegt bewusst im Paket und nicht nur im Projektordner: So ist
sie nach jeder Installationsart vorhanden und lässt sich ohne Internet im
Programm selbst lesen.
"""

from __future__ import annotations

import re
from pathlib import Path

ORDNER = Path(__file__).resolve().parent
BILDER = ORDNER / "bilder"

# Die Anleitung bettet die Bildschirmfotos als <img>-Element ein, weil
# GitHub nur darüber die Anzeigebreite steuern lässt. Qts Markdown-
# Darstellung übergeht solche Elemente stillschweigend - für die Anzeige
# im Programm werden sie deshalb in gewöhnliche Markdown-Bilder
# umgeschrieben.
_IMG = re.compile(r'<img\s+src="([^"]+)"[^>]*alt="([^"]*)"[^>]*/?>')

# Die Anleitung beginnt mit dem mittig gesetzten Programmsymbol. Dieser
# Block muss weg, bevor der Rest umgeschrieben wird: Qt zeigt HTML-Blöcke
# in Markdown unverändert als Rohtext an, und das Symbol liegt zudem unter
# assets/ im Projektordner, nicht im Paket - es wäre also ohnehin nur eine
# leere Stelle. Im Programm steht das Symbol ja ohnehin schon im Fenster.
_LOGOBLOCK = re.compile(r'<p align="center">\s*<img[^>]*>\s*</p>\s*', re.IGNORECASE)


def _als_markdown_bilder(text: str) -> str:
    return _IMG.sub(r'![\2](\1)', _LOGOBLOCK.sub("", text))


def anleitung_datei() -> Path | None:
    datei = ORDNER / "anleitung.md"
    return datei if datei.exists() else None


def anleitung_text() -> str | None:
    """Die Anleitung, bereit zur Darstellung durch Qt."""
    datei = anleitung_datei()
    if datei is None:
        return None
    try:
        return _als_markdown_bilder(datei.read_text(encoding="utf-8"))
    except OSError:
        return None


def bild_dateien() -> list[Path]:
    if not BILDER.is_dir():
        return []
    return sorted(BILDER.glob("*.png"))


_CSS = """
body { font-family: sans-serif; line-height: 1.55; max-width: 48em;
       margin: 2em auto; padding: 0 1.2em; color: #222; }
h1, h2, h3 { line-height: 1.25; margin-top: 1.6em; }
h1 { border-bottom: 2px solid #3584e4; padding-bottom: .2em; }
h2 { border-bottom: 1px solid #ddd; padding-bottom: .15em; }
img { max-width: 100%; height: auto; border: 1px solid #ddd;
      border-radius: 6px; margin: .4em .6em .4em 0; }
code, tt { background: #f4f4f4; padding: .1em .35em; border-radius: 3px; }
pre { background: #f4f4f4; padding: .8em 1em; border-radius: 6px;
      overflow-x: auto; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: .5em .7em; text-align: left;
         vertical-align: top; }
th { background: #f4f4f4; }
a { color: #1a5fb4; }
@media (prefers-color-scheme: dark) {
  body { background: #1e1e1e; color: #e4e4e4; }
  h2 { border-bottom-color: #444; }
  code, tt, pre, th { background: #2a2a2a; }
  th, td { border-color: #444; }
  img { border-color: #444; }
  a { color: #78aeed; }
}
"""


def als_html() -> str | None:
    """Die Anleitung als eigenständige HTML-Seite für den Browser.

    Gewandelt wird mit Qt; die Bildverweise werden auf absolute Pfade
    gelegt, damit die Seite auch außerhalb dieses Ordners funktioniert.
    """
    text = anleitung_text()
    if text is None:
        return None

    from PyQt6.QtGui import QTextDocument

    doc = QTextDocument()
    doc.setMarkdown(text)
    rumpf = doc.toHtml()

    # Qt schreibt einen eigenen Kopf mit eigenen Schriftvorgaben; für die
    # Anzeige im Browser zählt nur der Inhalt zwischen den body-Marken.
    start = rumpf.find("<body")
    if start != -1:
        start = rumpf.find(">", start) + 1
        ende = rumpf.rfind("</body>")
        rumpf = rumpf[start:ende if ende != -1 else len(rumpf)]

    rumpf = rumpf.replace('src="bilder/', f'src="{BILDER.as_uri()}/')

    return (
        "<!doctype html>\n<html lang=\"de\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<title>KALENDERBlick – Anleitung</title>\n"
        f"<style>{_CSS}</style>\n</head>\n<body>\n{rumpf}\n</body>\n</html>\n"
    )
