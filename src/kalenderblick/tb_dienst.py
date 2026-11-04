"""Thunderbird im Hintergrund, ohne Oberfläche.

Thunderbird ist kein Hintergrunddienst: Entfernte Kalender - CalDAV,
abonnierte Adressen - werden nur abgeholt, solange das Programm läuft.
Wer es selten öffnet, sieht in KALENDERBlick einen alten Stand.

Thunderbird kennt dafür `--headless`: Es läuft ohne Fenster und holt
trotzdem im eingestellten Takt ab (am 04.11.2026 an einem lokalen
Testserver gemessen). Das ist der einzige Weg, der auch CalDAV-Kalender
erreicht, denn deren Zugangsdaten hat nur Thunderbird selbst.

Nicht im Dauerbetrieb, sondern in **kurzen Abholfenstern**: alle 30
Minuten starten, abholen lassen, nach anderthalb Minuten wieder
beenden. Dafür gibt es zwei Gründe. Erstens belegt ein laufender
Thunderbird mehrere hundert Megabyte. Zweitens - und wichtiger - hält
er die Profilsperre: Solange er läuft, öffnet ein Klick auf
Thunderbird *kein Fenster*. Der Start wird an den kopflosen Prozess
weitergereicht, und der schaltet die Oberfläche ja gerade ab. Im
Dauerbetrieb wäre Thunderbird also gar nicht mehr zu öffnen; so ist
der Weg nur in diesen kurzen Fenstern versperrt.

Bewusst nicht von selbst eingeschaltet, und der Dienst endet mit
KALENDERBlick - was wir starten, räumen wir auch wieder weg.

**Beendet wird nur der eigene Prozess.** Vor jedem Signal wird geprüft,
ob hinter der gemerkten Nummer wirklich noch unser kopfloser
Thunderbird steckt. Nummern werden vom System wiederverwendet; ohne
diese Prüfung könnte ein fremdes Programm das Signal bekommen - im
schlimmsten Fall der eigene, von Hand geöffnete Thunderbird mitsamt
ungesicherter Nachricht.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from . import paths

# Woran der eigene Prozess zu erkennen ist
_KENNZEICHEN = "--headless"

# Abstand zwischen zwei Abholfenstern. Dieselbe Größenordnung, in der
# Thunderbird entfernte Kalender ohnehin abgleicht.
ABSTAND_MINUTEN = 30

# Wie lange ein Fenster offen bleibt. Thunderbird holt kurz nach dem
# Start ab (gemessen: erster Abruf nach rund 15 Sekunden); der Rest ist
# Luft für langsame Rechner und mehrere Kalender. Länger als nötig wäre
# schädlich, weil in dieser Zeit kein Thunderbird-Fenster aufgeht.
FENSTER_SEKUNDEN = 90


def _merkdatei() -> Path:
    return paths.zustand_ordner() / "tb-dienst.pid"


def programm() -> str | None:
    """Pfad zu Thunderbird oder Betterbird, je nachdem was da ist."""
    for name in ("thunderbird", "betterbird"):
        pfad = shutil.which(name)
        if pfad:
            return pfad
    return None


def _befehlszeile(pid: int) -> str:
    """Die Befehlszeile eines laufenden Prozesses, sonst leer."""
    try:
        roh = Path(f"/proc/{pid}/cmdline").read_bytes()
    except OSError:
        return ""
    return roh.replace(b"\0", b" ").decode("utf-8", "replace")


def _ist_unser(pid: int) -> bool:
    """Steckt hinter dieser Nummer wirklich unser kopfloser Thunderbird?

    Entscheidend vor jedem Signal: Nummern werden wiederverwendet, und
    ein normal geöffneter Thunderbird hat dieselbe Programmdatei - nur
    eben ohne `--headless`.
    """
    zeile = _befehlszeile(pid)
    if not zeile:
        return False
    return (("thunderbird" in zeile or "betterbird" in zeile)
            and _KENNZEICHEN in zeile)


def gemerkte_nummer() -> int | None:
    try:
        return int(_merkdatei().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def laeuft() -> bool:
    """Läuft unser Dienst gerade?"""
    pid = gemerkte_nummer()
    return pid is not None and _ist_unser(pid)


def offen_ohne_uns() -> bool:
    """Läuft Thunderbird bereits als gewöhnliches Fenster?

    Dann ist der Dienst überflüssig - und ein zweiter Start würde nur
    an das vorhandene Fenster weitergereicht.
    """
    eigene = gemerkte_nummer()
    for eintrag in Path("/proc").iterdir():
        if not eintrag.name.isdigit():
            continue
        pid = int(eintrag.name)
        if pid == eigene:
            continue
        zeile = _befehlszeile(pid)
        if not zeile or _KENNZEICHEN in zeile:
            continue
        if "-contentproc" in zeile:
            continue      # Kindprozess, kein eigenständiges Thunderbird
        if "/thunderbird" in zeile or "/betterbird" in zeile:
            return True
    return False


def starte() -> tuple[bool, str]:
    """Dienst starten. Gibt (geklappt, Meldung) zurück."""
    if laeuft():
        return True, "Der Hintergrunddienst läuft bereits."

    pfad = programm()
    if not pfad:
        return False, ("Weder Thunderbird noch Betterbird gefunden - "
                       "ohne eines von beiden gibt es nichts abzuholen.")

    if offen_ohne_uns():
        return True, ("Das Programm ist bereits geöffnet und holt selbst ab. "
                      "Der Dienst startet beim nächsten Abholfenster.")

    paths.lege_ordner_an()
    try:
        vorgang = subprocess.Popen(
            [pfad, _KENNZEICHEN],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,      # überlebt ein beendetes Endgerät
        )
    except OSError as fehler:
        return False, f"Start fehlgeschlagen: {fehler}"

    _merkdatei().write_text(str(vorgang.pid), encoding="utf-8")
    return True, "Hintergrunddienst gestartet."


def beende() -> tuple[bool, str]:
    """Nur den eigenen Prozess beenden - nie einen fremden."""
    pid = gemerkte_nummer()
    if pid is None:
        return True, "Es läuft kein Dienst."

    if not _ist_unser(pid):
        # Entweder längst beendet oder die Nummer gehört inzwischen
        # jemand anderem. In beiden Fällen: nichts anfassen.
        _merkdatei().unlink(missing_ok=True)
        return True, "Es läuft kein Dienst."

    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as fehler:
        return False, f"Beenden fehlgeschlagen: {fehler}"

    # Kurz auf das geordnete Ende warten; Thunderbird schreibt beim
    # Schließen noch seine Datenbanken.
    for _ in range(40):
        if not _ist_unser(pid):
            break
        time.sleep(0.25)
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass

    _merkdatei().unlink(missing_ok=True)
    return True, "Hintergrunddienst beendet."


def raeume_verwaistes_auf() -> bool:
    """Beim Start: einen Dienst aus einem abgestürzten Durchlauf beenden.

    Stirbt KALENDERBlick unsanft, bleibt der Dienst stehen - und mit ihm
    der Speicherverbrauch, von dem niemand mehr weiß, woher er kommt.
    """
    if not laeuft():
        _merkdatei().unlink(missing_ok=True)
        return False
    beende()
    return True


def abgleichen(gewuenscht: bool) -> tuple[bool, str]:
    """Zustand an die Einstellung angleichen."""
    if gewuenscht:
        return starte()
    return beende()
