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

**Manjaro, Arch**

```bash
pamac install python-dateutil python-pyqt6 python-pipx
pipx install --system-site-packages git+https://github.com/stephan-lefty/kalenderblick.git
```

**Debian, GuideOS, Ubuntu**

```bash
sudo apt install python3-dateutil python3-pyqt6 pipx
pipx install --system-site-packages git+https://github.com/stephan-lefty/kalenderblick.git
```

KALENDERBlick ist reines Python mit Qt und hat außer `python-dateutil` keine
Abhängigkeiten. Es läuft überall dort, wo Thunderbird läuft – auch wenn
Thunderbird als Flatpak oder Snap installiert ist, denn deren Profilordner
werden mitgesucht.

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

## Feiertage und Ferien

KALENDERBlick rechnet keine Feiertage oder Ferien selbst aus - es zeigt nur,
was in Thunderbird liegt. Dafür reicht ein zusätzlicher abonnierter Kalender
in Thunderbird; KALENDERBlick liest ihn automatisch mit, wie jeden anderen.

**Feiertage** (Deutschland und Österreich, als ICS-Abo, gültig 2025-2028):

```
https://www.thunderbird.net/media/caldata/autogen/GermanHolidays.ics
https://www.thunderbird.net/media/caldata/autogen/AustrianHolidays.ics
```

**Schulferien** nach Bundesland: [ferienwiki.de/exports/de](https://www.ferienwiki.de/exports/de).
Die Links dort tragen die Jahreszahl in der URL (z. B. `.../2026/de/bayern`) -
kein Dauerabo, die Adresse muss einmal im Jahr von Hand erneuert werden.

Einrichten in Thunderbird: Kalender → Rechtsklick → Kalender erstellen →
Im Netzwerk → URL einfügen. Die Abholfrequenz lässt sich dort wie bei jedem
anderen entfernten Kalender einstellen; `kalenderblick kalender` zeigt sie an.

## Wayland und KWin

Unter KDE Plasma/Wayland kann sich ein Fenster weder selbst positionieren
noch dauerhaft unter anderen Fenstern halten - das übernimmt KWin über eine
Fensterregel. Liegt bei: `packaging/kalenderblick.kwinrule`.

Einspielen: Systemeinstellungen → Fensterverwaltung → Fensterregeln →
Regeln importieren → die Datei wählen.

Unter GNOME (Wayland) gibt es dafür keine Entsprechung - das
Schreibtischfenster verhält sich dort wie ein gewöhnliches Fenster. Unter
X11 (z. B. Cinnamon auf GuideOS) braucht es keine Regel, KALENDERBlick
positioniert sich dort selbst.

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
Oberfläche (`src/kalenderblick/gui/`) ist gebaut: Schreibtischfenster,
Leistensymbol und ein gewöhnliches Fenster mit drei Reitern, alle auf
`TerminListe` aufgebaut. Fünf Ansichten stehen zur Wahl: die nächsten drei
Termine, Tag, Woche, Monat und eine reine Uhr- und Datumsanzeige. Größe,
Transparenz und Hell/Dunkel lassen sich einstellen. Offen sind noch die
Pakete (PKGBUILD, `.deb`) und die KWin-Regel – siehe `TODO.md`.

## Lizenz

MIT
