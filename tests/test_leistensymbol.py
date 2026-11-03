"""Das Leistensymbol muss mehrere Auflösungen mitbringen.

Mit nur einer Auflösung rechnet die Kontrollleiste das Bild selbst um,
und die Linien werden unscharf - unter Cinnamon/X11 war das deutlich zu
sehen. Diese Tests brauchen Qt und werden übersprungen, wo es fehlt (die
CI installiert es nicht).
"""

import os

import pytest

pytest.importorskip("PyQt6.QtWidgets")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def termin():
    from datetime import datetime, timedelta
    from kalenderblick.modell import Termin
    beginn = datetime.now() + timedelta(hours=2)
    return Termin(titel="Beispiel", beginn=beginn, ende=beginn + timedelta(hours=1))


def test_symbol_bietet_alle_leistengroessen(qt_app, termin):
    from kalenderblick.gui.gemeinsam import symbol_mit_naechstem_termin, _LEISTENGROESSEN

    icon = symbol_mit_naechstem_termin(termin)
    vorhanden = {s.width() for s in icon.availableSizes()}
    fehlend = set(_LEISTENGROESSEN) - vorhanden
    assert not fehlend, f"diese Größen fehlen, die Leiste müsste rechnen: {sorted(fehlend)}"


def test_symbol_ohne_termin_bietet_ebenfalls_alle_groessen(qt_app):
    from kalenderblick.gui.gemeinsam import symbol_mit_naechstem_termin, _LEISTENGROESSEN

    icon = symbol_mit_naechstem_termin(None)
    vorhanden = {s.width() for s in icon.availableSizes()}
    assert set(_LEISTENGROESSEN) <= vorhanden


def test_kleine_groessen_bleiben_nicht_leer(qt_app, termin):
    """Jede Größe muss tatsächlich gezeichnet sein - ein durchsichtiges
    Bild wäre in der Leiste schlicht unsichtbar."""
    from kalenderblick.gui.gemeinsam import symbol_mit_naechstem_termin

    icon = symbol_mit_naechstem_termin(termin)
    for groesse in (16, 22, 24):
        bild = icon.pixmap(groesse, groesse).toImage()
        sichtbar = any(
            bild.pixelColor(x, y).alpha() > 0
            for x in range(bild.width()) for y in range(bild.height())
        )
        assert sichtbar, f"das {groesse}px-Symbol ist vollständig durchsichtig"
