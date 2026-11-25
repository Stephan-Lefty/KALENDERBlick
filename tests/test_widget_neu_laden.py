"""Nach dem Speichern muss das Widget die Termine neu holen.

Gemeldet von Stephan am 25.11.2026 in der Mint-VM: Er hatte das Widget
auf dem Schreibtisch laufen, solange noch kein Kalender eingerichtet
war. Dann stellte er den Profilordner auf den Testkalender um - und das
Widget blieb leer. Erst Abschalten und neu Aktivieren brachte die
Termine.

**Kein Umstand, sondern eine fehlende Zeile.** Das Widget holte seine
Termine nur beim Start und danach per Timer, also standardmäßig alle
zehn Minuten. `aktualisiere_einstellungen` setzte bloß das neue
Intervall - das ändert nichts an der Liste, die schon hängt. Das
Hauptfenster rief in `_einstellungen_geaendert` längst
`_starte_ladethread()`; beim Widget fehlte das.

Betroffen war jede Einstellung, die den Inhalt bestimmt: Profilordner,
Terminquelle, versteckte Kalender, Vorausblick. Dass das Widget nicht
nachzog, war nirgends zu sehen - es zeigte einfach weiter den alten
Stand.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qt_app():
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    yield app


@pytest.fixture
def fenster(qt_app, heim):
    """Ohne die Fixture ``heim`` läse das Widget die echte Konfiguration."""
    from kalenderblick import config as konfig_modul
    from kalenderblick.gui.desktop import SchreibtischFenster

    e = konfig_modul.laden()
    e.desktop.sichtbar = True
    e.speichern()

    w = SchreibtischFenster()
    yield w
    w.close()


def test_speichern_holt_die_termine_neu(fenster, monkeypatch):
    gerufen = []
    monkeypatch.setattr(fenster, "_starte_ladethread",
                        lambda: gerufen.append(True))
    fenster.aktualisiere_einstellungen()
    assert gerufen, (
        "aktualisiere_einstellungen() lädt die Termine nicht neu - das "
        "Widget zeigt bis zum nächsten Timer-Tick den alten Stand.")


def test_profilwechsel_kommt_beim_laden_an(fenster, monkeypatch, tmp_path):
    """Der Ladethread muss das neue Profil sehen, nicht das gemerkte."""
    from kalenderblick import config as konfig_modul

    e = konfig_modul.laden()
    e.profil = str(tmp_path / "neues_profil")
    e.speichern()

    gesehen = {}
    from kalenderblick.gui import gemeinsam

    def falsches_lesen(**kwargs):
        gesehen.update(kwargs)
        return []

    monkeypatch.setattr(gemeinsam.quellen, "lies_termine", falsches_lesen)

    fenster.aktualisiere_einstellungen()
    thread = fenster._thread
    assert thread is not None, "es wurde kein Ladethread gestartet"
    thread.wait(10_000)

    assert gesehen.get("profil_vorgabe") == str(tmp_path / "neues_profil")


def test_ein_laufender_thread_wird_nicht_verdoppelt(fenster, monkeypatch):
    """Zweimal schnell speichern darf keine zwei Threads anwerfen."""
    class Laeuft:
        def isRunning(self):
            return True

    monkeypatch.setattr(fenster, "_thread", Laeuft())
    fenster.aktualisiere_einstellungen()
    assert isinstance(fenster._thread, Laeuft), (
        "der laufende Ladethread wurde ersetzt")
