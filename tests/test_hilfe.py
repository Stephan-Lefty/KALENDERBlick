"""Die Anleitung muss im Paket liegen, sonst ist die Hilfe im Programm leer."""

import pytest

from kalenderblick import hilfe


def test_anleitung_wird_mitgeliefert():
    assert hilfe.anleitung_datei() is not None, \
        "anleitung.md fehlt im Paket - die Hilfe im Programm bliebe leer"


def test_anleitung_hat_inhalt():
    text = hilfe.anleitung_text()
    assert text is not None
    assert "Voraussetzungen" in text
    assert "Wenn etwas nicht passt" in text


def test_bildschirmfotos_werden_mitgeliefert():
    bilder = hilfe.bild_dateien()
    assert len(bilder) >= 10, f"nur {len(bilder)} Bildschirmfotos gefunden"


def test_jedes_bild_aus_der_anleitung_ist_vorhanden():
    """Verweist die Anleitung auf eine Datei, muss es sie auch geben -
    sonst bleiben in der Hilfe graue Lücken statt Bildern."""
    text = hilfe.anleitung_text()
    verwiesen = set()
    for teil in text.split("](bilder/")[1:]:
        verwiesen.add(teil.split(")")[0])
    vorhanden = {p.name for p in hilfe.bild_dateien()}
    fehlend = verwiesen - vorhanden
    assert not fehlend, f"in der Anleitung verwiesen, aber nicht vorhanden: {fehlend}"


def test_img_elemente_werden_zu_markdown_bildern():
    """Qt übergeht <img>-Elemente - sie müssen umgeschrieben ankommen."""
    text = hilfe.anleitung_text()
    assert "<img" not in text, "es blieben <img>-Elemente stehen, Qt zeigt sie nicht"
    assert text.count("](bilder/") >= 10


def test_kein_html_block_bleibt_stehen():
    """HTML-Blöcke zeigt Qt in Markdown als Rohtext an - der mittig
    gesetzte Logo-Block am Anfang muss deshalb entfernt sein."""
    text = hilfe.anleitung_text()
    assert "<p align" not in text
    assert "assets/" not in text, \
        "Verweis auf assets/ - liegt nicht im Paket, bliebe eine leere Stelle"

