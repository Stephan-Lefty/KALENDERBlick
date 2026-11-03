from pathlib import Path

from kalenderblick.gui import position


def _kwin(heim, monkeypatch):
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "KDE")
    return heim / ".config" / "kwinrulesrc"


def test_speichert_neue_regel(heim, monkeypatch):
    datei = _kwin(heim, monkeypatch)
    position.speichere_feste_position("KALENDERBlick-Schreibtisch", 120, 340)

    inhalt = datei.read_text(encoding="utf-8")
    assert "[kalenderblick-position]" in inhalt
    assert "position=120,340" in inhalt
    assert "positionrule=3" in inhalt


def test_aktualisiert_bestehende_regel_statt_duplizieren(heim, monkeypatch):
    _kwin(heim, monkeypatch)
    position.speichere_feste_position("KALENDERBlick-Schreibtisch", 10, 10)
    position.speichere_feste_position("KALENDERBlick-Schreibtisch", 500, 600)

    parser = position._regeln_lesen()
    assert parser["General"]["count"] == "1"
    assert parser["kalenderblick-position"]["position"] == "500,600"


def test_bestehende_fremde_regel_bleibt_erhalten(heim, monkeypatch):
    datei = _kwin(heim, monkeypatch)
    datei.parent.mkdir(parents=True, exist_ok=True)
    datei.write_text(
        "[General]\ncount=1\nrules=andereregel\n\n"
        "[andereregel]\nDescription=Irgendein anderes Programm\nwmclass=sonstwas\n",
        encoding="utf-8",
    )

    position.speichere_feste_position("KALENDERBlick-Schreibtisch", 1, 2)

    parser = position._regeln_lesen()
    assert parser["General"]["count"] == "2"
    assert set(parser["General"]["rules"].split(",")) == {"andereregel", "kalenderblick-position"}
    assert parser["andereregel"]["Description"] == "Irgendein anderes Programm"


def test_entfernen_laesst_fremde_regel_stehen(heim, monkeypatch):
    datei = _kwin(heim, monkeypatch)
    position.speichere_feste_position("KALENDERBlick-Schreibtisch", 1, 2)
    datei_inhalt = datei.read_text(encoding="utf-8")
    assert "kalenderblick-position" in datei_inhalt

    position.entferne_feste_position()

    parser = position._regeln_lesen()
    assert "kalenderblick-position" not in parser
    assert parser["General"]["count"] == "0"


def test_entfernen_ohne_vorhandene_datei_ist_ungefaehrlich(heim, monkeypatch):
    _kwin(heim, monkeypatch)
    position.entferne_feste_position()  # darf nicht crashen


def test_ausserhalb_kde_wird_nichts_geschrieben(heim, monkeypatch):
    datei = heim / ".config" / "kwinrulesrc"
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "GNOME")
    position.speichere_feste_position("KALENDERBlick-Schreibtisch", 1, 2)
    assert not datei.exists()
