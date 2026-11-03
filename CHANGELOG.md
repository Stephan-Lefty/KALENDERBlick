# Änderungsprotokoll

## 1.3.0 – 2026-11-03

**Neu**

- Ein dritter Reiter „Hilfe" mit der vollständigen Anleitung samt
  Bildschirmfotos – mitgeliefert im Programm, also auch ohne Internet
  lesbar. Ein Knopf dort öffnet sie zusätzlich im Webbrowser, wo die
  Bilder in voller Größe erscheinen und sich ausdrucken lassen.
- Die Fassungsnummer steht jetzt sichtbar unter den Einstellungen – bei
  Rückfragen genügt ein Bildschirmfoto.
- Die Jahreszahl lässt sich wahlweise als eigene Zeile unter das Datum
  stellen (nur Uhr-Ansicht).

**Behoben**

- Das Leistensymbol wurde nur in einer einzigen Auflösung (64 × 64)
  erzeugt. Die Kontrollleiste musste es selbst herunterrechnen, wodurch
  die Linien unscharf wurden und die eigens ohne Schriftzug angelegten
  Vorlagen für 16 bis 32 Pixel gar nicht zum Zug kamen – unter
  Cinnamon/X11 deutlich zu sehen. Jetzt wird für jede übliche
  Leistengröße ein eigenes Bild erzeugt; unterhalb von 32 Pixeln zeigt
  das Abzeichen nur noch einen Punkt statt einer unleserlichen Zahl.
- Der Hinweis zu „Schreibtisch-Widget anzeigen" behauptete noch, die
  Einstellung wirke erst nach einem Neustart. Seit Fassung 1.1.0 greift
  sie sofort.

## 1.2.0 – 2026-11-03

**Neu**

- Eine weitere Größenstufe „Sehr klein" unterhalb von „Klein" – gedacht
  für ältere Geräte mit 1920er Auflösung, wo schon die bisherige
  kleinste Stufe viel Platz einnahm. Die Uhr misst damit rund
  100 × 110 Pixel statt 174 × 172.

## 1.1.2 – 2026-11-03

**Neu**

- Die Pakete bringen AppStream-Angaben mit. Dadurch taucht KALENDERBlick
  in den Software-Verwaltungen auf (GNOME Software, KDE Discover,
  Cinnamons Anwendungsverwaltung) – zum Finden, Ansehen der
  Bildschirmfotos und vor allem zum Entfernen per Mausklick. Bisher war
  dafür zwingend das Terminal nötig.

## 1.1.1 – 2026-11-03

**Behoben**

- Das `.deb`-Paket führte `python3-pyqt6` nur unter `Recommends` statt
  unter `Depends`. Wer es mit `dpkg -i` einspielte, bekam die Oberfläche
  gar nicht mit – ein Klick auf den Menüeintrag tat dann schlicht
  nichts, und die Fehlermeldung war nirgends zu sehen, weil der Eintrag
  ohne Terminal startet. Beim Arch-Paket (`PKGBUILD`) stand PyQt6
  entsprechend unter `optdepends`; auch dort ist es jetzt eine feste
  Abhängigkeit.
- `Anleitung.md` beschrieb nur den Weg über pipx. Der Abschnitt zum
  fertigen `.deb` fehlte, samt des Hinweises, dass `apt install ./datei.deb`
  und nicht `dpkg -i` zu verwenden ist.

## 1.1.0 – 2026-11-03

Alle Fehler dieser Fassung kamen heraus, als die Installation nach
`Anleitung.md` auf einem frisch bereinigten Rechner Schritt für Schritt
durchgespielt wurde. Wer 1.0.x einsetzt, sollte aktualisieren.

**Behoben**

- Das Schreibtischwidget erschien oder verschwand erst nach einem
  Neustart, wenn „Schreibtisch-Widget anzeigen" umgelegt wurde. Das
  Hauptfenster legt es jetzt sofort an beziehungsweise entfernt es.
- „Einstellungen speichern" warf das Widget aus einer an den Rand
  gezogenen Position zurück in die Bildschirmmitte.
- Das Schließen des Hauptfensters über den Fensterknopf beendete die
  ganze Anwendung samt Leistensymbol und Widget.
- „Position sperren" galt nur innerhalb einer laufenden Sitzung. Jetzt
  hält die Position auch über einen Neustart hinweg (unter KDE/KWin
  über eine eigene, automatisch verwaltete Fensterregel) - unter
  Wayland ist das der einzig mögliche Weg.
- In den Listenansichten wurde der Text unten abgeschnitten: die Höhe
  war auf die „Größe"-Vorgabe gedeckelt, obwohl sie dem Inhalt folgen
  soll. Begrenzt wird jetzt nur noch durch den Bildschirmrand.
- Nach einem Wechsel der Größe behielt das Fenster die Höhe der
  vorherigen Einstellung - die Breite stimmte sofort, die Höhe erst
  beim nächsten Speichern.
- „Einstellungen speichern" konnte aus dem sichtbaren Bereich scrollen;
  der Knopf ist jetzt fest am unteren Rand verankert.

**Geändert**

- `Anleitung.md`: Der Schritt zum Anlegen von Menüeintrag und Symbolen
  fehlte - `pipx install` richtet nur die Befehle ein.
- Die Pixelangaben in der Größen-Auswahl („Klein (280 × 340)") sind
  entfallen; die Höhe richtet sich ohnehin nach dem Inhalt.

## 1.0.1 – 2026-11-02

Das `.deb` der Fassung 1.0.0 trug noch die Versionsnummer 0.1.0:
`__init__.py` und `PKGBUILD` führen die Versionsnummer getrennt von
`pyproject.toml` und waren nicht mitgezogen worden.

## 1.0.0 – 2026-11-02

Erste öffentliche Fassung mit vollständiger Oberfläche.

- Schreibtischfenster, Leistensymbol und Hauptfenster (Termine ·
  Einstellungen), alle auf demselben Listen-Widget aufgebaut.
- Vier Ansichten für das Schreibtischwidget: Uhr + Datum, nächste 3
  Termine, nächste 7 Tage, nächste 14 Tage. Das Hauptfenster zeigt beim
  Durchklicken 31 Tage.
- Größe, Transparenz und Dark-/Light-Mode einstellbar; die Fensterhöhe
  richtet sich nach dem tatsächlichen Inhalt statt nach einer festen
  Vorgabe.
- Schalter für „Klick öffnet die Termine", „Position sperren", „Auf
  allen Arbeitsflächen zeigen" und „Beim Anmelden automatisch starten".
- Nächster Termin als Stunden-Abzeichen auf dem Leistensymbol.
- Kalenderquellen (Art, Abholfrequenz, Status) als eigener Abschnitt in
  den Einstellungen statt als eigener Reiter.
- `Anleitung.md` mit Screenshots für Installation und Einrichtung.
- Pakete für Arch (`PKGBUILD`) und Debian (`.deb` über GitHub Actions).

## 0.1.0 – 2026-11-01

Erste Fassung: Lesen von Thunderbirds Kalenderdaten (SQLite, `prefs.js`)
und Kommandozeile (`pruefen`, `kalender`, `liste`, `naechster`,
`einstellungen`, `fenster`, `start`).
