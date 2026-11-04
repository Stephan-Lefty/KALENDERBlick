"""Der Fall vom 04.11.2026: ein Termin morgen, der nächste erst in
15 Tagen - also knapp außerhalb der 14-Tage-Ansicht. Das Widget sah
dadurch aus, als fehlten Termine."""

import os
from datetime import date, datetime, timedelta

import pytest

pytest.importorskip("PyQt6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


def _termin(titel, tag, stunde=9):
    from kalenderblick.modell import Termin
    return Termin(kennung=titel, titel=titel,
                  beginn=datetime.combine(tag, datetime.min.time()).replace(hour=stunde),
                  ende=datetime.combine(tag, datetime.min.time()).replace(hour=stunde + 1),
                  kalender_id="k", kalender_name="Privat", farbe="#2ec27e")


def _texte(widget, app):
    """Alle Beschriftungen des Widgets.

    Darin steckt auch die Uhr-Anzeige, die als zweite Seite des
    Stapels immer im Baum hängt - deshalb wird hier auf Terminnamen
    geprüft und nicht auf die Gesamtzahl. processEvents, weil
    deleteLater() sonst erst später greift.
    """
    from PyQt6.QtWidgets import QLabel
    app.processEvents()
    return [k.text() for k in widget.findChildren(QLabel)]


def test_fusszeile_nennt_das_ende_des_zeitraums(qt_app):
    from kalenderblick.gui.liste import TerminListe
    heute = date.today()

    w = TerminListe(ansicht="14tage")
    w.setze_termine([_termin("Geburtstag", heute + timedelta(days=1)),
                     _termin("Tagung", heute + timedelta(days=15))])

    texte = " | ".join(_texte(w, qt_app))
    ende = heute + timedelta(days=13)

    assert "Geburtstag" in texte
    assert "Tagung" not in texte, "15 Tage voraus liegt außerhalb der 14-Tage-Ansicht"
    assert f"bis {ende:%d.%m.} keine weiteren" in texte, \
        "ohne diesen Hinweis wirkt die leere Fläche wie ein Fehler"
    assert f"nächster {heute + timedelta(days=15):%d.%m.}" in texte, \
        "der Termin knapp dahinter sollte wenigstens erwähnt werden"


def test_leere_ansicht_nennt_ebenfalls_das_datum(qt_app):
    from kalenderblick.gui.liste import TerminListe
    heute = date.today()

    w = TerminListe(ansicht="woche")
    w.setze_termine([_termin("Weit weg", heute + timedelta(days=40))])

    texte = " | ".join(_texte(w, qt_app))
    assert f"Bis {heute + timedelta(days=6):%d.%m.} keine Termine." in texte
    assert f"Nächster Termin am {heute + timedelta(days=40):%d.%m.}" in texte
    assert "Weit weg" in texte, "der Titel hilft mehr als ein bloßes Datum"


def test_naechste3_bekommt_keine_fusszeile(qt_app):
    """Dort gilt eine Anzahl, kein Zeitraum - ein Enddatum wäre gelogen."""
    from kalenderblick.gui.liste import TerminListe
    heute = date.today()

    w = TerminListe(ansicht="naechste3")
    w.setze_termine([_termin("A", heute + timedelta(days=1))])

    assert not any("keine weiteren" in t for t in _texte(w, qt_app))


def test_ohne_jeden_weiteren_termin_keine_falsche_zusage(qt_app):
    """Ist gar nichts mehr geladen, darf auch kein „nächster" erscheinen -
    sonst behauptete das Widget etwas, das es nicht weiß."""
    from kalenderblick.gui.liste import TerminListe

    w = TerminListe(ansicht="woche")
    w.setze_termine([])

    texte = " | ".join(_texte(w, qt_app))
    assert "keine Termine" in texte
    assert "ächster" not in texte
