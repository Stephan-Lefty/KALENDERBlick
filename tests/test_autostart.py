from kalenderblick import autostart, paths


def test_zunaechst_nicht_aktiv(heim):
    assert not autostart.ist_aktiv()


def test_aktivieren_legt_datei_an(heim):
    autostart.aktiviere()
    assert autostart.ist_aktiv()
    datei = paths.autostart_datei()
    assert datei.exists()
    assert "Exec=kalenderblick start" in datei.read_text(encoding="utf-8")


def test_deaktivieren_entfernt_datei(heim):
    autostart.aktiviere()
    autostart.deaktiviere()
    assert not autostart.ist_aktiv()


def test_deaktivieren_ohne_vorherige_datei_ist_ungefaehrlich(heim):
    autostart.deaktiviere()
    assert not autostart.ist_aktiv()
