from kalenderblick import autostart, paths


def test_zunaechst_nicht_aktiv(heim):
    assert not autostart.ist_aktiv()


def test_aktivieren_legt_datei_an(heim):
    autostart.aktiviere()
    assert autostart.ist_aktiv()
    datei = paths.autostart_datei()
    assert datei.exists()
    inhalt = datei.read_text(encoding="utf-8")
    # Je nach Umgebung mit vollem Pfad davor - entscheidend ist, dass
    # das Programm mit dem Unterbefehl "start" aufgerufen wird.
    assert "kalenderblick start" in inhalt
    assert inhalt.startswith("[Desktop Entry]")


def test_deaktivieren_entfernt_datei(heim):
    autostart.aktiviere()
    autostart.deaktiviere()
    assert not autostart.ist_aktiv()


def test_deaktivieren_ohne_vorherige_datei_ist_ungefaehrlich(heim):
    autostart.deaktiviere()
    assert not autostart.ist_aktiv()


def test_exec_zeile_nennt_den_vollen_pfad(heim, monkeypatch, tmp_path):
    """systemd löst Exec= beim Anmelden gegen einen noch kargen Suchpfad
    auf, in dem ~/.local/bin fehlt. Steht dort nur der Programmname, legt
    es die Autostart-Einheit gar nicht erst an - der Autostart bleibt
    dann wirkungslos."""
    unecht = tmp_path / "bin" / "kalenderblick"
    unecht.parent.mkdir(parents=True)
    unecht.write_text("#!/bin/sh\n")
    unecht.chmod(0o755)
    monkeypatch.setenv("PATH", str(unecht.parent))

    autostart.aktiviere()
    inhalt = paths.autostart_datei().read_text(encoding="utf-8")

    assert f"Exec={unecht} start" in inhalt, \
        f"Exec-Zeile ohne vollen Pfad - systemd findet das Programm nicht:\n{inhalt}"


def test_ohne_auffindbares_programm_bleibt_der_name_stehen(heim, monkeypatch):
    """Lieber eine Datei mit blankem Namen als gar keine - vielleicht
    passt der Suchpfad beim Anmelden ja doch."""
    monkeypatch.setenv("PATH", "")
    monkeypatch.setattr("sys.argv", ["/nicht/vorhanden/irgendwas"])

    autostart.aktiviere()
    inhalt = paths.autostart_datei().read_text(encoding="utf-8")
    assert "Exec=kalenderblick start" in inhalt
