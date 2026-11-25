"""Eine eigene Farbe je Kalender, statt der aus dem Kalenderprogramm.

Gewünscht am 25.11.2026. Bis dahin übernahm KALENDERBlick die Farbe
stillschweigend aus Thunderbird oder Evolution. Das bleibt die Vorgabe -
dort hat der Nutzer sie schon einmal vergeben, und auf eine zweite
Einrichtung hat niemand Lust. Aber auf dunklem Schreibtischgrund wirkt
dieselbe Farbe oft anders als in einem hellen Kalenderfenster.

**Die Zuordnung läuft über `Termin.kalender_id`.** Das ist dieselbe
Kennung, nach der auch ausgeblendet wird, und sie trägt in allen drei
Quellen denselben Wert wie `Kalender.kennung` - bei Thunderbird die
`cal_id`, bei Evolution und den Abonnements das, was `ical.termine_aus`
durchgereicht bekommt. Deshalb darf das Einfärben an einer einzigen
Stelle stehen; die Tests unten prüfen genau diese Annahme für jede
Quelle einzeln.
"""

from datetime import date, datetime

import pytest

from hilfe import Profil, termin

from kalenderblick import config, quellen, thunderbird
from kalenderblick.modell import Termin


@pytest.fixture
def zwei_kalender(heim):
    p = Profil(heim)
    heute = date.today()
    for kennung, name, farbe in (("k1", "Privat", "#3584e4"),
                                 ("k2", "Arbeit", "#e66100")):
        v = p.kalender(kennung, name, farbe=farbe)
        termin(v, kennung, f"e-{kennung}", f"Termin {name}",
               datetime(heute.year, heute.month, heute.day, 9, 0),
               datetime(heute.year, heute.month, heute.day, 10, 0))
    p.schreibe_prefs()
    return p


# ----------------------------------------------------------------------
# Die Zuordnung selbst
# ----------------------------------------------------------------------

def _termin(kalender_id: str, farbe: str) -> Termin:
    jetzt = datetime(2026, 11, 25, 9, 0)
    return Termin(titel="Test", beginn=jetzt, ende=jetzt,
                  kalender_id=kalender_id, farbe=farbe)


def test_eigene_farbe_sticht_die_der_quelle():
    termine = [_termin("k1", "#3584e4")]
    quellen.faerbe(termine, {"k1": "#ff0000"})
    assert termine[0].farbe == "#ff0000"


def test_ohne_eintrag_bleibt_die_farbe_der_quelle():
    """Die Vorgabe ist der Normalfall - sie darf nicht verlorengehen."""
    termine = [_termin("k1", "#3584e4")]
    quellen.faerbe(termine, {"k2": "#ff0000"})
    assert termine[0].farbe == "#3584e4"


def test_ohne_jede_angabe_passiert_nichts():
    termine = [_termin("k1", "#3584e4")]
    for leer in (None, {}):
        quellen.faerbe(termine, leer)
        assert termine[0].farbe == "#3584e4"


def test_nur_der_gemeinte_kalender_wird_umgefaerbt():
    termine = [_termin("k1", "#3584e4"), _termin("k2", "#e66100")]
    quellen.faerbe(termine, {"k2": "#ff0000"})
    assert [t.farbe for t in termine] == ["#3584e4", "#ff0000"]


# ----------------------------------------------------------------------
# Der ganze Weg, von der Konfiguration bis zum Termin
# ----------------------------------------------------------------------

def test_thunderbird_termine_bekommen_die_eigene_farbe(zwei_kalender):
    termine = quellen.lies_termine(
        quelle="thunderbird", profil_vorgabe=str(zwei_kalender.profil),
        tage_voraus=7, farben={"k2": "#9141ac"})
    nach_name = {t.kalender_name: t.farbe for t in termine}
    assert nach_name["Arbeit"] == "#9141ac"
    assert nach_name["Privat"] == "#3584e4", "die Vorgabe wurde mitgeändert"


def test_kalender_id_passt_zur_kennung(zwei_kalender):
    """Die Annahme, auf der alles beruht - sonst färbt nichts.

    Ginge sie verloren, bliebe die Farbe einfach die alte: ein Fehler,
    den man nur sieht, wenn man ihn sucht.
    """
    kalender = thunderbird.lies_kalender(zwei_kalender.profil)
    kennungen = {k.kennung for k in kalender}
    termine = thunderbird.lies_termine(zwei_kalender.profil, tage_voraus=7)
    assert {t.kalender_id for t in termine} <= kennungen


def test_die_eigene_farbe_ueberlebt_das_speichern(heim):
    e = config.laden()
    e.kalender_farben = {"k1": "#9141ac"}
    e.speichern()
    assert config.laden().kalender_farben == {"k1": "#9141ac"}


# ----------------------------------------------------------------------
# Was in der Datei stehen darf
# ----------------------------------------------------------------------

