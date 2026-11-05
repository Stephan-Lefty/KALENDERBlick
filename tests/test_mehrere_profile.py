"""Mehrere Thunderbird-Profile.

Wer privat und beruflich trennt, hat zwei Profile mit Terminen.
KALENDERBlick nimmt davon eines - das darf es nicht wortlos tun,
sonst sucht jemand die fehlenden Termine im falschen Programm.
"""

import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from hilfe import Profil, termin


def _zweites_profil(heim: Path, name: str, mit_terminen: bool) -> Path:
    """Ein zweites Profil neben dem ersten, in dieselbe profiles.ini."""
    ordner = heim / ".thunderbird" / f"{name}.weiteres"
    (ordner / "calendar-data").mkdir(parents=True)

    ini = heim / ".thunderbird" / "profiles.ini"
    ini.write_text(ini.read_text(encoding="utf-8")
                   + f"\n[Profile1]\nName={name}\nIsRelative=1\n"
                     f"Path={name}.weiteres\nDefault=0\n",
                   encoding="utf-8")

    datei = ordner / "calendar-data" / "local.sqlite"
    v = sqlite3.connect(datei)
    from hilfe import SCHEMA
    v.executescript(SCHEMA)
    if mit_terminen:
        heute = date.today()
        termin(v, "zzzz9999", "z1", "Aus dem zweiten Profil",
               datetime(heute.year, heute.month, heute.day, 10, 0),
               datetime(heute.year, heute.month, heute.day, 11, 0))
    v.commit()
    v.close()
    return ordner


@pytest.fixture
def erstes(heim):
    p = Profil(heim)
    heute = date.today()
    v = p.kalender("aaaa1111", "Privat")
    termin(v, "aaaa1111", "e1", "Im ersten Profil",
           datetime(heute.year, heute.month, heute.day, 9, 0),
           datetime(heute.year, heute.month, heute.day, 10, 0))
    p.schreibe_prefs()
    return p


def test_ein_einziges_profil_meldet_keine_weiteren(erstes):
    from kalenderblick import thunderbird
    assert thunderbird.weitere_profile_mit_terminen() == 0


def test_zweites_profil_mit_terminen_wird_gemeldet(erstes, heim):
    from kalenderblick import thunderbird
    _zweites_profil(heim, "arbeit", mit_terminen=True)
    assert thunderbird.weitere_profile_mit_terminen() == 1


def test_leeres_zweitprofil_zaehlt_nicht(erstes, heim):
    """Ein angelegtes, aber ungenutztes Profil ist kein Grund für einen
    Hinweis - sonst warnt das Programm bei jedem Testprofil."""
    from kalenderblick import thunderbird
    _zweites_profil(heim, "leer", mit_terminen=False)
    assert thunderbird.weitere_profile_mit_terminen() == 0


def test_bei_eigener_angabe_kein_hinweis(erstes, heim):
    """Wer das Profil selbst gewählt hat, weiß Bescheid."""
    from kalenderblick import thunderbird
    _zweites_profil(heim, "arbeit", mit_terminen=True)
    assert thunderbird.weitere_profile_mit_terminen(str(erstes.profil)) == 0


def test_gewaehlt_wird_das_startprofil(erstes, heim):
    """Thunderbirds eigene Vorgabe hat Vorrang - auch wenn das andere
    Profil mehr Termine enthält."""
    from kalenderblick import thunderbird
    zweites = _zweites_profil(heim, "arbeit", mit_terminen=True)
    gewaehlt = thunderbird.waehle_profil()
    assert gewaehlt == erstes.profil, f"nicht das Startprofil, sondern {gewaehlt}"
    assert gewaehlt != zweites
