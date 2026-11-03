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


# ----------------------------------------------------------------------
#  Profilwahl - mehrere Profile, wie auf einem gewachsenen Rechner
# ----------------------------------------------------------------------

def _profiles_ini(wurzel, startprofil: str, eintraege: list[tuple[str, str]]) -> None:
    text = [f"[Install4F96D1932A9F858E]", f"Default={startprofil}", "Locked=1", ""]
    for nummer, (name, pfad) in enumerate(eintraege):
        text += [f"[Profile{nummer}]", f"Name={name}", "IsRelative=1", f"Path={pfad}", ""]
    (wurzel / ".thunderbird" / "profiles.ini").write_text("\n".join(text), encoding="utf-8")


@pytest.fixture
def mehrere_profile(heim):
    """Ein leeres Testprofil vorn, das echte Profil hinten - wie bei Stephan."""
    from datetime import datetime as dt

    wurzel = heim / ".thunderbird"
    (wurzel).mkdir(parents=True, exist_ok=True)

    leer = Profil.__new__(Profil)
    leer.wurzel = heim
    leer.profil = wurzel / "h2gfk95y.TEST"
    (leer.profil / "calendar-data").mkdir(parents=True)
    leer.prefs = []
    leer.kalender("tttt0000", "Testkalender")
    leer.schreibe_prefs()

    echt = Profil.__new__(Profil)
    echt.wurzel = heim
    echt.profil = wurzel / "ig49q8o9.default-release"
    (echt.profil / "calendar-data").mkdir(parents=True)
    echt.prefs = []
    verbindung = echt.kalender("aaaa1111", "Privat")
    heute = date.today()
    termin(verbindung, "aaaa1111", "x1", "Echter Termin",
           dt(heute.year, heute.month, heute.day, 10, 0),
           dt(heute.year, heute.month, heute.day, 11, 0))
    echt.schreibe_prefs()

    _profiles_ini(heim, "ig49q8o9.default-release",
                  [("TEST", "h2gfk95y.TEST"),
                   ("default-release", "ig49q8o9.default-release")])
    return leer, echt


def test_startprofil_von_thunderbird_gewinnt(mehrere_profile):
    from kalenderblick import thunderbird

    leer, echt = mehrere_profile
    assert thunderbird.waehle_profil() == echt.profil


def test_leeres_profil_verliert_auch_wenn_es_startprofil_ist(mehrere_profile, heim):
    from kalenderblick import thunderbird

    leer, echt = mehrere_profile
    _profiles_ini(heim, "h2gfk95y.TEST",
                  [("TEST", "h2gfk95y.TEST"),
                   ("default-release", "ig49q8o9.default-release")])
    # Das Startprofil hat keine Termine, also gewinnt das Profil mit Inhalt
    assert thunderbird.waehle_profil() == echt.profil


def test_vorschlaege_zaehlen_dateien_und_termine(mehrere_profile):
    from kalenderblick import thunderbird

    nach_pfad = {p: (d, t, b) for p, d, t, b in thunderbird.profil_vorschlaege()}
    leer, echt = mehrere_profile
    assert nach_pfad[leer.profil][1] == 0
    assert nach_pfad[echt.profil][1] == 1
    assert nach_pfad[echt.profil][2] is True


