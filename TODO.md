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

## Offene Wünsche aus den Einstellungen

- [ ] Feiertage/Ferien: kein eigener Code nötig (siehe README) - das läuft
      über einen zusätzlichen abonnierten Kalender in Thunderbird. Prüfen,
      ob der Hinweis im README reicht oder ein Assistent in der GUI
      sinnvoller wäre.

## Pflege

- [ ] `pytest` in der Entwicklungsumgebung nachrüsten (aktuell nicht
      installiert, Tests konnten in dieser Sitzung nicht laufen - nur
      Syntaxprüfung und Live-Test gegen echte Daten)
- [ ] Englische Fassung des READMEs nachziehen, sobald das Repo
      veröffentlicht wird (Konvention: zweisprachig, gleicher Zug)
- [ ] Changelog im README verlinken, sobald veröffentlicht
- [ ] Hilfe-Zugang in der Oberfläche einbauen (Konvention: wer nicht
      weiterkommt, klickt auf Hilfe - noch nicht vorhanden)
