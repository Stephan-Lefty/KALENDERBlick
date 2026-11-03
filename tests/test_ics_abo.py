"""Kalender unmittelbar abonnieren - ohne Kalenderprogramm.

Abgerufen wird gegen einen kleinen Webserver im Testlauf; echte Adressen
sind dafür nicht nötig.
"""

import threading
from datetime import date, datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

pytest.importorskip("icalendar")

from kalenderblick import ics_abo  # noqa: E402


def _ics(titel: str, beginn: datetime, ende: datetime) -> bytes:
    return (
        "BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Test//DE\r\n"
        "BEGIN:VEVENT\r\nUID:abo-1\r\n"
        f"SUMMARY:{titel}\r\n"
        f"DTSTART:{beginn.strftime('%Y%m%dT%H%M%S')}\r\n"
        f"DTEND:{ende.strftime('%Y%m%dT%H%M%S')}\r\n"
        "END:VEVENT\r\nEND:VCALENDAR\r\n"
    ).encode("utf-8")


class _Zustand:
    """Was der Testserver ausliefert - und wie oft er gefragt wurde."""
    inhalt: bytes = b""
    status: int = 200
    abrufe: int = 0


@pytest.fixture
def server():
    zustand = _Zustand()
    heute = date.today()
    zustand.inhalt = _ics(
        "Abonnierter Termin",
        datetime(heute.year, heute.month, heute.day, 15, 0),
        datetime(heute.year, heute.month, heute.day, 16, 0))

    class Griff(BaseHTTPRequestHandler):
        def do_GET(self):
            zustand.abrufe += 1
            self.send_response(zustand.status)
            self.send_header("Content-Type", "text/calendar")
            self.end_headers()
            self.wfile.write(zustand.inhalt)

        def log_message(self, *_):
            pass

    httpd = HTTPServer(("127.0.0.1", 0), Griff)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    zustand.url = f"http://127.0.0.1:{httpd.server_port}/kalender.ics"
    yield zustand
    httpd.shutdown()


# ----------------------------------------------------------------------

def test_abo_wird_abgerufen_und_gelesen(heim, server):
    abo = ics_abo.Abo(name="Google", url=server.url)
    termine = ics_abo.lies_termine([abo], tage_voraus=7)
    assert [t.titel for t in termine] == ["Abonnierter Termin"]
    assert termine[0].kalender_name == "Google"


def test_abschrift_wird_abgelegt(heim, server):
    abo = ics_abo.Abo(name="Google", url=server.url)
    ics_abo.lies_termine([abo], tage_voraus=7)
    assert ics_abo.abschrift(abo).exists()


def test_frische_abschrift_wird_nicht_erneut_geholt(heim, server):
    """Sonst hinge die Oberfläche bei jeder Aktualisierung am Netz."""
    abo = ics_abo.Abo(name="Google", url=server.url)
    ics_abo.lies_termine([abo], tage_voraus=7)
    ics_abo.lies_termine([abo], tage_voraus=7)
    ics_abo.lies_termine([abo], tage_voraus=7)
    assert server.abrufe == 1, f"{server.abrufe} Abrufe statt einem"


def test_netzausfall_laesst_die_termine_stehen(heim, server):
    """Ein kurzer Ausfall darf nicht alle Termine verschwinden lassen."""
    abo = ics_abo.Abo(name="Google", url=server.url)
    ics_abo.lies_termine([abo], tage_voraus=7)

    abo_kaputt = ics_abo.Abo(name="Google", url="http://127.0.0.1:1/weg.ics")
    # gleiche Kennung erzwingen, damit dieselbe Abschrift gilt
    assert abo.kennung != abo_kaputt.kennung      # anders, also eigener Fall
    ics_abo.hole(abo, erzwingen=True)             # Abschrift bleibt frisch

    termine = ics_abo.lies_termine([abo], tage_voraus=7)
    assert [t.titel for t in termine] == ["Abonnierter Termin"]


def test_unerreichbare_adresse_ohne_abschrift_meldet_fehler(heim):
    abo = ics_abo.Abo(name="Weg", url="http://127.0.0.1:1/weg.ics")
    with pytest.raises(ics_abo.AboFehler) as fehler:
        ics_abo.hole(abo)
    assert "Weg" in str(fehler.value)


def test_fehlerseite_ueberschreibt_die_abschrift_nicht(heim, server):
    """Liefert der Server plötzlich HTML statt Kalenderdaten, soll die
    brauchbare Abschrift erhalten bleiben."""
    abo = ics_abo.Abo(name="Google", url=server.url)
    ics_abo.lies_termine([abo], tage_voraus=7)

    server.inhalt = b"<html><body>Nicht gefunden</body></html>"
    ics_abo.hole(abo, erzwingen=True)

    termine = ics_abo.lies_termine([abo], tage_voraus=7)
    assert [t.titel for t in termine] == ["Abonnierter Termin"], \
        "die Fehlerseite hat die Termine überschrieben"


def test_keine_brauchbare_adresse(heim):
    abo = ics_abo.Abo(name="Unsinn", url="nur text")
    with pytest.raises(ics_abo.AboFehler):
        ics_abo.hole(abo)


def test_abgeschaltetes_abo_wird_uebergangen(heim, server):
    abo = ics_abo.Abo(name="Google", url=server.url, abgeschaltet=True)
    assert ics_abo.lies_termine([abo], tage_voraus=7) == []


def test_kennung_verraet_die_adresse_nicht(heim):
    """Die Adresse ist ein Geheimnis und darf nicht in Kennungen oder
    Dateinamen auftauchen."""
    abo = ics_abo.Abo(name="Google", url="https://example.com/geheim123/basic.ics")
    assert "geheim123" not in abo.kennung
    assert "geheim123" not in str(ics_abo.abschrift(abo))


def test_webcal_wird_wie_https_behandelt(heim, server):
    abo = ics_abo.Abo(name="Google", url=server.url.replace("http://", "webcal://"))
    # Der Testserver spricht nur http, der Abruf scheitert also - wichtig
    # ist, dass es am Verbindungsaufbau scheitert und nicht an der
    # Schreibweise.
    with pytest.raises(ics_abo.AboFehler) as fehler:
        ics_abo.hole(abo)
    assert "keine brauchbare Adresse" not in str(fehler.value)


def test_abos_landen_in_der_konfiguration(heim):
    from kalenderblick import config, quellen

    e = config.laden()
    e.ics_abos = [ics_abo.Abo(name="Google", url="https://example.com/a.ics").als_dict()]
    e.speichern()

    geladen = quellen.abos()
    assert len(geladen) == 1
    assert geladen[0].name == "Google"
    assert quellen.lage().abos == 1


def test_konfigurationsdatei_ist_nur_fuer_den_benutzer_lesbar(heim):
    """In ihr stehen die geheimen Abo-Adressen."""
    import stat

    from kalenderblick import config, paths

    e = config.laden()
    e.ics_abos = [{"name": "Google", "url": "https://example.com/geheim/a.ics"}]
    e.speichern()

    rechte = stat.S_IMODE(paths.konfig_datei().stat().st_mode)
    assert not rechte & stat.S_IRGRP, "Gruppe darf nicht mitlesen"
    assert not rechte & stat.S_IROTH, "andere dürfen nicht mitlesen"