@pytest.mark.parametrize("farbe", ["#3584e4", "#abc", "#ABCDEF"])
def test_gueltige_farben_werden_angenommen(farbe):
    e = config.Einstellungen()
    e.kalender_farben = {"k1": farbe}
    e.pruefe()


@pytest.mark.parametrize("farbe", ["rot", "3584e4", "#12345", "", "#gggggg"])
def test_unbrauchbare_farben_werden_abgewiesen(farbe):
    """Von Hand bearbeitete Dateien - die Oberfläche liefert nur gültige.

    Ohne die Prüfung käme der Wert erst im Stylesheet an und fiele dort
    lautlos aus: Der Punkt wäre schwarz, ohne erkennbaren Grund.
    """
    e = config.Einstellungen()
    e.kalender_farben = {"k1": farbe}
    with pytest.raises(config.KonfigFehler) as f:
        e.pruefe()
    assert "k1" in str(f.value)


# ----------------------------------------------------------------------
# Die Oberfläche: der Punkt neben dem Haken
# ----------------------------------------------------------------------

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def uebersicht(qt_app, zwei_kalender, heim):
    """Die Kalenderliste aus dem Reiter „Einstellungen“, geladen."""
    from kalenderblick.gui.fenster import _KalenderUebersicht

    e = config.laden()
    e.profil = str(zwei_kalender.profil)
    e.quelle = "thunderbird"
    e.speichern()

    w = _KalenderUebersicht()
    w.lade()
    yield w
    w.deleteLater()


def _aufraeumen():
    """Zustellen, was `deleteLater()` angemeldet hat.

    `lade()` baut die Zeilen neu auf und meldet die alten mit
    `deleteLater()` ab - fällig wird das aber erst in der
    Ereignisschleife, und die läuft im Test nicht. Ohne diesen Schritt
    findet `findChildren` die abgeräumten Knöpfe noch und der Test
    misst Gespenster.
    """
    from PyQt6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QCoreApplication.processEvents()


def _knoepfe(w, zeichen):
    from PyQt6.QtWidgets import QPushButton
    _aufraeumen()
    return [b for b in w.findChildren(QPushButton) if b.text() == zeichen]


def _punkte(w):
    """Die Farbknöpfe, in der Reihenfolge der Zeilen."""
    return _knoepfe(w, "●")


def test_der_farbpunkt_ist_ein_knopf(uebersicht):
    """Vorher war er ein QLabel - unanklickbar und ohne Hinweis darauf."""
    punkte = _punkte(uebersicht)
    assert len(punkte) == 2
    assert all(b.isEnabled() for b in punkte)
    assert all("Farbe" in b.toolTip() for b in punkte)


def test_klick_auf_den_punkt_speichert_die_gewaehlte_farbe(uebersicht, monkeypatch):
    from PyQt6.QtGui import QColor
    from kalenderblick.gui import fenster as fenster_modul

    monkeypatch.setattr(fenster_modul.QColorDialog, "getColor",
                        staticmethod(lambda *a, **k: QColor("#9141ac")))
    _punkte(uebersicht)[0].click()

    assert "#9141ac" in config.laden().kalender_farben.values()


def test_abbrechen_aendert_nichts(uebersicht, monkeypatch):
    """Ein ungültiger QColor ist das, was „Abbrechen“ zurückgibt."""
    from PyQt6.QtGui import QColor
    from kalenderblick.gui import fenster as fenster_modul

    monkeypatch.setattr(fenster_modul.QColorDialog, "getColor",
                        staticmethod(lambda *a, **k: QColor()))
    _punkte(uebersicht)[0].click()

    assert config.laden().kalender_farben == {}


def test_die_vorgabefarbe_waehlen_merkt_nichts(uebersicht, monkeypatch):
    """Sonst stünde ein Eintrag da, der nichts tut - und eine spätere
    Änderung in Thunderbird käme stillschweigend nicht mehr an."""
    from PyQt6.QtGui import QColor
    from kalenderblick.gui import fenster as fenster_modul

    punkt = _punkte(uebersicht)[0]
    vorgabe = punkt.toolTip().split("(")[-1].rstrip(").")
    monkeypatch.setattr(fenster_modul.QColorDialog, "getColor",
                        staticmethod(lambda *a, **k: QColor(vorgabe)))
    punkt.click()

    assert config.laden().kalender_farben == {}


def test_zuruecksetzen_erscheint_erst_mit_eigener_farbe(uebersicht, monkeypatch):
    from PyQt6.QtGui import QColor
    from kalenderblick.gui import fenster as fenster_modul

    def rueckwege(w):
        return _knoepfe(w, "↺")

    assert rueckwege(uebersicht) == [], "Rückweg ohne eigene Farbe angeboten"

    monkeypatch.setattr(fenster_modul.QColorDialog, "getColor",
                        staticmethod(lambda *a, **k: QColor("#9141ac")))
    _punkte(uebersicht)[0].click()
    assert len(rueckwege(uebersicht)) == 1

    rueckwege(uebersicht)[0].click()
    assert config.laden().kalender_farben == {}
    assert rueckwege(uebersicht) == []
