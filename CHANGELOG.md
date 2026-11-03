# Änderungsprotokoll

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
