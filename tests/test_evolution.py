from datetime import date, datetime, timedelta

import pytest

from hilfe_evolution import EvolutionAblage

pytest.importorskip("icalendar")


@pytest.fixture
def ablage(heim):
    a = EvolutionAblage(heim)
    heute = date.today()

    a.lege_kalender_an("priv0001", "Privat", farbe="#2ec27e", art="local")
    a.termin("priv0001", "e1", "Zahnarzt",
             datetime(heute.year, heute.month, heute.day, 10, 0),
             datetime(heute.year, heute.month, heute.day, 11, 0),
             ort="Bahnhofstraße 12")

    morgen = heute + timedelta(days=1)
    a.termin("priv0001", "e2", "Urlaub",
             datetime(morgen.year, morgen.month, morgen.day),
             datetime(morgen.year, morgen.month, morgen.day) + timedelta(days=2),
             ganztags=True)

    fern = heute + timedelta(days=400)
    a.termin("priv0001", "e3", "Sehr spät",
             datetime(fern.year, fern.month, fern.day, 9, 0),
             datetime(fern.year, fern.month, fern.day, 10, 0))

    # Abonniert, mit wöchentlicher Wiederholung
    a.lege_kalender_an("arb0002", "Arbeit", farbe="#3584e4", art="caldav")
    montag = heute - timedelta(days=heute.weekday())
    a.termin("arb0002", "r1", "Teambesprechung",
             datetime(montag.year, montag.month, montag.day, 9, 0),
             datetime(montag.year, montag.month, montag.day, 10, 0),
             rrule="FREQ=WEEKLY;BYDAY=MO;COUNT=8")

    # Abgeschaltet - darf nicht auftauchen
    a.lege_kalender_an("alt0003", "Alt", abgeschaltet=True)
    a.termin("alt0003", "e9", "Sollte verborgen sein",
             datetime(heute.year, heute.month, heute.day, 8, 0),
             datetime(heute.year, heute.month, heute.day, 8, 30))
    return a


# ----------------------------------------------------------------------

def test_erkennt_dass_evolution_da_ist(ablage):
    from kalenderblick import evolution
    assert evolution.vorhanden()
    assert len(evolution.kalenderdateien()) == 3


def test_ohne_evolution_keine_funde(heim):
    from kalenderblick import evolution
    assert not evolution.vorhanden()
    assert evolution.lies_termine() == []


def test_namen_farben_und_art(ablage):
    from kalenderblick import evolution

    nach_namen = {k.name: k for k in evolution.lies_kalender()}
    assert nach_namen["Privat"].farbe == "#2ec27e"
    assert nach_namen["Privat"].ist_fern is False
    assert nach_namen["Arbeit"].art == "caldav"
    assert nach_namen["Arbeit"].ist_fern is True
    assert nach_namen["Alt"].abgeschaltet is True


def test_einfacher_termin(ablage):
    from kalenderblick import evolution

    termine = evolution.lies_termine(tage_voraus=14)
    zahnarzt = [t for t in termine if t.titel == "Zahnarzt"]
    assert len(zahnarzt) == 1
    assert zahnarzt[0].tag == date.today()
    assert zahnarzt[0].ganztags is False
    assert zahnarzt[0].ort == "Bahnhofstraße 12"
    assert zahnarzt[0].kalender_name == "Privat"
    assert zahnarzt[0].farbe == "#2ec27e"


def test_ganztaegiger_termin(ablage):
    from kalenderblick import evolution

    urlaub = [t for t in evolution.lies_termine(tage_voraus=14)
              if t.titel == "Urlaub"]
    assert len(urlaub) == 1
    assert urlaub[0].ganztags is True
    assert urlaub[0].beginn.date() == date.today() + timedelta(days=1)
    assert urlaub[0].zeitangabe() == "ganztägig"


def test_wiederholung_wird_entfaltet(ablage):
    from kalenderblick import evolution

    sitzungen = [t for t in evolution.lies_termine(tage_voraus=21)
                 if t.titel == "Teambesprechung"]
    assert len(sitzungen) >= 2, "die wöchentliche Wiederholung fehlt"
    assert all(t.beginn.weekday() == 0 for t in sitzungen), "nicht alle montags"


def test_termin_ausserhalb_des_fensters_fehlt(ablage):
    from kalenderblick import evolution

    assert not [t for t in evolution.lies_termine(tage_voraus=14)
                if t.titel == "Sehr spät"]


def test_abgeschalteter_kalender_bleibt_verborgen(ablage):
    from kalenderblick import evolution

    assert not [t for t in evolution.lies_termine(tage_voraus=14)
                if t.titel == "Sollte verborgen sein"]


def test_versteckte_kalender_werden_uebergangen(ablage):
    from kalenderblick import evolution

    termine = evolution.lies_termine(tage_voraus=14, versteckt=["priv0001"])
    assert not [t for t in termine if t.kalender_name == "Privat"]
    assert [t for t in termine if t.kalender_name == "Arbeit"]


def test_termine_sind_nach_zeit_sortiert(ablage):
    from kalenderblick import evolution

    termine = evolution.lies_termine(tage_voraus=21)
    assert termine == sorted(termine, key=lambda t: t.beginn)


