# TODO - KALENDERBlick

## Als Nächstes

- [ ] Unter Xfce die einzelnen Schalter einzeln prüfen (Position sperren,
      hinter anderen Fenstern, nicht in der Fensterleiste). Der
      Grundbetrieb läuft seit 04.11.2026; die Haken in der README-Tabelle
      stehen dort bisher nur, weil Xfce denselben X11-Weg nutzt wie
      Cinnamon - nachgemessen ist keiner davon.


- [ ] GNOME Online Konten einmal am lebenden System durchspielen: Konto
      in den Systemeinstellungen eintragen, „Kalender" ankreuzen,
      nachsehen ob KALENDERBlick die Termine zeigt. Nur noch eine
      Bestätigung, kein offenes Risiko: Der Data Server kennt kein
      eigenes Google-Verfahren, sondern legt solche Kalender über das
      CalDAV-Backend als cache.db ab (GOA liefert bloß die Zugangsdaten
      über module-credentials-goa.so) - und genau das lesen wir seit
      1.7.3. Ein Test bildet den Fall samt GOA-Abschnitt in der
      .source-Datei nach. Am einfachsten auf DialOS.

- [ ] Den Abholtakt einmal am Stück mit geschlossenem Thunderbird
      durchspielen: Schalter an, warten, nachsehen ob die Termine ohne
      geöffnetes Programm aktueller werden und ob Thunderbird danach
      wieder normal aufgeht. Hier ging das nicht am Stück, weil dafür
      Thunderbird geschlossen sein müsste; belegt sind bisher die
      Einzelteile (kopfloses Abholen am Testserver gemessen, die
      Taktlogik über Tests).

## Erledigt (installiert auf dem Manjaro-KDE-Rechner)

- [x] AUR verworfen (05.11.2026): Ein Paket dort zu pflegen heißt, bei
      jeder Fassung PKGBUILD und .SRCINFO nachzuziehen und einzureichen
      - bei zehn Programmen eine Daueraufgabe für eine kleine
      Zielgruppe. Das `.deb` erreicht mehr Leute und entsteht bei jedem
      Release von selbst. Das PKGBUILD bleibt, es baut sauber; wer mag,
      erzeugt sich damit ein Systempaket. Nicht wieder aufrollen, ohne
      dass Arch-Nutzer danach fragen.


- [x] Bildschirmfotos neu aufgenommen (04.11.2026, Stand 1.8.0): elf
      Bilder, erzeugt mit `werkzeuge/bilder_bauen.py` aus dem
      Fake-Profil. Gerendert statt abfotografiert - unter Wayland
      lässt sich kein einzelnes Fenster gezielt aufnehmen, und der
      Umweg über ein Vollbild erwischte prompt fremde Fensterinhalte.
      Neu dabei: der Reiter „Hilfe", der nie abgebildet war.


- [x] Fassungen 1.1.1 bis 1.3.0 an einem Vormittag (03.11.2026), alle
      aus Stephans Durchspielen auf zwei Systemen entstanden:
      - 1.1.1: `.deb` führte PyQt6 nur unter `Recommends`; wer mit
        `dpkg -i` einspielte, bekam keine Oberfläche und beim Klick auf
        den Menüeintrag passierte wortlos nichts
      - 1.1.2: AppStream-Angaben ergänzt, sonst taucht das Programm in
        keiner Software-Verwaltung auf - und lässt sich dort auch nicht
        ohne Terminal entfernen
      - 1.2.0: Größenstufe "Sehr klein" für 1920er-Bildschirme
      - 1.3.0: Reiter "Hilfe" mit der Anleitung offline im Programm,
        sichtbare Fassungsnummer, Jahreszahl unter dem Datum,
        Leistensymbol in allen Leistengrößen statt nur 64x64
      Gelernt: Versionsnummer erst anheben, wenn der Inhalt feststeht -
      der Eintrag zu 1.2.0 wurde sonst nachträglich um Dinge erweitert,
      die in der schon veröffentlichten Fassung gar nicht steckten.

- [x] v1.1.0 veröffentlicht (03.11.2026) mit den sieben Fehlern, die
      beim Durchspielen der Anleitung herauskamen - siehe CHANGELOG.md
- [x] Erste öffentliche Fassung: Repo öffentlich gestellt, v1.0.0 und
      v1.0.1 veröffentlicht (02.11.2026) - v1.0.0 hatte noch ein falsches
      Versions-Label im `.deb` (0.1.0 statt 1.0.0, `__init__.py` und
      PKGBUILD pflegen die Versionsnummer getrennt von pyproject.toml und
      waren nicht mitgezogen worden), mit v1.0.1 korrigiert