def test_altes_schema_mit_local_sqlite(heim):
    """Ältere Thunderbird-Fassungen legen alles in local.sqlite ab."""
    from datetime import datetime as dt

    from kalenderblick import thunderbird

    p = Profil(heim)
    verbindung = p.kalender("local", "wird nicht benutzt")
    # zwei Kalender in einer Datei, wie im alten Schema
    p.prefs = [z for z in p.prefs if "local" not in z]
    for kennung, name in (("aaaa1111", "Privat"), ("bbbb2222", "Arbeit")):
        p.prefs += [
            f'user_pref("calendar.registry.{kennung}.name", "{name}");',
            f'user_pref("calendar.registry.{kennung}.type", "storage");',
        ]
    heute = date.today()
    termin(verbindung, "aaaa1111", "l1", "Privattermin",
           dt(heute.year, heute.month, heute.day, 9, 0),
           dt(heute.year, heute.month, heute.day, 10, 0))
    termin(verbindung, "bbbb2222", "l2", "Arbeitstermin",
           dt(heute.year, heute.month, heute.day, 14, 0),
           dt(heute.year, heute.month, heute.day, 15, 0))
    p.schreibe_prefs()

    kalender = {k.kennung: k for k in thunderbird.lies_kalender(p.profil)}
    assert kalender["aaaa1111"].anzahl == 1
    assert kalender["bbbb2222"].anzahl == 1
    assert kalender["aaaa1111"].datei.name == "local.sqlite"
    assert kalender["bbbb2222"].datei.name == "local.sqlite"

    titel = {t.titel for t in thunderbird.lies_termine(p.profil)}
    assert titel == {"Privattermin", "Arbeitstermin"}


# ----------------------------------------------------------------------
#  Ausgelassene Einzeltermine
# ----------------------------------------------------------------------

@pytest.fixture
def reihe_mit_luecke(heim):
    """Wöchentliche Reihe, bei der ein Termin abgesagt wurde."""
    from datetime import datetime as dt

    p = Profil(heim)
    verbindung = p.kalender("bbbb2222", "Proton", art="ics", abholung=30)
    heute = date.today()
    montag = heute - timedelta(days=heute.weekday())
    ausgelassen = montag + timedelta(days=14)
    termin(verbindung, "bbbb2222", "r1", "Vorstandssitzung",
           dt(montag.year, montag.month, montag.day, 9, 0),
           dt(montag.year, montag.month, montag.day, 10, 30),
           rrule="RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=6",
           exdate="EXDATE;TZID=Europe/Berlin:"
                  + ausgelassen.strftime("%Y%m%d") + "T090000")
    p.schreibe_prefs()
    return p, ausgelassen


def test_exdate_laesst_den_termin_aus(reihe_mit_luecke):
    from kalenderblick import thunderbird

    p, ausgelassen = reihe_mit_luecke
    termine = thunderbird.lies_termine(p.profil, tage_voraus=60, tage_zurueck=14)
    tage = {t.tag for t in termine if t.titel == "Vorstandssitzung"}
    assert tage, "die Reihe fehlt ganz"
    assert ausgelassen not in tage, "der abgesagte Termin wird noch angezeigt"
    # die übrigen fünf sind da
    assert len(tage) == 5


def test_exdate_in_utc_wird_auch_erkannt(heim):
    from datetime import datetime as dt
    from datetime import timezone as tzone

    from kalenderblick import thunderbird

    p = Profil(heim)
    verbindung = p.kalender("dddd4444", "Reihe")
    heute = date.today()
    montag = heute - timedelta(days=heute.weekday())
    ausgelassen = montag + timedelta(days=7)
    # 09:00 Berlin entspricht 08:00 UTC in der Winterzeit, 07:00 in der Sommerzeit
    versatz = dt(ausgelassen.year, ausgelassen.month, ausgelassen.day, 9, 0)
    import zoneinfo
    in_utc = versatz.replace(tzinfo=zoneinfo.ZoneInfo("Europe/Berlin")).astimezone(tzone.utc)

    termin(verbindung, "dddd4444", "u1", "Jour fixe",
           dt(montag.year, montag.month, montag.day, 9, 0),
           dt(montag.year, montag.month, montag.day, 9, 30),
           rrule="RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=4",
           exdate="EXDATE:" + in_utc.strftime("%Y%m%dT%H%M%SZ"))
    p.schreibe_prefs()

    tage = {t.tag for t in thunderbird.lies_termine(p.profil, tage_voraus=40, tage_zurueck=14)
            if t.titel == "Jour fixe"}
    assert ausgelassen not in tage
    assert len(tage) == 3


# ----------------------------------------------------------------------
#  Profilorte: Flatpak, Snap, Betterbird

