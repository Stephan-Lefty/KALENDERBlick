"""Beim Einschalten des Schreibtischwidgets sagen, wo es liegt.

Es liegt bewusst hinter allen anderen Fenstern. Wer es gerade
eingeschaltet hat und einen vollen Bildschirm vor sich hat, sieht
deshalb nichts und hält es für kaputt.
"""

import os

import pytest

pytest.importorskip("PyQt6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture
def hinweis():
    from kalenderblick.gui.fenster import _EinstellungenReiter
    return _EinstellungenReiter._widget_lage_hinweis


def test_einschalten_erklaert_die_lage(hinweis):
    text = hinweis(False, True)
    assert "hinter allen Fenstern" in text
    assert "minimieren" in text, "ohne den Rat bleibt es bei der Feststellung"


def test_war_schon_an_wiederholt_nichts(hinweis):
    """Wer nur die Transparenz ändert, braucht die Erklärung nicht
    jedes Mal."""
    assert hinweis(True, True) == ""


def test_ausschalten_bringt_keinen_hinweis(hinweis):
    assert hinweis(True, False) == ""


def test_bleibt_aus_bringt_keinen_hinweis(hinweis):
    assert hinweis(False, False) == ""