- [x] Echte Neuinstallation nach `Anleitung.md` durchgespielt
      (03.11.2026) - dabei gefunden und behoben:
      - Menüeintrag und Symbole fehlten komplett in der Anleitung
        (`pipx install` legt nur die Befehle an) - Abschnitt ergänzt
      - Schreibtisch-Widget erschien erst nach Neustart, wenn der
        Schalter umgelegt wurde - Hauptfenster verwaltet es jetzt live
      - "Einstellungen speichern" warf das Widget aus einer gezogenen
        Ecke zurück in die Mitte (Nebenwirkung des hide()/show()-Fixes
        vom Vortag, griff bei jeder Größenänderung statt nur beim
        allerersten Laden)
      - Schließen des Hauptfensters über den X-Knopf hat die ganze
        Anwendung beendet (Qts quitOnLastWindowClosed zählt das
        "Tool"-Fenster des Widgets nicht mit)
      - "Position sperren" hielt nur innerhalb einer laufenden Sitzung,
        nicht über einen Neustart - neues Modul `gui/position.py` legt
        dafür eine eigene KWin-Fensterregel an/entfernt sie, dabei auch
        den wmclass-Fehler behoben, der schon die alten
        Fenstereigenschaften-Regeln unzuverlässig machte (zweiteiliger
        wmclass-Wert verlangt einen Abgleich des Instanznamens, der
        unter Wayland vom tatsächlichen Programmnamen abhängt)
      - "Einstellungen speichern" war beim Scrollen nicht immer sichtbar
        - jetzt außerhalb der Scroll-Fläche angeheftet
      - In den Listenansichten war der Text unten abgeschnitten: die
        Höhe war auf die "Größe"-Vorgabe gedeckelt (bei "Klein" 340 px,
        gebraucht wurden ~870 px), begrenzt wird jetzt nur noch durch
        den Bildschirmrand
      - Nach einem Größenwechsel behielt das Fenster die Höhe der
        vorherigen Einstellung (Stylesheet-Schriftgrößen rechnet Qt erst
        nach einem Durchlauf der Ereignisschleife durch) - Messung jetzt
        verzögert, am Gerät über Klein → Sehr groß → Klein nachgemessen

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
- [x] Mauszeiger der Uhr-Ansicht wurde unabhängig vom Schalter "Klick
      öffnet die Termine" immer als Hand angezeigt (nur einmal beim Start
      gesetzt) - folgt jetzt dem Schalter live
- [x] Ersteinrichtung: alle Schalter im Schreibtisch-Widget-Bereich
      (Widget anzeigen, Klick öffnet die Termine, Position sperren, Auf
      allen Arbeitsflächen zeigen) starten jetzt ausgeschaltet statt
      teils vorbelegt - wer nichts einstellt, sieht erstmal nur das
      Leistensymbol
- [x] Autostart-Schalter in den Einstellungen (neues Modul
      `autostart.py`) - legt `~/.config/autostart/kalenderblick.desktop`
      an oder entfernt sie
- [x] Reiter "Kalender" in die Einstellungen verschoben, als Abschnitt
      "Kalenderquellen" - zwei Reiter statt drei, "Termine" neben
      "Kalender" ließ sonst eine eigene Kalenderansicht vermuten
- [x] `Anleitung.md` mit Fake-Daten erstellt (eigenes Profil, keine
      echten Termine) - dabei zwei echte Bugs gefunden und behoben:
      Listenansichten blieben nach dem Nachladen zu klein (Wayland
      bestätigte ein zweites `resize()` nicht, behoben mit kurzem
      hide()/show()), und die Kalenderquellen-Übersicht ignorierte das
      eingestellte Profil und zeigte immer das echte Thunderbird-Profil
- [x] Einstellungen-Reiter in eine Scroll-Fläche gepackt - mit Autostart
      und Kalenderquellen passte der Inhalt nicht mehr ohne zu quetschen
- [x] Version 1.0.0, `CHANGELOG.md` angelegt, README verlinkt es

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

- Andere Kalenderquellen als Thunderbird: **vorerst nicht** (03.11.2026).
  Die Architektur gäbe es her - `Termin` ist generisch, die Oberfläche
  ruft nur `lies_termine`, `lies_kalender` und `waehle_profil` auf, und
  `dateutil.rrule` für Wiederholungen ist schon da. Ein Leser für lokale
  `.ics`-Dateien (`python-icalendar` liegt in Arch wie Debian bereit)
  würde Evolution/GNOME Kalender fast mit abdecken, weil der seine
  Kalender ebenfalls als `.ics` ablegt - für DialOS-Nutzer ohne
  Thunderbird wäre das der interessante Fall. Zurückgestellt, weil es
  bisher niemanden gibt, der KALENDERBlick will und keinen Thunderbird
  hat; es wäre Arbeit auf Vorrat. Nicht weiterverfolgt wird ohnehin:
  ICS-Abos per URL (macht aus dem Anzeiger einen Kalender-Client) und
  CalDAV direkt (bräuchte Zugangsdaten und bräche damit die Zusage
  "ohne Zugangsdaten irgendwo einzutragen").
- Feiertage/Ferien: kein eigener Code - läuft über einen zusätzlich in
  Thunderbird abonnierten Kalender (siehe README). Ein Picker oder
  automatisches Eintragen in `prefs.js` wurde erwogen und verworfen: hätte
  die Zusage „nur lesen, nie schreiben" gebrochen und riskiert, dass
  Thunderbird die Änderung beim nächsten eigenen Schreibvorgang wieder
  überschreibt.

## Pflege

- Englische Fassung von README und Anleitung: **entfällt**, von Stephan
  am 03.11.2026 entschieden. Weicht bewusst von der sonstigen
  Zweisprachigkeits-Konvention ab - nicht wieder aufmachen.
- [x] Changelog im README verlinkt (CHANGELOG.md, 02.11.2026)
- [x] Hilfe-Zugang in der Oberfläche: Reiter „Hilfe" mit der
      mitgelieferten Anleitung samt Bildschirmfotos, dazu ein Knopf, der
      sie als HTML im Browser öffnet (1.3.0)
