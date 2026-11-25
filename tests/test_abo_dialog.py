"""Der Abo-Dialog muss von selbst groß genug aufgehen.

Ein umbrechendes Textfeld meldet seine Höhe zu klein, solange die Breite
noch nicht feststeht - der Erklärungstext wurde dadurch von den
Eingabefeldern überdeckt. Bei größerer Systemschrift fällt das sofort
auf, bei kleiner gar nicht; deshalb wird hier beides geprüft.
"""

import os

import pytest

pytest.importorskip("PyQt6.QtWidgets")
pytest.importorskip("icalendar")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _text_passt(dialog) -> tuple[int, int]:
    """(vorhandene Höhe, benötigte Höhe) des Erklärungstextes."""
    from PyQt6.QtWidgets import QLabel
    label = dialog.findChildren(QLabel)[0]
    rand = 2 * dialog.layout().contentsMargins().left()
    return label.height(), label.heightForWidth(dialog.width() - rand)


@pytest.mark.parametrize("schriftgroesse", [9, 11, 14, 18])
def test_erklaerungstext_passt_bei_jeder_schriftgroesse(qt_app, schriftgroesse):
    from kalenderblick.gui.fenster import _AboDialog

    schrift = qt_app.font()
    vorher = schrift.pointSize()
    schrift.setPointSize(schriftgroesse)
    qt_app.setFont(schrift)
    try:
        dialog = _AboDialog()
        dialog.show()
        vorhanden, benoetigt = _text_passt(dialog)
        assert vorhanden >= benoetigt, (
            f"bei {schriftgroesse}pt fehlen {benoetigt - vorhanden} px - "
            "der Text wird von den Eingabefeldern überdeckt")
        dialog.close()
    finally:
        schrift.setPointSize(vorher)
        qt_app.setFont(schrift)


def test_dialog_ist_breit_genug_zum_lesen(qt_app):
    from kalenderblick.gui.fenster import _AboDialog

    dialog = _AboDialog()
    dialog.show()
    assert dialog.width() >= 500, "zu schmal, der Text würde zur Bleiwüste"
    dialog.close()


def test_falsche_adresse_wird_ohne_netzzugriff_gemeldet(qt_app, monkeypatch):
    """**Kein Abruf, wenn die Adressart schon erkennbar falsch ist.**

    Am 07.11.2026 trug Stephan die Browser-Adresse seines
    Google-Kalenders ein. Der Dialog rief sie ab, Google antwortete mit
    einer Anmeldeseite, und im Hinweisfeld landeten fünfzig Zeilen HTML
    und CSS. Jetzt steht dort sofort, welche Adresse gebraucht wird -
    und das Netz wird gar nicht erst bemüht.
    """
    from kalenderblick import ics_abo
    from kalenderblick.gui.fenster import _AboDialog

    def nicht_abrufen(*a, **k):
        raise AssertionError("es wurde trotzdem abgerufen")

    monkeypatch.setattr(ics_abo, "hole", nicht_abrufen)

    dialog = _AboDialog()
    dialog._name.setText("Google Kalender")
    dialog._url.setText("https://calendar.google.com/calendar/u/0?cid=abc123")
    dialog._pruefen_und_schliessen()

    hinweis = dialog._hinweis.text()
    assert ".ics" in hinweis, f"der Hinweis hilft nicht weiter: {hinweis!r}"
    assert len(hinweis) < 300
    assert dialog.result() != dialog.DialogCode.Accepted, \
        "der Dialog hat die falsche Adresse angenommen"
