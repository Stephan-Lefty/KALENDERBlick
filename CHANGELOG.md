# Änderungsprotokoll

## 1.7.2 – 2026-11-04

**Geändert**

- Das Schreibtisch-Widget sagt jetzt, wie weit es schaut. Unter dem
  letzten Eintrag steht das Enddatum der gewählten Ansicht, und liegt im
  Zeitraum gar nichts, nennt es zusätzlich den nächsten Termin dahinter.
  Vorher wirkte ein fast leeres Widget wie ein Fehler, obwohl es nur den
  kürzeren Zeitraum zeigte: Die Ansicht „14 Tage" endet am vierzehnten
  Tag, der Reiter „Termine" zeigt dagegen immer einen ganzen Monat. Ist
  gar nichts da, steht die Meldung mittig im Fenster statt oben am Rand.
- Die Kommandozeile liest dieselben Quellen wie die Oberfläche. `liste`,
  `naechster` und `kalender` sahen bisher nur in Thunderbird nach und
  übergingen Evolution, GNOME Kalender und die Abonnements - wer sie zur
  Fehlersuche benutzte, bekam dadurch ein falsches Bild.

**Behoben**

- `kalender` brach mit einem Fehler ab, sobald ein Kalender aus Evolution
  oder ein Abonnement dabei war: Die Ausgabe erwartete ein Merkmal, das
  es nur bei Thunderbird gibt.

**Dokumentation**

- Die Installationsbefehle nannten `python-icalendar` nicht, obwohl es
  seit Fassung 1.6.0 gebraucht wird. Die fertigen Pakete führen es
  ohnehin mit; betroffen war nur, wer den Anweisungen von Hand folgte.
- Xfce als vierte erprobte Arbeitsumgebung aufgenommen.
- „Terminquelle" fehlte in der Übersicht der Einstellungen.

## 1.7.1 – 2026-11-03

**Geändert**

- Betterbird wird im Programm jetzt auch benannt: Die Quellenauswahl
  heißt „Nur Thunderbird / Betterbird“, und in der Kalenderliste steht
  beides nebeneinander - von außen ist nicht zu erkennen, welches der
  beiden den gemeinsamen Profilordner angelegt hat.
- Die Beschreibung für die Software-Verwaltungen war noch auf
  Thunderbird allein zugeschnitten und nannte weder Evolution noch
  GNOME Kalender noch die Abonnements. Jetzt vollständig.

**Behoben**

- Kein seitliches Scrollen mehr. In allen drei Reitern war das Fenster
  schmaler als sein Inhalt, besonders in der Hilfe: Qt richtet die
  Spalten von Tabellen nach deren Inhalt aus, wodurch die Anleitung
  breiter wurde als das Fenster. Die Tabellen werden jetzt auf die
  Fensterbreite gezwungen, waagerechtes Scrollen ist abgeschaltet, und
  das Fenster öffnet in einer Größe, in der alle drei Reiter
  hineinpassen (780 × 700, mindestens 700 breit).
- Der Dialog zum Abonnieren öffnete zu klein: Der Erklärungstext wurde
  von den Eingabefeldern überdeckt. Ein umbrechendes Textfeld meldet
  seine Höhe zu klein, solange die Breite noch nicht feststeht - sie
  wird jetzt vorab ausgerechnet.

## 1.7.0 – 2026-11-03

**Neu**

- **Kalender unmittelbar abonnieren.** Unter „Einstellungen →
  Kalenderquellen“ lässt sich ein Kalender über seine Adresse im
  iCalendar-Format einbinden - etwa die „private Adresse“ eines
  Google-Kalenders. Damit ist KALENDERBlick auch ohne jedes
  Kalenderprogramm brauchbar. Abgerufen wird höchstens alle 30 Minuten;
  fällt das Netz aus, bleibt die zuletzt geholte Fassung stehen, statt
  dass alle Termine verschwinden.
- **GNOME Kalender** wird gelesen. Er legt seine Termine im selben
  Datenserver ab wie Evolution und war damit faktisch schon seit 1.6.0
  dabei - jetzt ist es auch so benannt.

**Zur Sicherheit**

Eine abonnierte Adresse ist ein Geheimnis: Wer sie kennt, kann den
Kalender lesen. Sie steht in der Konfigurationsdatei, die deshalb nur
noch für den eigenen Benutzer lesbar angelegt wird (0600). In Kennungen
und Dateinamen taucht sie nicht auf.

**Intern**

- Die iCalendar-Auswertung liegt jetzt in einem gemeinsamen Modul
  (`ical.py`), das sich Evolution und Abonnements teilen; `evolution.py`
  schrumpfte dadurch von 295 auf 181 Zeilen.

## 1.6.0 – 2026-11-03

**Neu**

- **Evolution wird gelesen.** Neben Thunderbird (samt Betterbird) wertet
  KALENDERBlick jetzt auch die Kalender des Evolution Data Servers aus -
  damit ist es unter GNOME auch ohne Thunderbird brauchbar. Unter
  „Einstellungen → Kalenderquellen“ lässt sich wählen, woher die Termine
  kommen: aus Thunderbird, aus Evolution oder aus beidem zusammen.
