"""Einzelne Kalender abwählen - nur für die Anzeige.

Die Auswahl verändert nichts am Kalenderprogramm selbst: In Thunderbird
bleibt alles sichtbar, KALENDERBlick überspringt die abgewählten nur
beim Anzeigen.
"""

from datetime import date, datetime

import pytest

from hilfe import Profil, termin

from kalenderblick import config, thunderbird


@pytest.fixture
def drei_kalender(heim):
    p = Profil(heim)
    heute = date.today()
    for kennung, name in (("k1", "Privat"), ("k2", "Arbeit"), ("k3", "Feiertage")):
        v = p.kalender(kennung, name)
        termin(v, kennung, f"e-{kennung}", f"Termin {name}",
               datetime(heute.year, heute.month, heute.day, 9, 0),
               datetime(heute.year, heute.month, heute.day, 10, 0))
    p.schreibe_prefs()
    return p


def test_ohne_auswahl_sind_alle_dabei(drei_kalender):
    termine = thunderbird.lies_termine(drei_kalender.profil, tage_voraus=7)
    assert {t.kalender_name for t in termine} == {"Privat", "Arbeit", "Feiertage"}


def test_abgewaehlter_kalender_verschwindet(drei_kalender):
    termine = thunderbird.lies_termine(
        drei_kalender.profil, tage_voraus=7, versteckt=["k2"])
    namen = {t.kalender_name for t in termine}
    assert "Arbeit" not in namen
    assert namen == {"Privat", "Feiertage"}


def test_auswahl_laesst_die_kalenderdateien_unberuehrt(drei_kalender):
    """Entscheidend: In Thunderbird muss alles sichtbar bleiben."""
    dateien = thunderbird.kalenderdateien(drei_kalender.profil)
    vorher = {d: (d.stat().st_size, d.stat().st_mtime_ns) for d in dateien}

    thunderbird.lies_termine(drei_kalender.profil, tage_voraus=7,
                             versteckt=["k1", "k2", "k3"])

    nachher = {d: (d.stat().st_size, d.stat().st_mtime_ns) for d in dateien}
    assert vorher == nachher, "an den Kalenderdateien wurde etwas verändert"

    # Und die prefs.js, in der Thunderbird seine eigene Sichtbarkeit führt
    prefs = drei_kalender.profil / "prefs.js"
    assert "disabled" not in prefs.read_text(encoding="utf-8"), \
        "in Thunderbirds eigener Einstellung wurde etwas abgeschaltet"


def test_auswahl_wird_gespeichert(heim):
    e = config.laden()
    e.versteckte_kalender = ["k2", "k3"]
    e.speichern()
    assert config.laden().versteckte_kalender == ["k2", "k3"]
