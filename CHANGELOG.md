# Änderungsprotokoll

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
