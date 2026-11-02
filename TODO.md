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
      Fensterregeln → Importieren) - Position, „hinter anderen halten" und
      Ziehen per `startSystemMove()` am echten Gerät bestätigt
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
