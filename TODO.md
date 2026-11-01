# TODO - KALENDERBlick

## Als Nächstes

- [ ] PKGBUILD für Arch/Manjaro schreiben (wie bei storage-box-sync)
- [ ] `debian/`-Verzeichnis für ein `.deb` (dh-python, pybuild);
      Abhängigkeiten `python3-dateutil`, `python3-pyqt6`; gilt für
      DialOS und GuideOS gleichermaßen

## Erledigt (installiert auf dem Manjaro-KDE-Rechner)

- [x] GitHub-Repository angelegt und gepusht: github.com/Stephan-Lefty/kalenderblick
- [x] Regulär per `pipx` installiert, Autostart und Startmenü-Eintrag
      eingerichtet, Symbole in den Icon-Theme-Ordner kopiert
- [x] KWin-Regel importiert (Systemeinstellungen → Fensterverwaltung →
      Fensterregeln → Importieren) - Position, „hinter anderen halten" und
      Ziehen per `startSystemMove()` am echten Gerät bestätigt

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

- [ ] `pytest` in der Entwicklungsumgebung nachrüsten (aktuell nicht
      installiert, Tests konnten in dieser Sitzung nicht laufen - nur
      Syntaxprüfung und Live-Test gegen echte Daten)
- [ ] Englische Fassung des READMEs nachziehen, sobald das Repo
      veröffentlicht wird (Konvention: zweisprachig, gleicher Zug)
- [ ] Changelog im README verlinken, sobald veröffentlicht
- [ ] Hilfe-Zugang in der Oberfläche einbauen (Konvention: wer nicht
      weiterkommt, klickt auf Hilfe - noch nicht vorhanden)
