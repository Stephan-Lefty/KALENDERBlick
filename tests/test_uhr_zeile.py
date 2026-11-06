"""Der nächste Termin als Zeile unter der Uhr.

Sie ist knapper als der Mauszeiger-Hinweis, und das mit Absicht: Der
Hinweis schwebt über allem und darf ausführlich sein, diese Zeile
steht **in** der Uhr und muss sich dem Platz fügen.

Der zweite Teil der Datei prüft das Widget selbst. Das ist hier kein
Beiwerk - in diesem Projekt war der häufigste Fehler nicht eine
falsche Rechnung, sondern etwas, das fertig gebaut dalag und von
niemandem abgeholt wurde.
"""

import os
from datetime import datetime

import pytest

from kalenderblick.modell import Termin, naechster, uhr_zeile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HEUTE = datetime(2026, 11, 6, 9, 30)   # ein Freitag


def _termin(titel="Zahnarzt", beginn=datetime(2026, 11, 6, 14, 0),
            ende=None, ganztags=False) -> Termin:
    return Termin(kennung=titel, titel=titel, beginn=beginn,
                  ende=ende or beginn.replace(hour=beginn.hour + 1),
                  ganztags=ganztags)


@pytest.fixture(scope="module")
def qt_app():
    # Der Skip gehört in die Fixture, nicht an den Dateianfang: Oben
    # stünde er auch über den Texttests, die ohne Qt auskommen. Und er
    # muss ein Skip sein - ein Import, der in der Fixture platzt, ist
    # für pytest ein Fehler und färbt die CI rot.
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


# ----------------------------------------------------------------- Text


def test_ohne_termin_steht_dort_keine_leere_zeile():
    """Ein leerer Platz sähe aus wie ein Fehler in der Anzeige."""
    assert uhr_zeile(None, HEUTE) == "Keine Termine"


def test_heute_nur_die_uhrzeit():
    """Welcher Tag heute ist, steht zwei Zeilen darüber."""
    assert uhr_zeile(_termin(), HEUTE) == "14:00 Zahnarzt"


def test_morgen_mit_tag_und_datum():
    zeile = uhr_zeile(_termin(beginn=datetime(2026, 11, 7, 8, 0)), HEUTE)
    assert zeile == "Morgen, 7.11. 08:00 Zahnarzt"


def test_ferner_termin_mit_kurzem_wochentag():
    """Kurzform, weil die Uhr im kleinsten Widget 220 px breit ist."""
    zeile = uhr_zeile(_termin(beginn=datetime(2026, 11, 12, 16, 30)), HEUTE)
    assert zeile == "Do, 12.11. 16:30 Zahnarzt"


def test_laufender_termin_ohne_uhrzeit():
    """Wann er begann, interessiert nicht mehr - er läuft ja."""
    laeuft = _termin(beginn=datetime(2026, 11, 6, 9, 0),
                     ende=datetime(2026, 11, 6, 10, 0))
    assert uhr_zeile(laeuft, HEUTE) == "Jetzt: Zahnarzt"


def test_ganztaegiger_termin_heute_ohne_uhrzeit():
    """Eine Uhrzeit wäre hier eine Erfindung."""
    feier = _termin(titel="Geburtstag Oma", beginn=datetime(2026, 11, 6, 0, 0),
                    ende=datetime(2026, 11, 6, 23, 59), ganztags=True)
    assert uhr_zeile(feier, HEUTE) == "Heute: Geburtstag Oma"


def test_ganztaegiger_termin_spaeter_mit_datum():
    feier = _termin(titel="Feiertag", beginn=datetime(2026, 12, 25, 0, 0),
                    ende=datetime(2026, 12, 25, 23, 59), ganztags=True)
    assert uhr_zeile(feier, HEUTE) == "Fr, 25.12.: Feiertag"


def test_langer_titel_wird_gekuerzt():
    """Sonst schiebt die wachsende Zeile die Uhrzeit aus der Mitte."""
    lang = _termin(titel="Elterngespräch in der Grundschule am Stadtpark")
    zeile = uhr_zeile(lang, HEUTE)

    assert zeile.endswith("…"), zeile
    assert len(zeile) <= len("14:00 ") + 30
    assert " …" not in zeile, "Leerzeichen vor den Punkten"


def test_kurzer_titel_bleibt_unangetastet():
    """Die Gegenprobe - gekürzt wird nur, was zu lang ist."""
    assert "…" not in uhr_zeile(_termin(titel="Arzt"), HEUTE)


