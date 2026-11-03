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
