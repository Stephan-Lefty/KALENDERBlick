"""Was passiert, wenn die Adresse die falsche Sorte ist.

Am 07.11.2026 hat Stephan versucht, seinen Google-Kalender zu
abonnieren, und dabei die Adresse aus der Browser-Zeile genommen
(``calendar.google.com/calendar/u/0?cid=…``). Google antwortete mit
einer Anmeldeseite; KALENDERBlick schickte die durch den
Kalenderleser, und im Dialog stand eine Fehlermeldung aus fünfzig
Zeilen HTML und CSS.

**Formal war das richtig und trotzdem unbrauchbar.** Wer so etwas
liest, hält das Programm für kaputt - dabei fehlte nur das Wort, das
sagt, welche Adresse gebraucht wird.

Zwei Linien dagegen: Erkennbar falsche Adressen werden genannt, bevor
überhaupt abgerufen wird, und eine Webseite als Antwort wird als
solche benannt statt zerlegt.
"""

import pytest

from kalenderblick import ics_abo


# --------------------------------------------------- vorab erkennen


def test_google_browseradresse_wird_erkannt():
    """**Der gemeldete Fall.** Die Adresse aus der Browser-Zeile."""
    hinweis = ics_abo.adressen_hinweis(
        "https://calendar.google.com/calendar/u/0?cid=abc123")

    assert hinweis is not None
    assert ".ics" in hinweis, "der Hinweis nennt nicht, was gebraucht wird"
    assert "iCal" in hinweis


def test_auch_ohne_benutzernummer():
    """Google schreibt die Adresse nicht immer gleich."""
    assert ics_abo.adressen_hinweis(
        "https://calendar.google.com/calendar?cid=abc123") is not None


def test_einbettadresse_wird_erkannt():
    """Derselbe Fehler in Grün - die Adresse für Webseiten."""
    hinweis = ics_abo.adressen_hinweis(
        "https://calendar.google.com/calendar/embed?src=abc")

    assert hinweis is not None
    assert ".ics" in hinweis


def test_die_richtige_adresse_geht_durch():
    """**Die Gegenprobe.** Sonst hielte die Prüfung alles auf."""
    assert ics_abo.adressen_hinweis(
        "https://calendar.google.com/calendar/ical/abc%40gmail.com/"
        "private-1234/basic.ics") is None


@pytest.mark.parametrize("adresse", [
    "https://cloud.example.org/remote.php/dav/public-calendars/abc?export",
    "https://example.org/kalender.ics",
    "webcal://example.org/kalender.ics",
    "http://example.org/termine",
])
def test_fremde_anbieter_werden_nicht_abgewiesen(adresse):
    """Jeder Anbieter baut seine Adressen anders.

    Geprüft wird nur, was sich sicher sagen lässt - eine unbekannte
    Form gilt als in Ordnung. Eine Prüfung, die zu viel abweist, ist
    schlimmer als keine: Sie hält Leute auf, deren Adresse stimmt.
    """
    assert ics_abo.adressen_hinweis(adresse) is None


def test_leere_adresse():
    assert ics_abo.adressen_hinweis("   ") == "Bitte eine Adresse eintragen."


def test_etwas_das_keine_adresse_ist():
    hinweis = ics_abo.adressen_hinweis("mein kalender")
    assert hinweis is not None
    assert "https://" in hinweis


# ------------------------------------------- Webseite als Antwort


def test_html_wird_als_webseite_erkannt():
    assert ics_abo._sieht_nach_webseite_aus(
        b"<!doctype html><html lang=\"en-US\">...")


def test_auch_ohne_doctype():
    assert ics_abo._sieht_nach_webseite_aus(b"<html><head><title>Anmelden")


def test_fuehrende_leerzeichen_stoeren_nicht():
    assert ics_abo._sieht_nach_webseite_aus(b"\n\n  <!DOCTYPE HTML>\n<html>")


def test_ein_kalender_ist_keine_webseite():
    """Die Gegenprobe - sonst würde jeder Abruf abgewiesen."""
    assert not ics_abo._sieht_nach_webseite_aus(
        b"BEGIN:VCALENDAR\r\nVERSION:2.0\r\nEND:VCALENDAR\r\n")


def test_webseite_ergibt_eine_lesbare_meldung(heim, monkeypatch):
    """**Der Kern.** Keine HTML-Wand mehr, sondern ein Satz.

    Vorher stand hier der Anfang des Quelltextes der Anmeldeseite -
    mitsamt CSS, über Dutzende Zeilen.
    """
    seite = (b"<!doctype html><html lang=\"en-US\"><head>"
             + b"<style>.x{color:red}</style>" * 50 + b"</head></html>")

    class Antwort:
        def read(self):
            return seite

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(ics_abo.urllib.request, "urlopen",
                        lambda *a, **k: Antwort())

    abo = ics_abo.Abo(name="Google Kalender",
                      url="https://calendar.google.com/calendar/u/0?cid=abc")
    with pytest.raises(ics_abo.AboFehler) as fehler:
        ics_abo.hole(abo, erzwingen=True)

    text = str(fehler.value)
    assert "Webseite" in text
    assert ".ics" in text, "die Meldung sagt nicht, was gebraucht wird"
    assert "<style>" not in text, "der HTML-Quelltext steht wieder drin"
    assert "doctype" not in text.lower()
    assert len(text) < 400, f"die Meldung ist {len(text)} Zeichen lang"
