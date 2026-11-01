from datetime import date, datetime, timedelta

import pytest

from hilfe import Profil, termin


@pytest.fixture
def profil(heim):
    p = Profil(heim)
    heute = date.today()
    ort = p.kalender("aaaa1111", "Privat", farbe="#2ec27e")
    termin(ort, "aaaa1111", "e1", "Zahnarzt",
           datetime(heute.year, heute.month, heute.day, 23, 30),
           datetime(heute.year, heute.month, heute.day, 23, 45), ort="Hauptstraße 3")
    morgen = heute + timedelta(days=1)
    termin(ort, "aaaa1111", "e2", "Urlaub",
           datetime(morgen.year, morgen.month, morgen.day),
           datetime(morgen.year, morgen.month, morgen.day), ganztags=True)
    p.kalender("bbbb2222", "Proton", art="ics", abholung=30)
    p.schreibe_prefs()
    return p


def test_hilfe(capsys):
    from kalenderblick.cli import main

    with pytest.raises(SystemExit) as abbruch:
        main(["--help"])
    assert abbruch.value.code == 0
    assert "Thunderbird" in capsys.readouterr().out


def test_pruefen_findet_profil_und_schema(profil, capsys):
    from kalenderblick.cli import main

    assert main(["pruefen"]) == 0
    ausgabe = capsys.readouterr().out
    assert "Gefundene Profile" in ausgabe
    assert "cal_events" in ausgabe
    assert "icalString" in ausgabe
    assert "aaaa1111.sqlite" in ausgabe


def test_pruefen_ohne_profil(heim, capsys):
    from kalenderblick.cli import main

    assert main(["pruefen"]) == 1
    assert "Kein Thunderbird-Profil gefunden" in capsys.readouterr().out


def test_kalender_zeigt_abholfrequenz(profil, capsys):
    from kalenderblick.cli import main

    assert main(["kalender"]) == 0
    ausgabe = capsys.readouterr().out
    assert "Proton" in ausgabe
    assert "30 Minuten" in ausgabe
    assert "örtlich gespeichert" in ausgabe
    assert "Zuletzt geschrieben" in ausgabe


def test_liste(profil, capsys):
    from kalenderblick.cli import main

    assert main(["liste", "--ausfuehrlich"]) == 0
    ausgabe = capsys.readouterr().out
    assert "HEUTE" in ausgabe
    assert "Zahnarzt" in ausgabe
    assert "[Privat]" in ausgabe
    assert "Hauptstraße 3" in ausgabe
    assert "ganztägig" in ausgabe


def test_naechster(profil, capsys):
    from kalenderblick.cli import main

    assert main(["naechster"]) == 0
    assert "Zahnarzt" in capsys.readouterr().out


def test_einstellungen_speichern(profil, capsys):
    from kalenderblick import config, paths
    from kalenderblick.cli import main

    assert main(["einstellungen", "--tage-voraus", "30",
                 "--verstecken", "bbbb2222"]) == 0
    assert paths.konfig_datei().exists()
    e = config.laden()
    assert e.tage_voraus == 30
    assert e.versteckte_kalender == ["bbbb2222"]

    assert main(["einstellungen", "--zeigen", "bbbb2222"]) == 0
    assert config.laden().versteckte_kalender == []


def test_unsinnige_einstellung_wird_abgelehnt(profil, capsys):
    from kalenderblick.cli import main

    assert main(["einstellungen", "--tage-voraus", "9999"]) == 2
    assert "Vorausblick" in capsys.readouterr().out


def test_symbole_sind_im_paket():
    from kalenderblick import bilder

    assert len(bilder.alle_symbole()) == len(bilder.GROESSEN)
    assert bilder.windows_symbol() is not None
    for datei in bilder.alle_symbole():
        assert datei.stat().st_size > 150
    # kleinere Anforderung bekommt die nächstgrößere Datei
    assert bilder.symbol_datei(20).name == "symbol-22.png"
    assert bilder.symbol_datei(1000).name == "symbol-512.png"
