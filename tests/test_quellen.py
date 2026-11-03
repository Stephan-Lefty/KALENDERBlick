"""Beide Kalenderprogramme unter einem Dach."""

from datetime import date, datetime, timedelta

import pytest

from hilfe import Profil, termin
from hilfe_evolution import EvolutionAblage

pytest.importorskip("icalendar")


@pytest.fixture
def nur_thunderbird(heim):
    p = Profil(heim)
    heute = date.today()
    v = p.kalender("tb001", "Thunderbird-Kalender")
    termin(v, "tb001", "t1", "Aus Thunderbird",
           datetime(heute.year, heute.month, heute.day, 9, 0),
           datetime(heute.year, heute.month, heute.day, 10, 0))
    p.schreibe_prefs()
    return p


@pytest.fixture
def nur_evolution(heim):
    a = EvolutionAblage(heim)
    heute = date.today()
    a.lege_kalender_an("ev001", "Evolution-Kalender")
    a.termin("ev001", "e1", "Aus Evolution",
             datetime(heute.year, heute.month, heute.day, 14, 0),
             datetime(heute.year, heute.month, heute.day, 15, 0))
    return a


# ----------------------------------------------------------------------

def test_lage_erkennt_gar_nichts(heim):
    from kalenderblick import quellen
    zustand = quellen.lage()
    assert not zustand.thunderbird
    assert not zustand.evolution
    assert not zustand.irgendwas


def test_lage_erkennt_nur_thunderbird(nur_thunderbird):
    from kalenderblick import quellen
    zustand = quellen.lage()
    assert zustand.thunderbird
    assert not zustand.evolution


def test_lage_erkennt_nur_evolution(nur_evolution):
    from kalenderblick import quellen
    zustand = quellen.lage()
    assert not zustand.thunderbird
    assert zustand.evolution


def test_ohne_jede_quelle_kommt_ein_sprechender_fehler(heim):
    from kalenderblick import quellen

    with pytest.raises(quellen.KeineQuelle) as fehler:
        quellen.lies_termine()
    text = str(fehler.value)
    assert "Thunderbird oder Evolution" in text
    assert "Kalenderquellen" in text


def test_termine_aus_evolution_allein(nur_evolution):
    from kalenderblick import quellen
    titel = {t.titel for t in quellen.lies_termine(tage_voraus=7)}
    assert "Aus Evolution" in titel


def test_termine_aus_thunderbird_allein(nur_thunderbird):
    from kalenderblick import quellen
    titel = {t.titel for t in quellen.lies_termine(tage_voraus=7)}
    assert "Aus Thunderbird" in titel


def test_beide_quellen_werden_zusammengefuehrt(heim):
    from kalenderblick import quellen

    heute = date.today()
    p = Profil(heim)
    v = p.kalender("tb001", "Thunderbird-Kalender")
    termin(v, "tb001", "t1", "Aus Thunderbird",
           datetime(heute.year, heute.month, heute.day, 9, 0),
           datetime(heute.year, heute.month, heute.day, 10, 0))
    p.schreibe_prefs()

    a = EvolutionAblage(heim)
    a.lege_kalender_an("ev001", "Evolution-Kalender")
    a.termin("ev001", "e1", "Aus Evolution",
             datetime(heute.year, heute.month, heute.day, 14, 0),
             datetime(heute.year, heute.month, heute.day, 15, 0))

    termine = quellen.lies_termine(tage_voraus=7)
    titel = [t.titel for t in termine]
    assert "Aus Thunderbird" in titel
    assert "Aus Evolution" in titel
    assert titel.index("Aus Thunderbird") < titel.index("Aus Evolution"), \
        "nicht nach Uhrzeit sortiert"


def test_auswahl_beschraenkt_die_quelle(heim):
    from kalenderblick import quellen

    heute = date.today()
    p = Profil(heim)
    v = p.kalender("tb001", "Thunderbird-Kalender")
    termin(v, "tb001", "t1", "Aus Thunderbird",
           datetime(heute.year, heute.month, heute.day, 9, 0),
           datetime(heute.year, heute.month, heute.day, 10, 0))
    p.schreibe_prefs()

    a = EvolutionAblage(heim)
    a.lege_kalender_an("ev001", "Evolution-Kalender")
    a.termin("ev001", "e1", "Aus Evolution",
             datetime(heute.year, heute.month, heute.day, 14, 0),
             datetime(heute.year, heute.month, heute.day, 15, 0))

    nur_tb = {t.titel for t in quellen.lies_termine(quellen.NUR_THUNDERBIRD,
                                                    tage_voraus=7)}
    assert nur_tb == {"Aus Thunderbird"}

    nur_ev = {t.titel for t in quellen.lies_termine(quellen.NUR_EVOLUTION,
                                                    tage_voraus=7)}
    assert nur_ev == {"Aus Evolution"}


def test_eine_kaputte_quelle_verdeckt_die_andere_nicht(nur_evolution, monkeypatch):
    """Fällt Thunderbird aus, sollen die Evolution-Termine trotzdem
    erscheinen - eine leere Liste samt Fehler wäre schlechter."""
    from kalenderblick import quellen, thunderbird

    monkeypatch.setattr(thunderbird, "waehle_profil",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("kaputt")))

    titel = {t.titel for t in quellen.lies_termine(tage_voraus=7)}
    assert "Aus Evolution" in titel


def test_kalenderliste_fuehrt_beide_zusammen(heim):
    from kalenderblick import quellen

    p = Profil(heim)
    p.kalender("tb001", "Thunderbird-Kalender")
    p.schreibe_prefs()
    a = EvolutionAblage(heim)
    a.lege_kalender_an("ev001", "Evolution-Kalender")

    namen = {k.name for k in quellen.lies_kalender()}
    assert "Thunderbird-Kalender" in namen
    assert "Evolution-Kalender" in namen
