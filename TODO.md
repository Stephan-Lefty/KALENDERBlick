# TODO - KALENDERBlick

## Als Nächstes

- [ ] Schwebendes Einstellungssymbol in der Uhr-Ansicht am echten Gerät
      selbst anklicken - die Automatisierung konnte den Klick wegen des
      „unter anderen halten"-Fensters nicht zuverlässig nachstellen, ohne
      auf den echten Desktop durchzuschlagen. Mechanik ist dieselbe wie bei
      den bereits funktionierenden Knöpfen (`clicked`-Signal).
- [ ] GitHub-Repository anlegen:
      `gh repo create kalenderblick --private --source=. --push`
- [ ] PKGBUILD für Arch/Manjaro schreiben (wie bei storage-box-sync)
- [ ] `debian/`-Verzeichnis für ein `.deb` (dh-python, pybuild);
      Abhängigkeiten `python3-dateutil`, `python3-pyqt6`; gilt für
      DialOS und GuideOS gleichermaßen

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
