"""Das gezogene Widget muss dort bleiben, wo es hingezogen wurde.

Gemeldet am 06.11.2026 von einem Anwender unter **Arch mit Xfce**, per
Bildschirmmitschnitt: Widget nach rechts gezogen, „Position sperren"
angehakt, auf „Einstellungen speichern" geklickt – und das Widget
sprang an seinen alten Platz zurück.

**Die Ursache lag nicht beim Sperren.** Gezogen wird über
`startSystemMove()`, also durch den Fenstermanager; KALENDERBlick
erfuhr die neue Stelle nie, weil sie allein im `closeEvent` gemerkt
wurde. Unter X11 setzt `_wende_groesse_an` das Fenster anschließend auf
den gemerkten Wert – den vom letzten Beenden.

**Auf Stephans Plasma/Wayland lief dieselbe Fassung sauber**, weil dort
gar nicht positioniert wird. Genau deshalb blieb es unentdeckt: Eine
Zusage, die nur auf einer Arbeitsumgebung geprüft ist, gilt nur dort.

Die Tests hier verlangen alle die Fixture ``heim``. Ohne sie lädt
``SchreibtischFenster`` die **echte** Konfiguration des Rechners – es
nimmt keine Einstellungen entgegen, sondern holt sie sich selbst. Beim
ersten Anlauf dieser Datei ist mir genau das passiert.
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
def fenster(qt_app, heim, monkeypatch):
    """Ein Widget auf einer eigenen Konfiguration, auf (60, 60) stehend.

    **Die Sitzung wird auf X11 gestellt, und das ist der Punkt.** Genau
    dort liegt der Fehler: `_wende_groesse_an` ruft `move()` nur unter
    X11. Auf einem Wayland-Rechner - und Stephans Manjaro ist einer -
    liefen diese Tests zwar grün, berührten die fragliche Zeile aber
    nie. Ein Test, der je nach Rechner etwas anderes prüft, ist keiner.
    """
    from kalenderblick import config as konfig_modul
    from kalenderblick.gui.desktop import SchreibtischFenster

    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    e = konfig_modul.laden()
    e.desktop.x, e.desktop.y = 60, 60
    e.desktop.sichtbar = True
    e.speichern()

    w = SchreibtischFenster()
    assert w._env["x11"], "die Sitzung gilt nicht als X11 - der Test misst nichts"
    yield w
    w.close()


def _verschieben(w, x, y):
    """Nachstellen, was der Fenstermanager nach dem Ziehen meldet."""
    from PyQt6.QtCore import QPoint
    from PyQt6.QtGui import QMoveEvent

    alt = QPoint(w._e.desktop.x, w._e.desktop.y)
    w.moveEvent(QMoveEvent(QPoint(x, y), alt))


def test_verschieben_wird_gemerkt(qt_app, fenster):
    """**Der Kern.** Vorher stand hier nach dem Ziehen noch der alte Wert."""
    fenster.show()
    qt_app.processEvents()

    _verschieben(fenster, 900, 40)

    assert (fenster._e.desktop.x, fenster._e.desktop.y) == (900, 40), (
        "die gezogene Stelle kommt in den Einstellungen nicht an")


def test_unsichtbar_verschoben_zaehlt_nicht(qt_app, fenster):
    """Beim Aufbau meldet Qt Zwischenstände.

    Die sagen nichts darüber, wohin der Anwender das Widget haben will –
    würden sie mitgeschrieben, wanderte es über die Zeit von selbst.
    """
    fenster.hide()
    qt_app.processEvents()

    _verschieben(fenster, 5, 5)

    assert (fenster._e.desktop.x, fenster._e.desktop.y) == (60, 60)


def test_groessenwechsel_behaelt_die_gezogene_stelle(qt_app, fenster):
    """Der Ablauf aus dem Mitschnitt: ziehen, dann Einstellungen speichern.

    `_wende_groesse_an` läuft beim Speichern und darf das Fenster nicht
    auf einen Wert zurücksetzen, der vor dem Ziehen galt.
    """
    fenster.show()
    qt_app.processEvents()

    _verschieben(fenster, 900, 40)
    fenster._wende_groesse_an()
    qt_app.processEvents()

    assert (fenster._e.desktop.x, fenster._e.desktop.y) == (900, 40), (
        "das Speichern hat die gezogene Stelle verworfen")


def test_auch_mit_neu_einblenden(qt_app, fenster):
    """`zeige_neu=True` blendet aus und wieder ein.

    Dabei setzt der Fenstermanager das Fenster unter Umständen an eine
    eigene Stelle - die darf die gemerkte nicht überschreiben. Deshalb
    hält `_wende_groesse_an` die Zielstelle fest, bevor es `hide()`
    ruft.
    """
    fenster.show()
    qt_app.processEvents()

    _verschieben(fenster, 900, 40)
    fenster._wende_groesse_an(zeige_neu=True)
    qt_app.processEvents()

    assert (fenster._e.desktop.x, fenster._e.desktop.y) == (900, 40)


def test_speichern_ueber_die_datei_verwirft_die_stelle_nicht(qt_app, fenster):
    """**Der gemeldete Fall, vollständig nachgestellt.**

    Die 1.8.6 hat ihn nicht behoben, und der Grund steht hier: Das
    Hauptfenster schreibt beim Speichern die *Datei* - und holt sie
    sich vorher frisch, weiß also nichts von der Stelle, die das
    Widget inzwischen gemerkt hat. Danach lädt
    `aktualisiere_einstellungen` die Datei neu, und die alte Stelle
    ist wieder da.

    Mein erster Test hat das nicht gefunden, weil er `_wende_groesse_an`
    unmittelbar aufrief, statt den Weg über die Datei zu gehen.
    """
    from kalenderblick import config as konfig_modul

    fenster.show()
    qt_app.processEvents()
    _verschieben(fenster, 900, 40)

    # Was das Hauptfenster beim Klick auf „Einstellungen speichern" tut:
    # Datei laden, eine Einstellung ändern, Datei schreiben.
    e = konfig_modul.laden()
    e.desktop.position_fixiert = True
    e.speichern()

    # Und was das Widget daraufhin tut.
    fenster.aktualisiere_einstellungen()
    qt_app.processEvents()

    assert (fenster._e.desktop.x, fenster._e.desktop.y) == (900, 40), (
        "das Speichern über die Datei hat die gezogene Stelle verworfen")


def test_die_stelle_steht_danach_in_der_datei(qt_app, fenster):
    """Nicht nur im Speicher.

    Wer den Rechner herunterfährt, ohne KALENDERBlick vorher zu
    schließen, verlöre die Stelle sonst - das Sitzungsende beendet
    Programme nicht immer so sanft, dass `closeEvent` noch läuft.
    """
    from kalenderblick import config as konfig_modul

    fenster.show()
    qt_app.processEvents()
    _verschieben(fenster, 900, 40)

    e = konfig_modul.laden()
    e.desktop.position_fixiert = True
    e.speichern()
    fenster.aktualisiere_einstellungen()
    qt_app.processEvents()

    aus_der_datei = konfig_modul.laden()
    assert (aus_der_datei.desktop.x, aus_der_datei.desktop.y) == (900, 40), (
        "die Stelle steht nur im Speicher, nicht in der Datei")
