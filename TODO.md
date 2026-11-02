# TODO - KALENDERBlick

## Als Nächstes

- [ ] Erste Fassung veröffentlichen: Tag `v0.1.0` setzen und einen
      GitHub-Release anlegen - erst dann laden PKGBUILD (lädt den
      Quellcode-Tarball vom Tag) und das Release-Workflow (lädt das
      gebaute `.deb` an den Release) wirklich etwas Echtes hoch.
      Fertiger Befehl, wenn es so weit ist:
      `gh release create v0.1.0 --title "0.1.0" --generate-notes`

## Erledigt (installiert auf dem Manjaro-KDE-Rechner)

- [x] GitHub-Repository angelegt und gepusht: github.com/Stephan-Lefty/KALENDERBlick
- [x] Regulär per `pipx` installiert, Autostart und Startmenü-Eintrag
      eingerichtet, Symbole in den Icon-Theme-Ordner kopiert
- [x] KWin-Regel importiert (Systemeinstellungen → Fensterverwaltung →
      Fensterregeln → Importieren) - Position und Ziehen per
      `startSystemMove()` am echten Gerät bestätigt. „Hinter anderen
      halten", „nie in Taskleiste/Fensterwechsler" und „auf allen
      Arbeitsflächen" liegen nicht mehr in der Regel: der wmclass-Abgleich
      griff beim manuellen Start nicht zuverlässig (Fensterklasse hing vom
      tatsächlichen Programmnamen ab), deshalb erzwingt KALENDERBlick diese
      Eigenschaften jetzt selbst per KWin-Skript bei jedem Anzeigen -
      unabhängig von der Regel, funktioniert nachweislich zuverlässiger.
- [x] `packaging/PKGBUILD` für Arch/Manjaro - wie bei storage-box-sync,
      baut aus dem Quellcode-Tarball eines Tags
- [x] `.deb`-Bau über `.github/workflows/release.yml` - kein
      `debian/`-Verzeichnis mit dh-python/pybuild, sondern derselbe
      schlanke Weg wie bei storage-box-sync (venv + `dpkg-deb`); lokal
      nachgebaut und geprüft, Struktur und Inhalt stimmen
- [x] `.github/workflows/tests.yml` - nur Ubuntu, da das Programm ohnehin
      nur unter Linux läuft (Thunderbird-Profilpfade, KDE/GNOME/Cinnamon);
      Matrix 3.10/3.14 statt 3.9/3.12 - Python 3.9 hat für den neuen
      Ubuntu-26-Runner keinen Build mehr (EOL seit Oktober 2025),
      `requires-python` entsprechend auf `>=3.10` angehoben. CI geprüft
      und grün.
- [x] `pytest` in `.venv/` eingerichtet (bleibt im Repo-Ordner, ist schon
      in `.gitignore`) - 25 Tests, alle grün; README von 18 auf die
      tatsächliche Zahl korrigiert
- [x] Icon im Haus-Stil (wie HANDYHelfer): Blauverlauf, Namenszug
      KALENDER/Blick; eigene textlose Fassung für 16-32 Pixel
      (Kontrollleiste), sonst unlesbar. Im README eingebettet.
- [x] Echter Absturz behoben (SIGBUS in SQLite): Schreibtischfenster,
      Hauptfenster und Leistensymbol kopierten beim Lesen in dieselbe
      Zieldatei - eigener Ordner pro Lesevorgang statt gemeinsamer Datei
- [x] Schreibtischfenster startete minimiert, dadurch zusätzlicher Tab in
      der Fensterleiste trotz "skiptaskbar" - KWin-Regel um
      `minimized=false` (Force) ergänzt
- [x] "Schreibtisch-Widget anzeigen" (desktop_an war totes
      Konfigurationsfeld, jetzt wirksam), "Position sperren", "Auf allen
      Arbeitsflächen zeigen" (per KWin-Skript live aus der App heraus,
      nur KDE/KWin)
- [x] Scrollbalken der Terminliste entfernt (Mausrad scrollt weiter)
- [x] Widget-Ansichten auf kurze Zeiträume verschlankt (Uhr, nächste 3,
      7 Tage, 14 Tage); Hauptfenster zeigt beim Durchklicken 31 Tage
- [x] Erscheinungsbild in "Dark-Mode (weiße Schrift)" /
      "Light-Mode (schwarze Schrift)" umbenannt
- [x] "Vorausblick" aus den Einstellungen entfernt (wirkte nur auf die
      Kommandozeile, hätte in der Oberfläche nur verwirrt); stattdessen
      zeigt das Leistensymbol die Stunde des nächsten Termins als
      Abzeichen unten rechts
- [x] Uhr-Ansicht: erst quadratisch zur gewählten "Größe" gemacht, dann
      nochmal überarbeitet - die Schrift blieb dabei fast unverändert
      klein, bei "Sehr groß" also viel leere Fläche in einem 520×520-
      Kasten. Jetzt eigene, deutlich größere Schrift für die Uhr
      (`_UHR_SCHRIFT` in `gui/liste.py`, unabhängig von der kleinen
      Listen-Schrift) UND der Kasten folgt dem Inhalt (wie bei den
      anderen Ansichten) statt der festen "Größe"-Breite - bei "Klein"
      jetzt ca. 350×310 statt vorher 280×340 mit viel Leerraum
- [x] "Klick öffnet die Termine" als eigener Schalter in den
      Einstellungen, wie "Position sperren" - einmal ausgeschaltet, lässt
      sich das Widget nur noch über das Leistensymbol öffnen

## Bekannte Einschränkung (von Stephan akzeptiert)

- Der Klick zum Öffnen der Termine funktioniert zuverlässig nur bei der
  Uhr-Ansicht. Bei den anderen Ansichten (nächste 3, 7 Tage, 14 Tage)
  reagiert der Klick in der Praxis nicht, obwohl der Code dafür vorgesehen
  ist (eventFilter in `gui/desktop.py`). Stephan kann damit leben
  (02.11.2026) - bei Bedarf später genauer debuggen, z. B. ob QLabel-Zeilen
  in der Terminliste den Klick vor dem App-weiten Event-Filter abfangen.

## Für GuideOS (Cinnamon, X11)

- [ ] Sobald GuideOS läuft: Schreibtischfenster dort wirklich testen.
      `umgebung()` in `gui/gemeinsam.py` erkennt X11 bereits und lässt
      `move()` zu - ungetestet ist es trotzdem.
- [ ] `.desktop`-Datei und Symbolpfade unter Cinnamon prüfen

## Entschieden

- Feiertage/Ferien: kein eigener Code - läuft über einen zusätzlich in
  Thunderbird abonnierten Kalender (siehe README). Ein Picker oder
  automatisches Eintragen in `prefs.js` wurde erwogen und verworfen: hätte
  die Zusage „nur lesen, nie schreiben" gebrochen und riskiert, dass
  Thunderbird die Änderung beim nächsten eigenen Schreibvorgang wieder
  überschreibt.

## Pflege

- [ ] Englische Fassung des READMEs nachziehen, sobald das Repo
      veröffentlicht wird (Konvention: zweisprachig, gleicher Zug)
- [ ] Changelog im README verlinken, sobald veröffentlicht
- [ ] Hilfe-Zugang in der Oberfläche einbauen (Konvention: wer nicht
      weiterkommt, klickt auf Hilfe - noch nicht vorhanden)
