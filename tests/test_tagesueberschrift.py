"""Die Überschrift über einem Tagesblock.

Bis November 2026 stand bei den Tagen der laufenden Woche nur der
Wochentag, bei ferneren das volle Datum. Zwei Formen nebeneinander, von
denen die eine zu wenig sagte: „Mittwoch" beantwortet nicht, der
wievielte das ist - und wer einen Termin absagen oder eintragen will,
braucht die Zahl.
"""

import os
from datetime import date, timedelta

import pytest

from kalenderblick.modell import tagesueberschrift

HEUTE = date(2026, 11, 5)          # ein Donnerstag


def test_jeder_tag_traegt_ein_datum():
    """Der eigentliche Punkt: keine Überschrift ohne Zahl."""
    for versatz in range(-1, 40):
        tag = HEUTE + timedelta(days=versatz)
        text = tagesueberschrift(tag, HEUTE)
        assert str(tag.day) in text, f"kein Datum in {text!r}"


def test_die_laufende_woche_zeigt_es_auch():
    """Genau hier fehlte es - Tag 2 bis 6 lieferten nur den Wochentag."""
    assert tagesueberschrift(HEUTE + timedelta(days=3), HEUTE) == "Sonntag, 8. November"


def test_heute_und_morgen_behalten_ihren_namen():
    """„Heute" sagt mehr als „Donnerstag" - das Datum kommt dazu, nicht
    an seine Stelle."""
    assert tagesueberschrift(HEUTE, HEUTE) == "Heute, 5. November"
    assert tagesueberschrift(HEUTE + timedelta(days=1), HEUTE) == "Morgen, 6. November"
    assert tagesueberschrift(HEUTE - timedelta(days=1), HEUTE) == "Gestern, 4. November"


def test_kein_jahr():
    """Es steht ohnehin fest und kostet nur Platz."""
    for versatz in (0, 5, 60, 300):
        text = tagesueberschrift(HEUTE + timedelta(days=versatz), HEUTE)
        assert "2026" not in text and "2027" not in text


def test_die_kurzform_kuerzt_beides():
    assert tagesueberschrift(HEUTE + timedelta(days=3), HEUTE, kurz=True) == "So, 8.11."
    assert tagesueberschrift(HEUTE, HEUTE, kurz=True) == "Heute, 5.11."


def test_kurze_wochentage_bleiben_unterscheidbar():
    """Mit einem Buchstaben fielen Montag/Mittwoch und
    Dienstag/Donnerstag zusammen."""
    from kalenderblick.modell import WOCHENTAGE_KURZ
    assert len(set(WOCHENTAGE_KURZ)) == 7


# ----------------------------------------------------------------------
#  Die Anzeige wählt nach Platz
# ----------------------------------------------------------------------

pytest.importorskip("PyQt6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    yield QApplication.instance() or QApplication([])


def test_viel_platz_nimmt_die_lange_form(qt_app):
    from kalenderblick.gui.liste import _passende_ueberschrift
    text = _passende_ueberschrift(date(2026, 11, 15), 9, platz=600)
    assert "November" in text


def test_wenig_platz_nimmt_die_kurze(qt_app):
    """Im kleinsten Widget (220 px) passt die ausgeschriebene Form ab
    14 pt nicht mehr - dann lieber kürzen als abschneiden."""
    from kalenderblick.gui.liste import _passende_ueberschrift
    text = _passende_ueberschrift(date(2026, 11, 15), 14, platz=190)
    assert "November" not in text
    assert "15.11." in text


def test_ohne_angabe_bleibt_es_lang(qt_app):
    """platz=0 heißt „unbekannt" - im Hauptfenster ist immer Raum."""
    from kalenderblick.gui.liste import _passende_ueberschrift
    assert "November" in _passende_ueberschrift(date(2026, 11, 15), 9, platz=0)