- **Einzelne Kalender abwählen.** Jeder gefundene Kalender hat ein
  Ankreuzfeld. Abgewählte erscheinen weder im Schreibtischwidget noch in
  der Terminliste - im Kalenderprogramm selbst bleibt alles unverändert
  sichtbar. Bisher ging das nur auf der Kommandozeile.
- **Übersichtlichere Kalenderliste.** Statt eines Rahmens mit vier
  Angaben je Kalender nun eine Zeile mit Farbpunkt und Namen, nach
  Herkunft gruppiert; die Einzelheiten stehen im Tooltip. Bei zwölf
  Kalendern schrumpft die Liste damit von rund 1500 auf knapp 400
  Bildpunkte Höhe.

**Anmerkung zu Online-Kalendern**

Google, Nextcloud, Proton und dergleichen bindet man weiterhin in
Thunderbird oder Evolution ein; von dort liest KALENDERBlick sie mit.
Eine eigene Anmeldung wird es nicht geben - sie würde Zugangsdaten
erfordern und damit die Zusage brechen, dass nirgends welche
einzutragen sind.

**Neue Abhängigkeit**

- `python-icalendar` (Arch) beziehungsweise `python3-icalendar`
  (Debian). Fehlt es, sagt KALENDERBlick das jetzt deutlich, statt
  stillschweigend leere Kalender anzuzeigen.

## 1.5.1 – 2026-11-03

**Behoben**

- Das Umschalten zwischen den Reitern dauerte mehrere Sekunden. Ursache:
  Läuft Thunderbird, hält es seine Kalenderdateien dauerhaft gesperrt.
  KALENDERBlick wartete bei jedem Zugriff zwei Sekunden auf diese Sperre
  und zog danach ohnehin eine Kopie - die binnen Millisekunden lesbar
  ist. Jetzt wird sofort auf die Kopie ausgewichen. Am echten Profil
  gemessen: die Kalenderliste von 6000 ms auf 21 ms, die Profilsuche von
  4000 ms auf 2 ms, bei unveränderten Ergebnissen.

## 1.5.0 – 2026-11-03

**Neu**

- Der Thunderbird-Profilordner lässt sich jetzt in der Oberfläche
  auswählen: unter „Einstellungen → Kalenderquellen“ steht, welches
  Profil verwendet wird, daneben die Knöpfe „Profilordner auswählen …“
  und „Wieder automatisch suchen“. Bisher ging das nur auf der
  Kommandozeile. Wird eine Ebene zu hoch gewählt, sucht KALENDERBlick
  den passenden Unterordner selbst.

**Geändert**

- Die Meldung bei fehlendem Profil nennt jetzt den Grund und den Ausweg,
  statt nur die Liste der durchsuchten Pfade abzuladen. Die gehört in
  `kalenderblick pruefen`, wo sie beim Suchen nach Fehlern hilft.

**Behoben**

- Im Reiter „Termine“ blieb bei fehlendem Profil nur „Keine Termine im
  gewählten Zeitraum“ stehen - als wäre alles in Ordnung und bloß nichts
  eingetragen. Das Hauptfenster hatte das Fehler-Signal gar nicht
  ausgewertet, anders als Schreibtischwidget und Leistensymbol.

## 1.4.1 – 2026-11-03

**Behoben**

- Der Autostart griff nicht: Beim Anmelden erzeugt systemd aus den
  Dateien in `~/.config/autostart/` eigene Einheiten und löst `Exec=`
  dabei gegen einen noch sehr kargen Suchpfad auf, in dem
  `~/.local/bin` fehlt. In der Datei stand nur `kalenderblick`, also
  meldete systemd „Exec binary does not exist" und legte die Einheit
  gar nicht erst an - KALENDERBlick startete beim Anmelden schlicht
  nicht. Jetzt wird der volle Pfad eingetragen.

  **Wer den Autostart schon eingeschaltet hatte, muss ihn einmal aus-
  und wieder einschalten**, damit die Datei neu geschrieben wird.

## 1.4.0 – 2026-11-03

**Neu**

- Betterbird wird mitgelesen. Der Thunderbird-Abkömmling nutzt denselben
  Profilordner `~/.thunderbird` und funktionierte deshalb schon bisher;
  neu hinzugekommen ist der abweichende Pfad der Flatpak-Fassung
  (`~/.var/app/eu.betterbird.Betterbird/`).

## 1.3.1 – 2026-11-03

**Behoben**

- Unter GNOME startete KALENDERBlick wortlos und blieb unsichtbar: Die
  Arbeitsumgebung zeigt seit Fassung 3.26 keine Leistensymbole mehr von
  sich aus an, und das Programm hat das nicht geprüft. Jetzt erscheint
  ein Hinweis samt dem Befehl für die nötige Erweiterung
  (`gnome-shell-extension-appindicator`); wäre sonst überhaupt nichts
  zu sehen, öffnet sich stattdessen das Hauptfenster.

**Geändert**

- Die Anleitung hat einen eigenen Abschnitt zu GNOME bekommen: die
  Erweiterung für das Leistensymbol und die Tatsache, dass sich unter
  GNOME/Wayland weder eine feste Position noch „hinter allen Fenstern"
  durchsetzen lässt.

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