def test_kaputter_eintrag_kippt_nicht_die_ganze_liste(ablage):
    """Ein unbrauchbarer Eintrag darf die übrigen nicht mitreißen."""
    from kalenderblick import evolution

    datei = ablage.kalender / "priv0001" / "calendar.ics"
    inhalt = datei.read_text(encoding="utf-8")
    datei.write_text(inhalt.replace(
        "END:VCALENDAR",
        "BEGIN:VEVENT\nUID:kaputt\nSUMMARY:Ohne Anfang\nEND:VEVENT\n"
        "END:VCALENDAR"), encoding="utf-8")

    termine = evolution.lies_termine(tage_voraus=14)
    assert [t for t in termine if t.titel == "Zahnarzt"], \
        "der gültige Termin fehlt, ein kaputter Eintrag hat alles gekippt"


# ----------------------------------------------------------------------
#  Entfernte Kalender liegen woanders
# ----------------------------------------------------------------------
#
#  Am 04.11.2026 an Evolution 3.60.2 geprüft: CalDAV-, Google- und
#  abonnierte Kalender landen nicht als calendar.ics unter den Daten,
#  sondern als SQLite unter ~/.cache/evolution/calendar/<uid>/cache.db.
#  Solange nur der erste Ort gelesen wurde, blieben sie unsichtbar -
#  während README und Anleitung genau das Gegenteil versprachen.

def test_entfernter_kalender_wird_gefunden(heim):
    from kalenderblick import evolution
    heute = date.today()

    a = EvolutionAblage(heim)
    a.lege_fernkalender_an("fern01", "Arbeit (CalDAV)", art="caldav")
    a.fern_termin("fern01", "f1", "Aus dem Zwischenspeicher",
                  datetime(heute.year, heute.month, heute.day, 11, 0),
                  datetime(heute.year, heute.month, heute.day, 12, 0),
                  ort="Büro")

    namen = {k.name for k in evolution.lies_kalender()}
    assert "Arbeit (CalDAV)" in namen

    titel = {t.titel for t in evolution.lies_termine(tage_voraus=7)}
    assert "Aus dem Zwischenspeicher" in titel


def test_ort_kommt_aus_dem_zwischenspeicher_mit(heim):
    from kalenderblick import evolution
    heute = date.today()

    a = EvolutionAblage(heim)
    a.lege_fernkalender_an("fern01", "Arbeit")
    a.fern_termin("fern01", "f1", "Besprechung",
                  datetime(heute.year, heute.month, heute.day, 11, 0),
                  datetime(heute.year, heute.month, heute.day, 12, 0),
                  ort="Raum 3")

    termine = [t for t in evolution.lies_termine(tage_voraus=7)
               if t.titel == "Besprechung"]
    assert termine and termine[0].ort == "Raum 3"


def test_beide_ablageorte_nebeneinander(heim):
    """Ein örtlicher und ein entfernter Kalender gleichzeitig - der
    häufige Fall, wenn jemand Google in Evolution eingebunden hat."""
    from kalenderblick import evolution
    heute = date.today()

    a = EvolutionAblage(heim)
    a.lege_kalender_an("ort01", "Privat")
    a.termin("ort01", "o1", "Örtlich",
             datetime(heute.year, heute.month, heute.day, 9, 0),
             datetime(heute.year, heute.month, heute.day, 10, 0))
    a.lege_fernkalender_an("fern01", "Google")
    a.fern_termin("fern01", "f1", "Entfernt",
                  datetime(heute.year, heute.month, heute.day, 14, 0),
                  datetime(heute.year, heute.month, heute.day, 15, 0))

    titel = [t.titel for t in evolution.lies_termine(tage_voraus=7)]
    assert "Örtlich" in titel and "Entfernt" in titel
    assert titel.index("Örtlich") < titel.index("Entfernt"), "nicht sortiert"


def test_vorhanden_erkennt_auch_reine_fernkalender(heim):
    """Wer in Evolution ausschließlich Google eingebunden hat, besitzt
    überhaupt keine .ics-Datei - trotzdem ist Evolution vorhanden."""
    from kalenderblick import evolution

    a = EvolutionAblage(heim)
    a.lege_fernkalender_an("fern01", "Nur Google")
    assert evolution.vorhanden()


def test_abgeschalteter_fernkalender_bleibt_draussen(heim):
    """Zwei Fernkalender, einer abgeschaltet: Nur so prüft der Test
    wirklich die Abschaltung. Mit nur einem Kalender wäre er auch dann
    grün, wenn Fernkalender überhaupt nicht gelesen würden."""
    from kalenderblick import evolution
    heute = date.today()

    a = EvolutionAblage(heim)
    a.lege_fernkalender_an("fern01", "Aus", abgeschaltet=True)
    a.fern_termin("fern01", "f1", "Unsichtbar",
                  datetime(heute.year, heute.month, heute.day, 11, 0),
                  datetime(heute.year, heute.month, heute.day, 12, 0))
    a.lege_fernkalender_an("fern02", "An")
    a.fern_termin("fern02", "f2", "Sichtbar",
                  datetime(heute.year, heute.month, heute.day, 13, 0),
                  datetime(heute.year, heute.month, heute.day, 14, 0))

    titel = {t.titel for t in evolution.lies_termine(tage_voraus=7)}
    assert "Sichtbar" in titel, "Fernkalender werden gar nicht gelesen"
    assert "Unsichtbar" not in titel
