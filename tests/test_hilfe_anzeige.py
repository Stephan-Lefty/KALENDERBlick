"""Die Hilfe muss die Bildschirmfotos auch wirklich darstellen.

Diese Prüfung hätte den Fehler gefunden, dass setMarkdown() zuvor
eingehängte Bilder wieder verwirft: Die Bildstellen waren vorhanden,
nur ohne Bilddaten dahinter - also leere Lücken. Es genügt deshalb
nicht, bloß die Bildstellen zu zählen.

Braucht Qt und wird übersprungen, wo es fehlt (die CI installiert es
nicht).
"""

import os

import pytest

pytest.importorskip("PyQt6.QtWidgets")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    """Muss modulweit bestehen bleiben - wird die Anwendung zwischendurch
    eingesammelt, stürzt Qt beim Anlegen weiterer Widgets ab."""
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture(scope="module")
def hilfe_reiter(qt_app):
    from kalenderblick.gui.fenster import _HilfeReiter
    reiter = _HilfeReiter()
    yield reiter


def _bildstellen(doc):
    """(Anzahl insgesamt, Anzahl ohne hinterlegte Bilddaten)"""
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QTextDocument

    gesamt = ohne_daten = 0
    block = doc.begin()
    while block.isValid():
        stueck = block.begin()
        while not stueck.atEnd():
            format_ = stueck.fragment().charFormat()
            if format_.isImageFormat():
                gesamt += 1
                name = format_.toImageFormat().name()
                res = doc.resource(QTextDocument.ResourceType.ImageResource, QUrl(name))
                if res is None or (hasattr(res, "isNull") and res.isNull()):
                    ohne_daten += 1
            stueck += 1
        block = block.next()
    return gesamt, ohne_daten


def test_alle_bildstellen_haben_bilddaten(hilfe_reiter):
    gesamt, ohne_daten = _bildstellen(hilfe_reiter._browser.document())
    assert gesamt >= 10, f"nur {gesamt} Bildstellen in der Hilfe"
    assert ohne_daten == 0, \
        f"{ohne_daten} von {gesamt} Bildstellen ohne Bilddaten - sie blieben leer"


def test_anleitung_beginnt_nicht_mit_rohem_html(hilfe_reiter):
    anfang = hilfe_reiter._browser.document().toPlainText().strip()[:60]
    assert "<p align" not in anfang
    assert "![" not in anfang, f"roher Markdown-Text sichtbar: {anfang!r}"


def test_html_fassung_bindet_die_bilder_absolut_ein(qt_app):
    from kalenderblick import hilfe

    html = hilfe.als_html()
    assert html is not None
    assert html.count("file://") >= 10, \
        "ohne absolute Pfade zeigt der Browser keine Bilder"