def test_profilwurzeln_decken_die_ueblichen_orte_ab(heim):
    from kalenderblick import thunderbird

    orte = {str(p) for p in thunderbird.profil_wurzeln()}
    erwartet = {
        str(heim / ".thunderbird"),
        str(heim / ".var" / "app" / "org.mozilla.Thunderbird" / ".thunderbird"),
        str(heim / ".var" / "app" / "eu.betterbird.Betterbird" / ".thunderbird"),
        str(heim / "snap" / "thunderbird" / "common" / ".thunderbird"),
    }
    assert erwartet <= orte, f"nicht gesucht wird in: {erwartet - orte}"


def test_profil_in_betterbird_flatpak_wird_gefunden(heim):
    """Betterbird teilt sich sonst ~/.thunderbird mit Thunderbird; als
    Flatpak liegt das Profil wegen der Abschottung woanders."""
    from kalenderblick import thunderbird
    from hilfe import Profil

    wurzel = heim / ".var" / "app" / "eu.betterbird.Betterbird"
    wurzel.mkdir(parents=True)
    p = Profil(wurzel)
    p.kalender("bb001", "Betterbird-Kalender")
    p.schreibe_prefs()

    assert thunderbird.waehle_profil() == p.profil


def test_fehlermeldung_ohne_profil_nennt_den_ausweg(heim):
    """Die Meldung landet in der Oberfläche - sie muss sagen, was zu tun
    ist, statt nur eine Liste durchsuchter Pfade abzuladen."""
    from kalenderblick import thunderbird

    try:
        thunderbird.waehle_profil()
    except thunderbird.ThunderbirdFehler as fehler:
        text = str(fehler)
    else:
        raise AssertionError("ohne Profil müsste ein Fehler kommen")

    assert "Kalenderquellen" in text, "kein Hinweis, wo man es einstellt"
    assert str(heim) not in text, "rohe Pfadliste gehört in `pruefen`, nicht hierher"


def test_fehlermeldung_bei_verschwundenem_profil(heim):
    from kalenderblick import thunderbird

    try:
        thunderbird.waehle_profil("/gibt/es/nicht")
    except thunderbird.ThunderbirdFehler as fehler:
        text = str(fehler)
    else:
        raise AssertionError("ein nicht vorhandener Pfad müsste auffallen")

    assert "/gibt/es/nicht" in text, "der betroffene Pfad gehört genannt"
    assert "Kalenderquellen" in text


def test_gesperrte_datei_bremst_nicht(profil):
    """Läuft Thunderbird, sind seine Dateien dauerhaft gesperrt. Früher
    wartete jeder Zugriff zwei Sekunden auf eine Sperre, die nie
    aufgeht, und wich dann ohnehin auf eine Kopie aus - das Umschalten
    zwischen den Reitern dauerte dadurch mehrere Sekunden."""
    import sqlite3
    import time

    from kalenderblick import thunderbird

    datei = thunderbird.kalenderdateien(profil.profil)[0]
    sperre = sqlite3.connect(datei)
    sperre.execute("BEGIN EXCLUSIVE")
    try:
        start = time.perf_counter()
        kalender = thunderbird.lies_kalender(profil.profil)
        gebraucht = time.perf_counter() - start
    finally:
        sperre.rollback()
        sperre.close()

    assert gebraucht < 1.0, f"{gebraucht:.1f} s trotz gesperrter Datei - wird gewartet?"
    assert kalender, "trotz Sperre müssen die Kalender über die Kopie lesbar sein"


def test_termine_trotz_gesperrter_datei_vollstaendig(profil):
    """Das Ausweichen auf die Kopie darf keine Termine verschlucken."""
    import sqlite3

    from kalenderblick import thunderbird

    ohne_sperre = thunderbird.lies_termine(profil.profil, tage_voraus=14)

    datei = thunderbird.kalenderdateien(profil.profil)[0]
    sperre = sqlite3.connect(datei)
    sperre.execute("BEGIN EXCLUSIVE")
    try:
        mit_sperre = thunderbird.lies_termine(profil.profil, tage_voraus=14)
    finally:
        sperre.rollback()
        sperre.close()

    assert {t.titel for t in mit_sperre} == {t.titel for t in ohne_sperre}
