# Übergabe an den Code-Tab: kalenderblick

Stand: 01.11.2026. Geschrieben im Cowork-Tab, dort ohne Zugriff auf Stephans
Rechner, auf seine Thunderbird-Daten und ohne Bildschirm für die Oberfläche.

## Was gebaut werden soll

Eine Anzeige der Thunderbird-Termine, in drei Gestalten:

1. **Fenster auf dem Schreibtisch** – rahmenlos, durchscheinend, liegt hinter
   den anderen Fenstern. So soll es aussehen:

   ```
   ┌──────────────────────────┐
   │ HEUTE                    │
   │ ● 09:00–10:30  Vorstand  │
   │ ● 14:00        Zahnarzt  │
   │                          │
   │ MORGEN                   │
   │ ● ganztägig    Urlaub    │
   └──────────────────────────┘
   ```
   Der Punkt trägt die Farbe des Kalenders aus `prefs.js`.

2. **Symbol in der Kontrollleiste** – Mauszeiger-Hinweis zeigt den nächsten
   Termin (`modell.kurzfassung` liefert den Text fertig), Klick öffnet eine
   Liste, Rechtsklick ein Menü.

3. **Gewöhnliches Fenster** mit drei Reitern: Termine, Kalender (Art,
   Abholfrequenz, Stand – wie `kalenderblick kalender`), Einstellungen.

Stephans Wünsche, abgefragt: nur anzeigen, kein Schreiben, keine Erinnerungen.
Nur Manjaro KDE. Quelle ist Thunderbirds Ablage, nicht die ICS-Adressen.

## Was fertig ist

```
18 passed
```

* `paths.py` – Ablageorte
* `modell.py` – `Termin`, Tagesgruppierung, deutsche Tagesüberschriften
  („Heute", „Morgen", „Mittwoch, 4. November"), `kurzfassung()` für den
  Mauszeiger-Hinweis („In 25 min: Vorstand")
* `config.py` – Einstellungen als JSON, inklusive Lage des Schreibtischfensters
* `thunderbird.py` – **der Kern.** Profil finden, `prefs.js` auswerten,
  SQLite lesen, Wiederholungen entfalten
* `cli.py` – `pruefen`, `kalender`, `liste`, `naechster`, `einstellungen`
* `tests/hilfe.py` – baut ein Thunderbird-Profil nach, mit echtem Schema

Was `thunderbird.py` kann, jeweils durch einen Test belegt: einfache Termine,
ganztägige, wöchentliche Wiederholungen, `EXDATE`, abweichende Einzeltermine,
abgeschaltete Kalender, versteckte Kalender, Zeitzonen, Fenstergrenzen.

## Was zuerst zu tun ist

**Vor jeder Zeile Oberfläche:**

```bash
pipx install --system-site-packages ~/Github/kalenderblick
kalenderblick pruefen --beispiele
kalenderblick kalender
kalenderblick liste --ausfuehrlich
```

Das ist der Punkt, an dem sich zeigt, ob mein Leser Stephans echte
Thunderbird-Fassung trifft. Ich konnte nur gegen ein nachgebautes Schema
testen. Achte besonders darauf:

* Hat `cal_recurrence` wirklich eine Spalte `icalString`? Ältere Fassungen
  legen Wiederholungen in Einzelspalten ab (`recur_type`, `interval`, `day` …).
  Dann muss `_wiederholungszeilen()` einen zweiten Weg bekommen.
* Liegt je Kalender eine eigene `.sqlite` vor, oder gibt es noch das alte
  `local.sqlite` und `cache.sqlite`? Der Leser nimmt beides, aber die Zuordnung
  Datei → Kalendername in `lies_kalender()` ist für den alten Fall nur geraten.
* Stimmen die Uhrzeiten? Wenn alles um ein oder zwei Stunden verschoben ist,
  liegt es an `als_zeitpunkt()` und der Zeitzonenspalte.

## Oberfläche – vorgesehener Aufbau

```
gui/
  __init__.py    Weiche, prüft ob PyQt6 da ist (steht schon, gibt noch 4 zurück)
  gemeinsam.py   Lade-Thread (QThread -> list[Termin]), Farben, Symbol
  liste.py       TerminListe(QWidget) - wird von allen drei Ansichten benutzt
  desktop.py     rahmenloses, durchscheinendes Fenster
  fenster.py     gewöhnliches Fenster mit drei Reitern
  symbol.py      QSystemTrayIcon
```

`liste.py` einmal bauen und dreimal verwenden – das ist der Hebel, der die
Arbeit klein hält.

Für das Symbol bietet sich ein selbst gemaltes Blatt mit der heutigen Zahl an
(`QPainter`), dann braucht es kein Bildmaterial und es stimmt immer.

## Wayland – das muss man vorher wissen

Stephan fährt Plasma 6.7 auf **Wayland**. Zwei Dinge, die unter X11 selbstver-
ständlich wären, gehen dort nicht:

* **Ein Fenster kann sich nicht selbst positionieren.** `move(x, y)` wird
  ignoriert. Die gespeicherte Lage in `config.Fensterlage` lässt sich also
  nicht beim Start wiederherstellen.
* **`WindowStaysOnBottomHint` wird nicht beachtet.**

Der Weg unter KDE: dem Fenster einen eigenen, festen Titel und eine eigene
Fensterklasse geben (`app.setDesktopFileName("kalenderblick")`), und dann eine
KWin-Regel mitliefern, die darauf zielt:

* Position: merken, oder fest vorgeben
* Unter anderen halten: ja
* In der Fensterleiste übergehen: ja
* In der Fensterumschaltung übergehen: ja

Die Regel gehört als Datei nach `packaging/kalenderblick.kwinrule`, dazu ein
Absatz im README, wie man sie einspielt (Systemeinstellungen → Fenster­ver­
waltung → Fensterregeln → Regeln importieren). Das ist ehrlicher als zu
versuchen, Wayland zu überlisten.

Prüf vorher, ob `xdg-desktop-portal` und die Plasma-Fassung inzwischen etwas
Besseres anbieten – Plasma 6.7 ist neuer als mein Kenntnisstand.

## Danach

* `packaging/kalenderblick.desktop` für den Autostart
* PKGBUILD, wie bei `storage-box-sync`
* Repository anlegen:
  ```bash
  cd ~/Github/kalenderblick
  gh repo create kalenderblick --private --source=. --push
  ```

## Zusammenhang

Dieses Werkzeug ist aus einer Frage entstanden: Proton Calendar hat keine
Desktop-App und kein CalDAV. Stephan abonniert den Proton-Freigabe-Link in
Thunderbird; `kalenderblick` holt die Termine von dort auf den Schreibtisch.
Deshalb ist die Anzeige der Abholfrequenz kein Beiwerk, sondern der Punkt:
zwischen einer Änderung bei Proton und ihrer Anzeige liegen zwei Wartezeiten –
die von Proton am Freigabe-Link und die Abholfrequenz von Thunderbird.
