"""Erzeugt die Bildschirmfotos für die Anleitung.

Gerendert statt abfotografiert: Unter Wayland lässt sich kein einzelnes
Fenster gezielt aufnehmen - man bekommt ein Vollbild und müsste
zuschneiden, was den ganzen Schreibtisch mitliest und beim ersten
Versuch prompt fremde Inhalte erwischt hat. Qt kann seine Fenster
selbst zeichnen; das ist wiederholbar, stört niemanden und liefert
immer denselben Ausschnitt.

Alle Daten stammen aus dem Fake-Profil (werkzeuge/fakeprofil.py), das
vorher angelegt sein muss:

    python3 werkzeuge/fakeprofil.py
    python3 werkzeuge/bilder_bauen.py src/kalenderblick/hilfe/bilder
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Fester, sprechender Pfad statt eines Zufallsnamens: Er steht in den
# Einstellungen sichtbar auf dem Bild, und „kalenderblick-beispiel“
# erklärt sich von selbst, wo „/tmp/kb-bilder-6lzo_vuw“ nur Fragen
# aufwirft.
ARBEIT = Path("/tmp/kalenderblick-beispiel")
if ARBEIT.exists():
    shutil.rmtree(ARBEIT)
ARBEIT.mkdir(parents=True)
ECHTES_HEIM = Path.home()
QUELLE = ECHTES_HEIM / "KALENDERBlick-Fakeprofil/.thunderbird"

# Das Fake-Profil in ein eigenes Heimatverzeichnis kopieren und HOME
# darauf richten. Dann findet KALENDERBlick es von selbst, und in den
# Einstellungen steht keine Zeile „Von Hand gewählt: /home/<name>/…“ -
# der Benutzername hat auf einem öffentlichen Bild nichts zu suchen.
shutil.copytree(QUELLE, ARBEIT / "heim" / ".thunderbird")
FAKE = ARBEIT / "heim" / ".thunderbird" / "abc123.default"
ZIEL = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("bilder-neu")
ZIEL.mkdir(parents=True, exist_ok=True)

os.environ.update(
    QT_QPA_PLATFORM="offscreen",
    HOME=str(ARBEIT / "heim"),
    XDG_CONFIG_HOME=str(ARBEIT / "config"),
    XDG_STATE_HOME=str(ARBEIT / "state"),
    XDG_CACHE_HOME=str(ARBEIT / "cache"),
)

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout       # noqa: E402
from PyQt6.QtGui import QPixmap, QPainter, QColor, QLinearGradient   # noqa: E402
from PyQt6.QtCore import Qt, QRect                                   # noqa: E402

app = QApplication([])

from kalenderblick import config as konfig_modul                     # noqa: E402
from kalenderblick.gui.liste import TerminListe                      # noqa: E402
from kalenderblick.gui.fenster import HauptFenster                   # noqa: E402
from kalenderblick import thunderbird                                # noqa: E402

e = konfig_modul.Einstellungen()
e.profil = ""                      # automatisch finden
e.quelle = "thunderbird"
e.desktop_an = True
e.speichern()

TERMINE = thunderbird.lies_termine(FAKE, tage_voraus=31)
print(f"  {len(TERMINE)} Fake-Termine geladen")


def hintergrund(breite: int, hoehe: int) -> QPixmap:
    """Ein ruhiger Verlauf hinter dem Widget, damit man sieht, dass es
    durchscheint - ohne einen fremden Schreibtisch abzubilden."""
    bild = QPixmap(breite, hoehe)
    maler = QPainter(bild)
    verlauf = QLinearGradient(0, 0, breite, hoehe)
    verlauf.setColorAt(0.0, QColor("#2b3a52"))
    verlauf.setColorAt(0.5, QColor("#3d5272"))
    verlauf.setColorAt(1.0, QColor("#55708f"))
    maler.fillRect(QRect(0, 0, breite, hoehe), verlauf)
    maler.end()
    return bild


def widget_bild(ansicht: str, erscheinung: str, name: str,
                breite: int, hoehe: int, rand: int = 26,
                zusatzzeilen: bool = False) -> None:
    """`hoehe` ist die Obergrenze - gezeigt wird nur, was der Inhalt
    braucht. So verhält es sich auch im Betrieb: Der Kasten ist nie
    größer als nötig, sonst stünde durchscheinender Leerraum herum.

    `zusatzzeilen` schaltet in der Uhr-Ansicht Jahr und nächsten
    Termin ein. Von den beiden Uhr-Bildern zeigt eines die nackte
    Uhr, das andere beides - zwei Bilder desselben Zustands nur in
    zwei Farben wären für diese Ansicht die ärmere Auskunft.
    """
    liste = TerminListe(ansicht=ansicht, schrift=10, erscheinung=erscheinung,
                        uhr_groesse="mittel",
                        jahr_zeigen=zusatzzeilen, termin_zeigen=zusatzzeilen)
    liste.setze_termine(TERMINE)
    liste.setFixedWidth(breite)
    liste.setFixedHeight(hoehe)
    app.processEvents()
    if ansicht != "uhr":
        # Am Inhalt des Rollbereichs messen, nicht am Rahmen: dessen
        # sizeHint bleibt bei der eingestellten Höhe stehen, und dann
        # schneidet das Bild mitten in einem Eintrag ab.
        noetig = liste._inhalt.sizeHint().height() + 14
        hoehe = max(90, min(noetig, 900))
    liste.setFixedSize(breite, hoehe)
    app.processEvents()

    kasten = QWidget()
    kasten.setFixedSize(breite, hoehe)
    farbe = "#1e1e1e" if erscheinung == "dunkel" else "#fafafa"
    kasten.setStyleSheet(f"background: {farbe}; border-radius: 10px;")
    lay = QVBoxLayout(kasten)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.addWidget(liste)
    kasten.show()
    app.processEvents()

    gesamt = QPixmap(breite + 2 * rand, hoehe + 2 * rand)
    maler = QPainter(gesamt)
    maler.drawPixmap(0, 0, hintergrund(gesamt.width(), gesamt.height()))
    vorne = QPixmap(kasten.size())
    vorne.fill(QColor(farbe))
    kasten.render(vorne)
    maler.setOpacity(0.88)                 # entspricht der Vorgabe 85 %
    maler.drawPixmap(rand, rand, vorne)
    maler.end()
    gesamt.save(str(ZIEL / name))
    print(f"  {name}  {gesamt.width()}x{gesamt.height()}")


def fenster_bild(reiter: str, name: str, hoehe: int = 760) -> None:
    f = HauptFenster(verwalte_desktop=False)
    f.resize(780, hoehe)
    tabs = f.findChild(type(f.centralWidget())) if False else None
    from PyQt6.QtWidgets import QTabWidget
    tw = f.findChild(QTabWidget)
    for i in range(tw.count()):
        if reiter.lower() in tw.tabText(i).lower():
            tw.setCurrentIndex(i)
            break
    f.show()
    # Die Termine kommen aus einem Hintergrund-Thread. Ohne Warten
    # rendert man einen leeren Reiter - beim ersten Versuch genau so
    # passiert.
    import time as _zeit
    from PyQt6.QtWidgets import QLabel
    for _ in range(120):
        app.processEvents()
        _zeit.sleep(0.05)
        texte = " ".join(k.text() for k in f.findChildren(QLabel))
        if "Wochenbesprechung" in texte or "Schreibtisch-Widget" in texte \
                or "Voraussetzungen" in texte:
            break
    for _ in range(10):
        app.processEvents()
    bild = QPixmap(f.size())
    f.render(bild)
    bild.save(str(ZIEL / name))
    print(f"  {name}  {bild.width()}x{bild.height()}")


print("\n--- Schreibtischwidget ---")
for ansicht, name, b, h in [
        ("uhr", "uhr", 300, 290),
        ("naechste3", "naechste3", 420, 260),
        ("woche", "woche", 420, 600),
        ("14tage", "14tage", 420, 600)]:
    for erscheinung, kennung in (("dunkel", "dunkel"), ("hell", "hell")):
        # Nur bei der Uhr: das hellere Bild zeigt zusätzlich Jahr und
        # nächsten Termin, damit beide Zustände einmal zu sehen sind.
        widget_bild(ansicht, erscheinung, f"{name}_{kennung}.png", b, h,
                    zusatzzeilen=(ansicht == "uhr" and erscheinung == "hell"))

print("\n--- Hauptfenster ---")
fenster_bild("Termine", "hauptfenster_termine.png")
fenster_bild("Einstellungen", "hauptfenster_einstellungen.png", hoehe=900)
fenster_bild("Hilfe", "hauptfenster_hilfe.png")

shutil.rmtree(ARBEIT, ignore_errors=True)
print(f"\n  fertig: {ZIEL}")
