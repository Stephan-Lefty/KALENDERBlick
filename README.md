# KALENDERBlick

Zeigt die Termine aus **Thunderbird** auf dem Schreibtisch und in der
Kontrollleiste – ohne Thunderbird offen zu haben und ohne Zugangsdaten
irgendwo einzutragen. Gelesen wird ausschließlich, geschrieben nie.

Gedacht für Manjaro mit KDE Plasma.

## Warum nicht einfach Rainlendar oder ein Plasma-Widget?

Weil keines von beiden an Thunderbirds Daten kommt. Rainlendar liest
iCalendar-Dateien, das Plasma-Widget „Event Calendar" kann Google und ICS –
Thunderbirds eigene Ablage kann keines von beiden. KALENDERBlick geht genau
dorthin: an die SQLite-Dateien im Profil. Damit siehst du **alle** Kalender auf
einmal, auch rein örtliche, und zwar genau so, wie Thunderbird sie kennt.

## Wie es an die Daten kommt

```
~/.thunderbird/<profil>/
   ├── prefs.js                     Namen, Farben, Art, Abholfrequenz
   └── calendar-data/
        ├── <kennung>.sqlite        ein Kalender je Datei
        └── …
```

* Zeiten stehen als Mikrosekunden seit 1970 in UTC, die Zeitzone getrennt
  daneben – deshalb wird mit Zeitzone gerechnet und erst zur Anzeige auf
  Ortszeit umgestellt.
* Wiederholungen stehen als `icalString` in `cal_recurrence` und werden mit
  `dateutil` entfaltet, samt `EXDATE` und abweichenden Einzelterminen.
* Ein laufender Thunderbird sperrt die Datei, deshalb wird vor dem Lesen eine
  Kopie gezogen.

## Installation

```bash
pamac install python-dateutil python-pyqt6
pipx install --system-site-packages git+https://github.com/stephan-lefty/kalenderblick.git
```

## Zuerst ausprobieren

```bash
kalenderblick pruefen      # was wurde gefunden, welches Schema
kalenderblick kalender     # welche Kalender, wie oft wird abgeglichen
kalenderblick liste        # die nächsten Termine als Text
```

`kalender` beantwortet die Frage, die bei einem abonnierten Proton-Kalender
zuerst kommt: **wie oft holt Thunderbird eigentlich?**

```
Proton
   Art:      ics
   Abholung: alle 30 Minuten
   Zuletzt geschrieben: 01.11.2026 09:12  (vor 18 Minuten)
```

Die Abholfrequenz stellst du in Thunderbird ein: Rechtsklick auf den Kalender →
Eigenschaften → Aktualisieren. „Zuletzt geschrieben" ist der Zeitpunkt, an dem
sich tatsächlich etwas geändert hat – holt Thunderbird ab und es gibt nichts
Neues, bleibt der Stand stehen.

## Alle Befehle

| Befehl | Zweck |
|---|---|
| `pruefen` | Profile, Dateien, Tabellen und Spalten zeigen |
| `kalender` | Kalender mit Art, Abholfrequenz und Stand |
| `liste` | kommende Termine, `--tage`, `--alles`, `--ausfuehrlich` |
| `naechster` | der nächste Termin in einer Zeile |
| `einstellungen` | Vorausblick, Aktualisierung, Kalender verstecken |
| `fenster` | Fenster öffnen |
| `start` | Leistensymbol und Schreibtischfenster |

## Stand

Der Leser und die Kommandozeile sind fertig und mit 18 Tests abgedeckt. Die
Oberfläche (`src/kalenderblick/gui/`) fehlt noch – siehe
`uebergabe-kalenderblick.md`.

## Lizenz

MIT
