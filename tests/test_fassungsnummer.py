"""Die Fassungsnummer steht an fünf Stellen – sie müssen übereinstimmen.

Das ist keine theoretische Sorge. Bei v1.0.0 (02.11.2026) trug das
fertige Debian-Paket die Nummer 0.1.0, weil `__init__.py` und PKGBUILD
getrennt von der `pyproject.toml` gepflegt werden und niemand sie
mitgezogen hatte. Ein Release war dafür nötig.

Seit dem 06.11.2026 ist `debian/changelog` als fünfte Stelle
dazugekommen – und die ist die heikelste: Aus *ihr* nimmt
`dpkg-buildpackage` die Paketversion. Steht sie falsch, baut das Paket
trotzdem, nur eben unter der falschen Nummer. Eine Software-Verwaltung
bietet dann eine Aktualisierung an, die es nicht gibt, oder sie bietet
keine an, obwohl es eine gibt.

Nebenbei prüft diese Datei, dass die Angaben für die Software-Verwaltung
überhaupt im Paket liegen – ohne sie erscheint KALENDERBlick dort weder
zum Finden noch zum Entfernen.
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import kalenderblick

WURZEL = Path(__file__).resolve().parent.parent


def _lies(pfad: str) -> str:
    return (WURZEL / pfad).read_text(encoding="utf-8")


def test_pyproject_nennt_dieselbe_fassung():
    treffer = re.search(r'^version = "([^"]+)"', _lies("pyproject.toml"), re.M)
    assert treffer, "keine version in pyproject.toml"
    assert treffer.group(1) == kalenderblick.__version__


def test_pkgbuild_nennt_dieselbe_fassung():
    treffer = re.search(r"^pkgver=(.+)$", _lies("packaging/PKGBUILD"), re.M)
    assert treffer, "kein pkgver im PKGBUILD"
    assert treffer.group(1).strip() == kalenderblick.__version__


def test_appstream_nennt_dieselbe_fassung():
    """Eine veraltete Angabe lässt die Software-Verwaltung eine
    Aktualisierung anbieten, die es nicht gibt."""
    datei = (WURZEL / "src/kalenderblick/paketdaten"
             / "io.github.stephan_lefty.kalenderblick.metainfo.xml")
    fassungen = [e.get("version") for e in ET.parse(datei).getroot().iter("release")]

    assert fassungen, "keine <release>-Angabe"
    assert fassungen[0] == kalenderblick.__version__, (
        "die oberste <release>-Angabe ist nicht die laufende Fassung")


def test_debian_changelog_nennt_dieselbe_fassung():
    """**Die heikelste Stelle.**

    Aus ihr nimmt `dpkg-buildpackage` die Paketversion – nicht aus der
    `pyproject.toml`. Eine falsche Nummer hier fällt beim Bauen nicht
    auf, sondern erst beim Anwender.
    """
    erste = _lies("debian/changelog").splitlines()[0]
    treffer = re.match(r"^kalenderblick \(([^)]+)\)", erste)

    assert treffer, f"erste Zeile hat nicht die erwartete Form: {erste!r}"
    assert treffer.group(1) == kalenderblick.__version__


def test_das_debian_verzeichnis_ist_vollstaendig():
    """Ohne eine dieser Dateien bricht `dpkg-buildpackage` ab – oder,
    schlimmer, es baut ein Paket, das keine Distribution annimmt."""
    for name in ("control", "changelog", "copyright", "rules", "source/format"):
        assert (WURZEL / "debian" / name).is_file(), f"debian/{name} fehlt"


def test_debian_rules_ist_ausfuehrbar():
    """Sonst meldet dpkg-buildpackage nur ein dürres
    „Permission denied"."""
    import os
    rules = WURZEL / "debian" / "rules"
    assert os.access(rules, os.X_OK), "debian/rules ist nicht ausführbar"


def test_die_kurzbeschreibung_passt_in_debians_grenze():
    """Debian deckelt die erste Description-Zeile bei 80 Zeichen.

    Darüber meldet lintian `synopsis-too-long`, und der Release-Lauf
    hält an – der lintian-Schritt dort lässt keinen Befund durchgehen.
    """
    treffer = re.search(r"^Description: (.+)$", _lies("debian/control"), re.M)

    assert treffer, "keine Description in debian/control"
    assert len(treffer.group(1)) <= 80, (
        f"Kurzbeschreibung ist {len(treffer.group(1))} Zeichen lang")


def test_pyqt6_steht_unter_depends():
    """Nicht unter Recommends.

    Ein grafischer Paketinstaller zieht Recommends oft nicht mit; dann
    passiert beim Klick auf den Menüeintrag wortlos nichts. Genau daran
    scheiterte die Fassung 1.1.0.
    """
    control = _lies("debian/control")
    depends = control.split("Depends:", 1)[1].split("Description:", 1)[0]

    assert "python3-pyqt6" in depends
    assert "Recommends:" not in control, (
        "PyQt6 darf nicht nach Recommends abrutschen")


@pytest.mark.parametrize("datei", [
    "src/kalenderblick/paketdaten/kalenderblick.desktop",
    "src/kalenderblick/paketdaten/io.github.stephan_lefty.kalenderblick.metainfo.xml",
])
def test_die_paketdaten_liegen_im_paket(datei):
    """**Im Paket, nicht daneben.**

    Am 05.11.2026 fand Stephan KALENDERBlick in keiner
    Software-Verwaltung: Die Datei lag unter `packaging/` und kam damit
    bei keiner Installationsart an.
    """
    assert (WURZEL / datei).is_file()
