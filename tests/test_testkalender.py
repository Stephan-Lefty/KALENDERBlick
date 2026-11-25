"""Legt werkzeuge/testkalender.py ein Profil an, das auch auffindbar ist?

Der erste Anlauf baute Thunderbirds echte Struktur nach - also
`.thunderbird/test.default` unter dem Zielordner. Technisch lief alles,
die Termine standen in der Datenbank und wurden gelesen. Nur sah
Stephan im Dateimanager einen leeren Ordner, denn ein Name mit Punkt
am Anfang ist versteckt, und der Auswahldialog zeigt ihn genauso
wenig. Deshalb prüft der erste Test hier nicht die Termine, sondern
ob überhaupt etwas zu sehen ist.
"""

import importlib.util
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

from kalenderblick import thunderbird

WERKZEUG = Path(__file__).resolve().parent.parent / "werkzeuge" / "testkalender.py"


def _lade():
    spec = importlib.util.spec_from_file_location("testkalender", WERKZEUG)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture
def angelegt(tmp_path):
    ziel = tmp_path / "Testkalender"
    ergebnis = subprocess.run(
        [sys.executable, str(WERKZEUG), str(ziel)],
        capture_output=True, text=True, timeout=120)
    assert ergebnis.returncode == 0, ergebnis.stderr
    return ziel, ergebnis.stdout


def test_zielordner_ist_nicht_leer_fuer_den_dateimanager(angelegt):
    """Kein Eintrag mit Punkt am Anfang - sonst wirkt der Ordner leer."""
    ziel, _ = angelegt
    sichtbar = [p.name for p in ziel.iterdir() if not p.name.startswith(".")]
    assert sichtbar, (
        "Der Zielordner enthält nur versteckte Einträge und sieht damit "
        "im Dateimanager und im Auswahldialog leer aus.")


def test_auch_der_profilordner_ist_sichtbar(angelegt):
    """Der Pfad, den man auswählen soll, muss anklickbar sein."""
    ziel, ausgabe = angelegt
    profil = next(p for p in ziel.iterdir()
                  if p.is_dir() and not p.name.startswith("."))
    assert not any(teil.startswith(".")
                   for teil in profil.relative_to(ziel).parts)
    assert str(profil) in ausgabe, "Der Profilpfad fehlt in der Ausgabe."


def test_liesmich_nennt_den_auszuwaehlenden_pfad(angelegt):
    ziel, _ = angelegt
    text = (ziel / "LIESMICH.txt").read_text(encoding="utf-8")
    assert "Kalenderquellen" in text
    assert str(ziel / "profil") in text


def test_kalenderblick_findet_die_drei_kalender(angelegt):
    ziel, _ = angelegt
    namen = [k.name for k in thunderbird.lies_kalender(ziel / "profil")]
    assert sorted(namen) == ["Arbeit", "Familie", "Privat"]


def test_termine_liegen_in_den_naechsten_drei_wochen(angelegt):
    """Die Zusage lautet drei Wochen - und die 14-Tage-Ansicht braucht viele."""
    ziel, _ = angelegt
    profil = ziel / "profil"
    assert len(thunderbird.lies_termine(profil, tage_voraus=1)) >= 3
    in_vierzehn = thunderbird.lies_termine(profil, tage_voraus=14)
    assert len(in_vierzehn) >= 20
    assert len(thunderbird.lies_termine(profil, tage_voraus=21)) > len(in_vierzehn)

    heute = date.today()
    for termin in in_vierzehn:
        assert heute <= termin.tag <= heute + timedelta(days=14)


def test_ganztagstermine_sind_dabei(angelegt):
    """Ganztags läuft im Widget durch einen eigenen Zweig."""
    ziel, _ = angelegt
    termine = thunderbird.lies_termine(ziel / "profil", tage_voraus=21)
    assert any(t.ganztags for t in termine)
    assert any(not t.ganztags for t in termine)


def test_vorhandener_ordner_wird_nicht_ueberschrieben(tmp_path):
    ziel = tmp_path / "schon_da"
    ziel.mkdir()
    (ziel / "wichtig.txt").write_text("nicht anfassen", encoding="utf-8")
    ergebnis = subprocess.run(
        [sys.executable, str(WERKZEUG), str(ziel)],
        capture_output=True, text=True, timeout=120)
    assert ergebnis.returncode == 1
    assert (ziel / "wichtig.txt").read_text(encoding="utf-8") == "nicht anfassen"


def test_keine_echten_daten_in_den_terminen():
    """Erfundene Namen und Orte - Bildschirmfotos landen irgendwann öffentlich."""
    modul = _lade()
    text = " ".join(
        eintrag[-2] + " " + eintrag[-1]
        for eintrag in modul.ARBEIT + modul.PRIVAT + modul.GANZTAGS)
    assert "@" not in text
    assert "habefa" not in text.lower()
    assert "roesner" not in text.lower()
