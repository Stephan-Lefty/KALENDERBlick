"""Thunderbird als Hintergrunddienst.

Der heikelste Teil ist das Beenden: Prozessnummern werden vom System
wiederverwendet, und ein von Hand geöffneter Thunderbird hat dieselbe
Programmdatei wie unser kopfloser - nur ohne `--headless`. Wird das
verwechselt, verliert jemand eine halb geschriebene Nachricht.
"""

import os
import subprocess
import sys
import time

import pytest

pytest.importorskip("PyQt6")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    from PyQt6.QtWidgets import QApplication
    yield QApplication.instance() or QApplication([])


@pytest.fixture
def dienst(heim):
    from kalenderblick import tb_dienst
    return tb_dienst


def _schlafender(markierung: str) -> subprocess.Popen:
    """Ein echter Prozess, dessen Befehlszeile wir vorgeben können."""
    return subprocess.Popen([sys.executable, "-c",
                             f"import time; time.sleep(30)  # {markierung}"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ----------------------------------------------------------------------
#  Erkennen, was uns gehört
# ----------------------------------------------------------------------

def test_fremder_prozess_gilt_nicht_als_unserer(dienst):
    """Die Kernabsicherung: Nur was nach kopflosem Thunderbird aussieht,
    darf ein Signal bekommen."""
    p = _schlafender("irgendein fremdes programm")
    try:
        assert not dienst._ist_unser(p.pid)
    finally:
        p.kill(); p.wait()


def test_thunderbird_ohne_headless_gilt_nicht_als_unserer(dienst):
    """Der gefährlichste Fall: ein von Hand geöffneter Thunderbird.
    Gleiche Programmdatei, aber er gehört dem Benutzer."""
    p = _schlafender("/usr/lib/thunderbird/thunderbird")
    try:
        assert not dienst._ist_unser(p.pid), \
            "ein normal geöffneter Thunderbird darf nie beendet werden"
    finally:
        p.kill(); p.wait()


def test_kopfloser_thunderbird_gilt_als_unserer(dienst):
    p = _schlafender("/usr/lib/thunderbird/thunderbird --headless")
    try:
        assert dienst._ist_unser(p.pid)
    finally:
        p.kill(); p.wait()


def test_beendeter_prozess_gilt_nicht_als_unserer(dienst):
    p = _schlafender("/usr/lib/thunderbird/thunderbird --headless")
    pid = p.pid
    p.kill(); p.wait()
    time.sleep(0.2)
    assert not dienst._ist_unser(pid)


# ----------------------------------------------------------------------
#  Beenden
# ----------------------------------------------------------------------

def test_beenden_laesst_fremden_prozess_in_ruhe(dienst):
    """Wiederverwendete Nummer: In der Merkdatei steht eine Nummer, die
    inzwischen einem anderen Programm gehört. Das darf überleben."""
    fremd = _schlafender("ein voellig anderes programm")
    try:
        dienst._merkdatei().parent.mkdir(parents=True, exist_ok=True)
        dienst._merkdatei().write_text(str(fremd.pid), encoding="utf-8")

        geklappt, _ = dienst.beende()
        time.sleep(0.3)

        assert geklappt
        assert fremd.poll() is None, "ein fremder Prozess wurde beendet!"
        assert not dienst._merkdatei().exists(), "die Merkdatei blieb liegen"
    finally:
        fremd.kill(); fremd.wait()


def test_beenden_ohne_merkdatei_ist_harmlos(dienst):
    geklappt, meldung = dienst.beende()
    assert geklappt
    assert "kein Dienst" in meldung


def test_beenden_bei_unsinniger_merkdatei(dienst):
    dienst._merkdatei().parent.mkdir(parents=True, exist_ok=True)
    dienst._merkdatei().write_text("kein text mit zahl", encoding="utf-8")
    geklappt, _ = dienst.beende()
    assert geklappt


# ----------------------------------------------------------------------
#  Zustand
# ----------------------------------------------------------------------

def test_laeuft_ist_falsch_ohne_dienst(dienst):
    assert not dienst.laeuft()


def test_laeuft_bei_eigenem_prozess(dienst):
    p = _schlafender("/usr/lib/thunderbird/thunderbird --headless")
    try:
        dienst._merkdatei().parent.mkdir(parents=True, exist_ok=True)
        dienst._merkdatei().write_text(str(p.pid), encoding="utf-8")
        assert dienst.laeuft()
    finally:
        p.kill(); p.wait()


def test_verwaistes_aufraeumen_beendet_den_eigenen(dienst):
    """Nach einem Absturz von KALENDERBlick hinge der Dienst sonst
    für immer im Speicher."""
    p = _schlafender("/usr/lib/thunderbird/thunderbird --headless")
    try:
        dienst._merkdatei().parent.mkdir(parents=True, exist_ok=True)
        dienst._merkdatei().write_text(str(p.pid), encoding="utf-8")

        assert dienst.raeume_verwaistes_auf()
        time.sleep(0.5)
        assert p.poll() is not None, "der verwaiste Dienst lief weiter"
    finally:
        if p.poll() is None:
            p.kill()
        p.wait()


def test_aufraeumen_ohne_dienst_meldet_nichts(dienst):
    assert not dienst.raeume_verwaistes_auf()


# ----------------------------------------------------------------------
#  Starten
# ----------------------------------------------------------------------

def test_start_ohne_thunderbird_meldet_das(dienst, monkeypatch):
    monkeypatch.setattr(dienst, "programm", lambda: None)
    geklappt, meldung = dienst.starte()
    assert not geklappt
    assert "Thunderbird" in meldung and "Betterbird" in meldung


def test_start_startet_nichts_wenn_thunderbird_schon_offen_ist(dienst, monkeypatch):
    """Ein zweiter Start würde nur an das vorhandene Fenster
    weitergereicht - und der Dienst wäre ohnehin überflüssig."""
    monkeypatch.setattr(dienst, "programm", lambda: "/bin/true")
    monkeypatch.setattr(dienst, "offen_ohne_uns", lambda: True)

    geklappt, meldung = dienst.starte()
    assert geklappt
    assert "bereits geöffnet" in meldung
    assert not dienst._merkdatei().exists(), "es wurde doch etwas gestartet"


def test_abholfenster_ist_deutlich_kuerzer_als_der_abstand(dienst):
    """Das Fenster hält die Profilsperre - in dieser Zeit öffnet ein
    Klick auf Thunderbird kein Fenster. Es muss also der kurze
    Ausnahmefall bleiben, nicht der Normalzustand."""
    anteil = dienst.FENSTER_SEKUNDEN / (dienst.ABSTAND_MINUTEN * 60)
    assert anteil < 0.1, f"Thunderbird wäre {anteil:.0%} der Zeit gesperrt"


# ----------------------------------------------------------------------
#  Einstellung
# ----------------------------------------------------------------------

def test_vorgabe_ist_aus(heim):
    """Ein dauerhafter Thunderbird kostet mehrere hundert Megabyte -
    das darf niemand ungefragt bekommen."""
    from kalenderblick import config
    assert config.Einstellungen().tb_hintergrund is False


def test_einstellung_bleibt_erhalten(heim):
    from kalenderblick import config
    e = config.Einstellungen()
    e.tb_hintergrund = True
    e.speichern()
    assert config.laden().tb_hintergrund is True


# ----------------------------------------------------------------------
#  Der Takt
# ----------------------------------------------------------------------

def _takt(qt_app, monkeypatch, offen=False):
    from kalenderblick import tb_dienst
    from kalenderblick.gui.gemeinsam import AbholTakt
    verlauf = []
    monkeypatch.setattr(tb_dienst, "offen_ohne_uns", lambda: offen)
    monkeypatch.setattr(tb_dienst, "starte",
                        lambda: (verlauf.append("start"), (True, ""))[1])
    monkeypatch.setattr(tb_dienst, "beende",
                        lambda: (verlauf.append("stop"), (True, ""))[1])
    return AbholTakt(), verlauf


def test_takt_holt_sofort_ab_statt_erst_in_einer_halben_stunde(qt_app, monkeypatch):
    takt, verlauf = _takt(qt_app, monkeypatch)
    takt.an()
    assert verlauf == ["start"], "wer den Schalter umlegt, will jetzt Termine"
    takt.aus()


def test_takt_startet_nichts_wenn_thunderbird_offen_ist(qt_app, monkeypatch):
    takt, verlauf = _takt(qt_app, monkeypatch, offen=True)
    takt.an()
    assert "start" not in verlauf, "Thunderbird holt bereits selbst ab"
    takt.aus()


def test_ausschalten_beendet_einen_laufenden_abruf(qt_app, monkeypatch):
    takt, verlauf = _takt(qt_app, monkeypatch)
    takt.an()
    verlauf.clear()
    takt.aus()
    assert "stop" in verlauf


def test_ausschalten_haelt_auch_die_zeitgeber_an(qt_app, monkeypatch):
    """Sonst liefe der Takt weiter und startete Thunderbird erneut,
    obwohl der Schalter aus ist."""
    takt, _ = _takt(qt_app, monkeypatch)
    takt.an()
    assert takt._takt.isActive()
    takt.aus()
    assert not takt._takt.isActive()
    assert not takt._schliesser.isActive()


def test_zweimal_einschalten_legt_keinen_zweiten_takt_an(qt_app, monkeypatch):
    takt, verlauf = _takt(qt_app, monkeypatch)
    takt.an()
    erster = verlauf.count("start")
    takt.an()
    assert verlauf.count("start") == erster, "doppelt gestartet"
    takt.aus()


def test_fenster_wird_nach_der_frist_geschlossen(qt_app, monkeypatch):
    """Ohne das bliebe Thunderbird dauerhaft offen - und mit ihm die
    Profilsperre."""
    from kalenderblick import tb_dienst
    takt, verlauf = _takt(qt_app, monkeypatch)
    monkeypatch.setattr(tb_dienst, "FENSTER_SEKUNDEN", 0.05)
    takt.an()
    assert takt._schliesser.isActive(), "kein Schließer gesetzt"
    for _ in range(40):
        qt_app.processEvents()
        time.sleep(0.02)
        if "stop" in verlauf:
            break
    assert "stop" in verlauf, "das Abholfenster wurde nie geschlossen"
    takt.aus()
