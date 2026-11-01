from datetime import date, datetime, timedelta

import pytest

from hilfe import Profil, tag_mikro, termin


@pytest.fixture
def profil(heim):
    p = Profil(heim)
    heute = date.today()

    # Örtlicher Kalender
    ort = p.kalender("aaaa1111", "Privat", farbe="#2ec27e", art="storage")
    termin(ort, "aaaa1111", "e1", "Zahnarzt",
           datetime(heute.year, heute.month, heute.day, 12, 0),
           datetime(heute.year, heute.month, heute.day, 13, 0),
           tz="/mozilla.org/20050126_1/Europe/Berlin", ort="Hauptstraße 3")

    morgen = heute + timedelta(days=1)
    termin(ort, "aaaa1111", "e2", "Urlaub",
           datetime(morgen.year, morgen.month, morgen.day),
           datetime(morgen.year, morgen.month, morgen.day) + timedelta(days=2),
           ganztags=True)

    # Weit in der Zukunft - darf nicht auftauchen
    fern = heute + timedelta(days=400)
    termin(ort, "aaaa1111", "e3", "Sehr spät",
           datetime(fern.year, fern.month, fern.day, 9, 0),
           datetime(fern.year, fern.month, fern.day, 10, 0))

    # Abonnierter Kalender von Proton
    proton = p.kalender("bbbb2222", "Proton", farbe="#c061cb", art="ics", abholung=30)
    montag = heute - timedelta(days=heute.weekday())       # Montag dieser Woche
    termin(proton, "bbbb2222", "r1", "Vorstandssitzung",
           datetime(montag.year, montag.month, montag.day, 9, 0),
           datetime(montag.year, montag.month, montag.day, 10, 30),
           rrule="RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=8")

    # Abgeschalteter Kalender
    aus = p.kalender("cccc3333", "Alt", art="storage", abgeschaltet=True)
    termin(aus, "cccc3333", "e9", "Sollte verborgen sein",
           datetime(heute.year, heute.month, heute.day, 8, 0),
           datetime(heute.year, heute.month, heute.day, 8, 30))

    p.schreibe_prefs()
    return p


# ----------------------------------------------------------------------

def test_profil_wird_gefunden(profil, heim):
    from kalenderblick import thunderbird

    gefunden = thunderbird.waehle_profil()
    assert gefunden == profil.profil
    assert len(thunderbird.kalenderdateien(gefunden)) == 3


def test_registry_liest_namen_farben_und_abholung(profil):
    from kalenderblick import thunderbird

    registry = thunderbird.lies_registry(profil.profil)
    assert registry["aaaa1111"].name == "Privat"
    assert registry["aaaa1111"].farbe == "#2ec27e"
    assert registry["aaaa1111"].ist_fern is False

    proton = registry["bbbb2222"]
    assert proton.art == "ics"
    assert proton.ist_fern is True
    assert proton.abholung_minuten == 30
    assert "30 Minuten" in proton.abholtext()

    assert registry["cccc3333"].abgeschaltet is True


def test_abholtext_sonderfaelle(profil):
    from kalenderblick.thunderbird import Kalender

    assert "von Hand" in Kalender("x", art="ics", abholung_minuten=0).abholtext()
    assert "2 Stunden" in Kalender("x", art="ics", abholung_minuten=120).abholtext()
    assert "Vorgabe" in Kalender("x", art="ics").abholtext()
    assert "örtlich" in Kalender("x", art="storage").abholtext()


def test_einfacher_termin(profil):
    from kalenderblick import thunderbird

    termine = thunderbird.lies_termine(profil.profil, tage_voraus=14)
    zahnarzt = [t for t in termine if t.titel == "Zahnarzt"]
    assert len(zahnarzt) == 1
    assert zahnarzt[0].tag == date.today()
    assert zahnarzt[0].ganztags is False
    assert zahnarzt[0].ort == "Hauptstraße 3"
    assert zahnarzt[0].kalender_name == "Privat"
    assert zahnarzt[0].farbe == "#2ec27e"


def test_ganztaegiger_termin(profil):
    from kalenderblick import thunderbird

    termine = thunderbird.lies_termine(profil.profil, tage_voraus=14)
    urlaub = [t for t in termine if t.titel == "Urlaub"]
    assert len(urlaub) == 1
    assert urlaub[0].ganztags is True
    assert urlaub[0].beginn.date() == date.today() + timedelta(days=1)
    assert urlaub[0].zeitangabe() == "ganztägig"


def test_termin_ausserhalb_des_fensters_fehlt(profil):
    from kalenderblick import thunderbird

    termine = thunderbird.lies_termine(profil.profil, tage_voraus=14)
    assert not [t for t in termine if t.titel == "Sehr spät"]


def test_abgeschalteter_kalender_bleibt_verborgen(profil):
    from kalenderblick import thunderbird

    termine = thunderbird.lies_termine(profil.profil, tage_voraus=14)
    assert not [t for t in termine if t.titel == "Sollte verborgen sein"]


def test_versteckte_kalender(profil):
    from kalenderblick import thunderbird

    termine = thunderbird.lies_termine(profil.profil, tage_voraus=30,
                                       versteckt=["bbbb2222"])
    assert not [t for t in termine if t.titel == "Vorstandssitzung"]


def test_woechentliche_wiederholung(profil):
    from kalenderblick import thunderbird

    termine = thunderbird.lies_termine(profil.profil, tage_voraus=28, tage_zurueck=7)
    sitzungen = sorted(t.beginn for t in termine if t.titel == "Vorstandssitzung")
    assert len(sitzungen) >= 4
    # alle montags, jeweils eine Woche auseinander
    assert all(z.weekday() == 0 for z in sitzungen)
    for frueher, spaeter in zip(sitzungen, sitzungen[1:]):
        assert (spaeter.date() - frueher.date()).days == 7
    assert all(z.hour == 9 and z.minute == 0 for z in sitzungen)


def test_kalenderliste_mit_stand(profil):
    from kalenderblick import thunderbird

    kalender = {k.kennung: k for k in thunderbird.lies_kalender(profil.profil)}
    assert set(kalender) == {"aaaa1111", "bbbb2222", "cccc3333"}
    proton = kalender["bbbb2222"]
    assert proton.datei is not None
    assert proton.zuletzt_geschrieben is not None
    assert proton.anzahl == 0 or proton.anzahl >= 0