def test_titel_ohne_inhalt_wird_benannt():
    """Ein Termin ohne Titel ist in Thunderbird erlaubt.

    Ohne Ersatzwort stünde dort nur eine Uhrzeit, und die läse sich
    wie ein Anzeigefehler.
    """
    assert uhr_zeile(_termin(titel="   "), HEUTE) == "14:00 (ohne Titel)"


def test_ohne_jetzt_stuerzt_nichts_ab():
    """Der Vorgabeweg - die Uhr ruft im Takt ohne Zeitangabe auf."""
    assert isinstance(uhr_zeile(None), str)


# --------------------------------------------------------------- Widget


def _liste(qt_app, **kwargs):
    from kalenderblick.gui.liste import TerminListe
    return TerminListe(ansicht="uhr", **kwargs)


def test_die_termine_kommen_bei_der_uhr_an(qt_app):
    """**Der eigentliche Punkt dieser Datei.**

    Die Uhr-Ansicht liegt in einem eigenen Blatt des Stapels, und
    `_aktualisiere` springt für sie gleich wieder heraus. Wer die
    Termine nur an die Liste gibt, baut eine Zeile, die im Betrieb
    für immer „Keine Termine" sagt - und das sieht nicht nach einem
    Fehler aus, sondern nach einem leeren Kalender.
    """
    liste = _liste(qt_app, termin_zeigen=True)
    liste.setze_termine([_termin()])

    assert liste._uhr._naechster.text() == "14:00 Zahnarzt"


def test_abgeschaltet_bleibt_die_zeile_unsichtbar(qt_app):
    liste = _liste(qt_app, termin_zeigen=False)
    liste.setze_termine([_termin()])

    assert not liste._uhr._naechster.isVisible()


def test_der_schalter_wirkt_in_beide_richtungen(qt_app):
    """Zweimal umschalten muss zweimal etwas tun.

    Am 2026-11-05 hatte ein Schalter den Haken gesetzt und nichts
    bewirkt, weil die Funktion beim zweiten Aufruf früh heraussprang.
    """
    liste = _liste(qt_app, termin_zeigen=False)
    liste.show()

    liste.setze_termin_zeigen(True)
    assert liste._uhr._naechster.isVisible()
    liste.setze_termin_zeigen(False)
    assert not liste._uhr._naechster.isVisible()
    liste.setze_termin_zeigen(True)
    assert liste._uhr._naechster.isVisible()


def test_jahr_und_termin_sind_unabhaengig(qt_app):
    """Die vier Kombinationen, um die Stephan gebeten hat.

    Deshalb zwei Schalter und keine Auswahlliste: Jede Mischung ist
    erreichbar, ohne dass jemand eine Liste lesen muss.
    """
    liste = _liste(qt_app)
    liste.show()

    for jahr in (False, True):
        for termin in (False, True):
            liste.setze_jahr_zeigen(jahr)
            liste.setze_termin_zeigen(termin)
            assert liste._uhr._jahr.isVisible() is jahr
            assert liste._uhr._naechster.isVisible() is termin


def test_die_zeile_entsteht_im_takt_nicht_beim_abruf(qt_app):
    """Welcher Termin der nächste ist, ändert sich ohne neue Daten.

    Stünde der Text beim Setzen fest, bliebe er bis zum nächsten
    Abruf stehen - also bis zu zehn Minuten, mit dem Hintergrundabruf
    bis zu einer halben Stunde. Deshalb merkt sich die Uhr die
    Termine und rechnet die Zeile selbst.
    """
    termine = [_termin(titel="Früh", beginn=datetime(2026, 11, 6, 10, 0)),
               _termin(titel="Spät", beginn=datetime(2026, 11, 6, 15, 0))]

    liste = _liste(qt_app, termin_zeigen=True)
    liste.setze_termine(termine)

    # Was die Uhr beim nächsten Takt zeigen würde - ohne neuen Abruf.
    gemerkt = liste._uhr._termine
    vormittags = datetime(2026, 11, 6, 9, 0)
    nachmittags = datetime(2026, 11, 6, 12, 0)

    assert uhr_zeile(naechster(gemerkt, vormittags), vormittags) == "10:00 Früh"
    assert uhr_zeile(naechster(gemerkt, nachmittags), nachmittags) == "15:00 Spät"
