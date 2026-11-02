"""Thunderbirds Kalenderdaten lesen - ohne Thunderbird zu stören.

Thunderbird legt je Kalender eine SQLite-Datei unter
<profil>/calendar-data/ ab. Die Namen, Farben und Abholfrequenzen der
Kalender stehen in prefs.js unter calendar.registry.<kennung>.*

Gelesen wird ausschließlich; und weil ein laufender Thunderbird die Datei
sperrt, wird vor dem Lesen eine Kopie gezogen.
"""

from __future__ import annotations

import configparser
import os
import re
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from . import paths
from .modell import Termin

try:
    from zoneinfo import ZoneInfo
except ImportError:                                    # pragma: no cover
    ZoneInfo = None                                    # type: ignore[assignment]

try:
    from dateutil.rrule import rrulestr
except ImportError:                                    # pragma: no cover
    rrulestr = None                                    # type: ignore[assignment]

# Bits in cal_events.flags
FLAG_GANZTAGS = 8
FLAG_WIEDERHOLUNG = 16

STANDARDFARBEN = ["#3584e4", "#2ec27e", "#e5a50a", "#c061cb", "#e66100", "#c01c28"]


class ThunderbirdFehler(Exception):
    """Profil oder Daten nicht auffindbar."""


# ----------------------------------------------------------------------
#  Profil finden
# ----------------------------------------------------------------------

def profil_wurzeln() -> list[Path]:
    """Mögliche Orte des Thunderbird-Profilordners."""
    heim = Path.home()
    return [
        heim / ".thunderbird",
        heim / ".mozilla-thunderbird",
        heim / ".var" / "app" / "org.mozilla.Thunderbird" / ".thunderbird",   # Flatpak
        heim / "snap" / "thunderbird" / "common" / ".thunderbird",            # Snap
    ]


def _profile_einer_wurzel(wurzel: Path) -> tuple[list[Path], set[str]]:
    """Profile einer Wurzel lesen; dazu die von Thunderbird selbst gewählten.

    In profiles.ini steht unter [InstallXXXX] ein Eintrag Default=<Pfad>.
    Das ist das Profil, mit dem Thunderbird tatsächlich startet - und nicht
    unbedingt das, das als erstes in der Datei steht.
    """
    ini = wurzel / "profiles.ini"
    if not ini.exists():
        return [], set()

    leser = configparser.ConfigParser()
    try:
        leser.read(ini, encoding="utf-8")
    except (OSError, configparser.Error):
        return [], set()

    bevorzugt: set[str] = set()
    for abschnitt in leser.sections():
        if abschnitt.lower().startswith("install"):
            ziel = leser[abschnitt].get("Default")
            if ziel:
                bevorzugt.add(ziel.strip())

    standard: list[Path] = []
    weitere: list[Path] = []
    gewaehlt: set[str] = set()

    for abschnitt in leser.sections():
        if abschnitt.lower().startswith("install"):
            continue
        werte = leser[abschnitt]
        pfad = werte.get("Path")
        if not pfad:
            continue
        voll = Path(pfad) if werte.get("IsRelative", "1") == "0" else wurzel / pfad
        if not voll.is_dir():
            continue
        if pfad.strip() in bevorzugt:
            standard.insert(0, voll)
            gewaehlt.add(str(voll))
        elif werte.get("Default", "0") == "1":
            standard.append(voll)
        else:
            weitere.append(voll)

    return standard + weitere, gewaehlt


def finde_profile() -> list[Path]:
    """Alle Profile. Das von Thunderbird gewählte steht vorn."""
    gefunden: list[Path] = []
    for wurzel in profil_wurzeln():
        pfade, _ = _profile_einer_wurzel(wurzel)
        gefunden += pfade

    if not gefunden:
        for wurzel in profil_wurzeln():
            if wurzel.is_dir():
                gefunden += [p.parent for p in wurzel.glob("*/calendar-data") if p.is_dir()]

    einmalig: list[Path] = []
    for pfad in gefunden:
        if pfad not in einmalig:
            einmalig.append(pfad)
    return einmalig


def bevorzugte_profile() -> set[str]:
    """Die Profile, die Thunderbird selbst als Startprofil führt."""
    alle: set[str] = set()
    for wurzel in profil_wurzeln():
        _, gewaehlt = _profile_einer_wurzel(wurzel)
        alle |= gewaehlt
    return alle


def termin_anzahl(profil: Path) -> int:
    """Grobe Zahl der Termine - ohne Kopie, nur zum Vergleichen von Profilen."""
    gesamt = 0
    for datei in kalenderdateien(profil):
        try:
            verbindung = sqlite3.connect(f"file:{datei}?mode=ro", uri=True, timeout=2)
            try:
                gesamt += verbindung.execute("SELECT count(*) FROM cal_events").fetchone()[0]
            finally:
                verbindung.close()
        except sqlite3.Error:
            # Gesperrt oder unlesbar: die Dateigröße muss als Anhaltspunkt reichen
            gesamt += 1 if datei.stat().st_size > 40_000 else 0
    return gesamt


def profil_vorschlaege() -> list[tuple[Path, int, int, bool]]:
    """Alle Profile mit Dateizahl, Terminzahl und ob Thunderbird es führt."""
    bevorzugt = bevorzugte_profile()
    ergebnis = []
    for pfad in finde_profile():
        ergebnis.append((
            pfad,
            len(kalenderdateien(pfad)),
            termin_anzahl(pfad),
            str(pfad) in bevorzugt,
        ))
    return ergebnis


def waehle_profil(vorgabe: str = "") -> Path:
    """Das Profil, in dem die Termine tatsächlich liegen.

    Vorrang hat ein von Hand angegebenes Profil. Sonst das Startprofil von
    Thunderbird - aber nur, wenn dort auch Termine stehen. Ein leeres
    Testprofil soll nicht gewinnen, bloß weil es zufällig vorn steht.
    """
    if vorgabe:
        pfad = Path(os.path.expanduser(vorgabe))
        if not pfad.is_dir():
            raise ThunderbirdFehler(f"Das angegebene Profil gibt es nicht: {pfad}")
        return pfad

    vorschlaege = profil_vorschlaege()
    if not vorschlaege:
        raise ThunderbirdFehler(
            "Es wurde kein Thunderbird-Profil gefunden.\n"
            "Gesucht wurde in: " + ", ".join(str(p) for p in profil_wurzeln())
        )

    mit_terminen = [v for v in vorschlaege if v[2] > 0]
    if mit_terminen:
        bevorzugt = [v for v in mit_terminen if v[3]]
        auswahl = bevorzugt or mit_terminen
        return max(auswahl, key=lambda v: v[2])[0]

    mit_dateien = [v for v in vorschlaege if v[1] > 0]
    if mit_dateien:
        return max(mit_dateien, key=lambda v: v[1])[0]
    return vorschlaege[0][0]


# ----------------------------------------------------------------------
#  prefs.js - Namen, Farben, Abholfrequenz
# ----------------------------------------------------------------------

@dataclass
class Kalender:
    kennung: str
    name: str = ""
    farbe: str = "#3584e4"
    art: str = "storage"
    abgeschaltet: bool = False
    nur_lesen: bool = False
    abholung_minuten: int | None = None     # None = nicht eingestellt
    zuletzt_geschrieben: datetime | None = None
    datei: Path | None = None
    anzahl: int = 0

    @property
    def ist_fern(self) -> bool:
        return self.art in ("ics", "caldav", "webdav")

    def abholtext(self) -> str:
        if not self.ist_fern:
            return "örtlich gespeichert, kein Abgleich nötig"
        if self.abholung_minuten is None:
            return "Abholung: Vorgabe von Thunderbird (meist 30 Minuten)"
        if self.abholung_minuten <= 0:
            return "Abholung: nur von Hand"
        if self.abholung_minuten % 60 == 0:
            return f"Abholung: alle {self.abholung_minuten // 60} Stunden"
        return f"Abholung: alle {self.abholung_minuten} Minuten"


_PREF = re.compile(r'user_pref\(\s*"calendar\.registry\.([^."]+)\.([^"]+)"\s*,\s*(.*?)\s*\);')


def lies_registry(profil: Path) -> dict[str, Kalender]:
    datei = profil / "prefs.js"
    kalender: dict[str, Kalender] = {}
    if not datei.exists():
        return kalender

    text = datei.read_text(encoding="utf-8", errors="replace")
    for kennung, schluessel, wert in _PREF.findall(text):
        wert = wert.strip()
        if wert.startswith('"') and wert.endswith('"'):
            wert = wert[1:-1]
        eintrag = kalender.setdefault(kennung, Kalender(kennung=kennung))
        if schluessel == "name":
            eintrag.name = wert.encode().decode("unicode_escape") if "\\u" in wert else wert
        elif schluessel == "color":
            eintrag.farbe = wert or eintrag.farbe
        elif schluessel == "type":
            eintrag.art = wert
        elif schluessel == "disabled":
            eintrag.abgeschaltet = wert == "true"
        elif schluessel == "readOnly":
            eintrag.nur_lesen = wert == "true"
        elif schluessel == "refreshInterval":
            try:
                eintrag.abholung_minuten = int(wert)
            except ValueError:
                pass
    return kalender


# ----------------------------------------------------------------------
#  Zeitrechnung
# ----------------------------------------------------------------------

_TZ_PRAEFIX = re.compile(r"^/[^/]*/[^/]*/")


def zeitzone(angabe: str | None):
    """Aus '/mozilla.org/20050126_1/Europe/Berlin' wird Europe/Berlin."""
    if not angabe:
        return None
    name = _TZ_PRAEFIX.sub("", angabe).strip()
    if not name or name.lower() == "floating":
        return None
    if name.upper() == "UTC":
        return timezone.utc
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(name)
    except Exception:
        return None


def als_zeitpunkt(wert: int | None, tz_angabe: str | None):
    """Mikrosekunden seit 1970 in einen Zeitpunkt mit Zeitzone wandeln.

    Thunderbird speichert in UTC und merkt sich die Zone getrennt. Gerechnet
    wird mit Zeitzone, erst zur Anzeige wird auf die Ortszeit umgestellt -
    sonst stimmen Wiederholungen über die Zeitumstellung hinweg nicht.
    """
    if wert is None:
        return None
    roh = datetime.fromtimestamp(wert / 1_000_000, tz=timezone.utc)
    zone = zeitzone(tz_angabe)
    return roh.astimezone(zone) if zone is not None else roh.astimezone()


def als_tag(wert: int | None) -> datetime | None:
    """Ganztägige Termine: der Tag zählt, nicht die Uhrzeit."""
    if wert is None:
        return None
    roh = datetime.fromtimestamp(wert / 1_000_000, tz=timezone.utc)
    return datetime.combine(roh.date(), time(0, 0))


def als_ortszeit(zeitpunkt: datetime) -> datetime:
    """Für die Anzeige: auf die Zeitzone dieses Rechners bringen."""
    if zeitpunkt.tzinfo is None:
        return zeitpunkt
    return zeitpunkt.astimezone().replace(tzinfo=None)


def _schluessel(zeitpunkt: datetime, ganztags: bool) -> int:
    """Der Wert, unter dem Thunderbird eine abweichende Wiederholung ablegt."""
    if ganztags:
        return int(datetime.combine(zeitpunkt.date(), time(0, 0),
                                    tzinfo=timezone.utc).timestamp() * 1_000_000)
    return int(zeitpunkt.timestamp() * 1_000_000)


# ----------------------------------------------------------------------
#  Datenbank lesen
# ----------------------------------------------------------------------

def _kopiere(datei: Path) -> Path:
    """Kopie in einem eigenen Ordner anlegen, damit weder ein laufender
    Thunderbird noch ein zweiter, gleichzeitiger Lesevorgang dieses
    Programms sich in die Quere kommt.

    Schreibtischfenster, Hauptfenster und Leistensymbol lesen jeweils
    unabhängig voneinander und können sich zeitlich überlappen. Ein
    gemeinsamer Dateiname hätte bedeutet, dass die Kopie mitten im Lesen
    von einem anderen Lesevorgang überschrieben wird - das hat tatsächlich
    zu Abstürzen geführt (SIGBUS in SQLite beim Lesen einer plötzlich
    verkürzten Datei). tempfile.mkdtemp() ist für genau das gemacht: ein
    garantiert eindeutiger Ordner, auch bei gleichzeitigen Aufrufen.
    """
    paths.lege_ordner_an()
    eigener_ordner = Path(tempfile.mkdtemp(prefix="lesen-", dir=paths.arbeits_ordner()))
    ziel = eigener_ordner / datei.name
    shutil.copy2(datei, ziel)
    for anhang in ("-wal", "-shm"):
        begleiter = datei.with_name(datei.name + anhang)
        if begleiter.exists():
            shutil.copy2(begleiter, ziel.with_name(ziel.name + anhang))
    return ziel


def _aufraeumen(kopie: Path) -> None:
    """Den eigenen Ordner einer Kopie wieder entfernen."""
    shutil.rmtree(kopie.parent, ignore_errors=True)


def _spalten(verbindung: sqlite3.Connection, tabelle: str) -> set[str]:
    try:
        return {z[1] for z in verbindung.execute(f"PRAGMA table_info({tabelle})")}
    except sqlite3.Error:
        return set()


def kalenderdateien(profil: Path) -> list[Path]:
    ordner = profil / "calendar-data"
    if not ordner.is_dir():
        return []
    return sorted(p for p in ordner.glob("*.sqlite") if p.is_file())


def _wiederholungszeilen(verbindung: sqlite3.Connection, kennung: str,
                         spalten: set[str]) -> list[tuple[str, bool]]:
    if "icalString" not in spalten:
        return []
    negativ = "is_negative" in spalten
    felder = "icalString" + (", is_negative" if negativ else "")
    try:
        zeilen = verbindung.execute(
            f"SELECT {felder} FROM cal_recurrence WHERE item_id = ?", (kennung,)
        ).fetchall()
    except sqlite3.Error:
        return []
    ergebnis = []
    for zeile in zeilen:
        text = zeile[0]
        if not text:
            continue
        ergebnis.append((text, bool(zeile[1]) if negativ else False))
    return ergebnis


def _zeitschluessel(zeitpunkt: datetime):
    """Vergleichbarer Schlüssel - unabhängig davon, in welcher Zone etwas steht."""
    if zeitpunkt.tzinfo is None:
        return ("ohne", zeitpunkt.replace(microsecond=0).isoformat())
    return ("mit", round(zeitpunkt.timestamp()))


def _datumsliste(zeile: str, bezug: datetime) -> list[datetime]:
    """EXDATE- und RDATE-Zeilen lesen, in der Zone des Grundtermins.

    EXDATE;TZID=Europe/Berlin:20261102T090000
    EXDATE:20261102T080000Z
    EXDATE;VALUE=DATE:20261102
    """
    kopf, _, rest = zeile.partition(":")
    zone = None
    for teil in kopf.split(";")[1:]:
        if teil.upper().startswith("TZID="):
            zone = zeitzone(teil.split("=", 1)[1])

    ergebnis: list[datetime] = []
    for stueck in rest.split(","):
        stueck = stueck.strip()
        if not stueck:
            continue
        in_utc = stueck.endswith("Z")
        roh = stueck.rstrip("Z")
        gelesen = None
        for muster in ("%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d"):
            try:
                gelesen = datetime.strptime(roh, muster)
                break
            except ValueError:
                continue
        if gelesen is None:
            continue

        if bezug.tzinfo is None:
            ergebnis.append(gelesen)
        elif in_utc:
            ergebnis.append(gelesen.replace(tzinfo=timezone.utc))
        elif zone is not None:
            ergebnis.append(gelesen.replace(tzinfo=zone))
        else:
            ergebnis.append(gelesen.replace(tzinfo=bezug.tzinfo))
    return ergebnis


def _entfalte(regeln: list[tuple[str, bool]], beginn: datetime,
              von: datetime, bis: datetime) -> list[datetime]:
    """Aus RRULE, RDATE und EXDATE die Termine im Zeitfenster errechnen."""
    if rrulestr is None:
        return [beginn] if von <= beginn <= bis else []

    zeilen_positiv: list[str] = []
    ausnahmen: set = set()

    for text, negativ in regeln:
        for zeile in str(text).splitlines():
            zeile = zeile.strip()
            if not zeile:
                continue
            kopf = zeile.split(":", 1)[0].split(";", 1)[0].upper()
            if kopf == "EXDATE" or (negativ and kopf in ("RDATE", "DTSTART")):
                for zeitpunkt in _datumsliste(zeile, beginn):
                    ausnahmen.add(_zeitschluessel(zeitpunkt))
            elif kopf == "EXRULE":
                continue                      # seit RFC 5545 abgeschafft
            elif kopf in ("RRULE", "RDATE"):
                zeilen_positiv.append(zeile)
            elif kopf.startswith("FREQ="):
                zeilen_positiv.append("RRULE:" + zeile)

    if not zeilen_positiv:
        return [beginn] if von <= beginn <= bis else []

    try:
        satz = rrulestr("\n".join(zeilen_positiv), dtstart=beginn, forceset=True)
        zeitpunkte = list(satz.between(von, bis, inc=True))
    except Exception:
        return [beginn] if von <= beginn <= bis else []

    return [z for z in zeitpunkte if _zeitschluessel(z) not in ausnahmen]


def _orte(verbindung: sqlite3.Connection, kennungen: list[str]) -> dict[str, str]:
    if not kennungen:
        return {}
    try:
        platzhalter = ",".join("?" * len(kennungen))
        zeilen = verbindung.execute(
            f"SELECT item_id, value FROM cal_properties "
            f"WHERE key = 'LOCATION' AND item_id IN ({platzhalter})",
            kennungen,
        ).fetchall()
    except sqlite3.Error:
        return {}
    return {z[0]: z[1] for z in zeilen if z[1]}


def _termin_aus(zeile, zeitpunkt: datetime, dauer, ganztags: bool,
                kalender: "Kalender", ort: str, kennung: str) -> Termin:
    beginn = zeitpunkt if ganztags else als_ortszeit(zeitpunkt)
    return Termin(
        titel=(zeile["title"] or "").strip() or "(ohne Titel)",
        beginn=beginn,
        ende=beginn + dauer,
        ganztags=ganztags,
        ort=ort,
        kalender_id=str(zeile["cal_id"]),
        kalender_name=kalender.name or str(zeile["cal_id"])[:8],
        farbe=kalender.farbe,
        kennung=f"{kennung}@{beginn.isoformat()}",
    )


def lies_datei(datei: Path, von: datetime, bis: datetime,
               registry: dict[str, Kalender]) -> tuple[list[Termin], dict[str, int]]:
    """Alle Termine einer Kalenderdatei im Zeitfenster.

    von und bis sind Ortszeit ohne Zeitzone.
    """
    kopie = _kopiere(datei)
    try:
        return _lies_kopie(kopie, von, bis, registry)
    finally:
        _aufraeumen(kopie)


def _lies_kopie(kopie: Path, von: datetime, bis: datetime,
                registry: dict[str, Kalender]) -> tuple[list[Termin], dict[str, int]]:
    termine: list[Termin] = []
    anzahl: dict[str, int] = {}

    von_zone = von.astimezone() if von.tzinfo else von.replace(tzinfo=None).astimezone()
    bis_zone = bis.astimezone() if bis.tzinfo else bis.replace(tzinfo=None).astimezone()

    verbindung = sqlite3.connect(f"file:{kopie}?mode=ro", uri=True, timeout=5)
    try:
        verbindung.row_factory = sqlite3.Row
        if not _spalten(verbindung, "cal_events"):
            return [], {}
        spalten_wdh = _spalten(verbindung, "cal_recurrence")

        zeilen = verbindung.execute("SELECT * FROM cal_events").fetchall()
        felder = set(zeilen[0].keys()) if zeilen else set()

        abweichungen: dict[tuple[str, int], object] = {}
        grundtermine = []
        for zeile in zeilen:
            wiederholung = zeile["recurrence_id"] if "recurrence_id" in felder else None
            if wiederholung:
                abweichungen[(zeile["id"], int(wiederholung))] = zeile
            else:
                grundtermine.append(zeile)

        orte = _orte(verbindung, [z["id"] for z in grundtermine])

        for zeile in grundtermine:
            kennung = zeile["id"]
            kalender_id = str(zeile["cal_id"])
            anzahl[kalender_id] = anzahl.get(kalender_id, 0) + 1

            flags = int(zeile["flags"] or 0)
            ganztags = bool(flags & FLAG_GANZTAGS)

            if ganztags:
                beginn = als_tag(zeile["event_start"])
                ende = als_tag(zeile["event_end"])
                fenster_von, fenster_bis = von, bis
            else:
                beginn = als_zeitpunkt(zeile["event_start"], zeile["event_start_tz"])
                ende = als_zeitpunkt(zeile["event_end"], zeile["event_end_tz"])
                fenster_von, fenster_bis = von_zone, bis_zone

            if beginn is None:
                continue
            if ende is None or ende < beginn:
                ende = beginn
            dauer = ende - beginn

            regeln = (_wiederholungszeilen(verbindung, kennung, spalten_wdh)
                      if flags & FLAG_WIEDERHOLUNG else [])

            if regeln:
                zeitpunkte = _entfalte(regeln, beginn, fenster_von, fenster_bis)
            elif beginn <= fenster_bis and ende >= fenster_von:
                zeitpunkte = [beginn]
            else:
                zeitpunkte = []

            kalender = registry.get(kalender_id) or Kalender(kennung=kalender_id)

            for zeitpunkt in zeitpunkte:
                abweichung = abweichungen.get((kennung, _schluessel(zeitpunkt, ganztags)))
                if abweichung is not None:
                    a_flags = int(abweichung["flags"] or 0)
                    a_ganztags = bool(a_flags & FLAG_GANZTAGS)
                    if a_ganztags:
                        a_beginn = als_tag(abweichung["event_start"])
                        a_ende = als_tag(abweichung["event_end"])
                    else:
                        a_beginn = als_zeitpunkt(
                            abweichung["event_start"], abweichung["event_start_tz"])
                        a_ende = als_zeitpunkt(
                            abweichung["event_end"], abweichung["event_end_tz"])
                    if a_beginn is None:
                        continue
                    termine.append(_termin_aus(
                        abweichung, a_beginn, (a_ende or a_beginn) - a_beginn,
                        a_ganztags, kalender, orte.get(kennung, ""), kennung))
                    continue

                termine.append(_termin_aus(
                    zeile, zeitpunkt, dauer, ganztags, kalender,
                    orte.get(kennung, ""), kennung))
    finally:
        verbindung.close()

    return termine, anzahl


# ----------------------------------------------------------------------
#  Zusammenführen
# ----------------------------------------------------------------------

def _verteilung(datei: Path) -> dict[str, int]:
    """Welche Kalender stecken in dieser Datei, mit wie vielen Terminen?

    Thunderbird legt je nach Fassung eine Datei pro Kalender an oder alles
    in local.sqlite und cache.sqlite. Die Spalte cal_id sagt es verlässlich,
    der Dateiname nicht.
    """
    for quelle in (datei, None):
        kopie = None
        try:
            if quelle is not None:
                pfad = quelle
            else:
                kopie = pfad = _kopiere(datei)
            verbindung = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True, timeout=3)
            try:
                zeilen = verbindung.execute(
                    "SELECT cal_id, count(*) FROM cal_events GROUP BY cal_id").fetchall()
                return {str(z[0]): int(z[1]) for z in zeilen}
            finally:
                verbindung.close()
        except (sqlite3.Error, OSError):
            continue
        finally:
            if kopie is not None:
                _aufraeumen(kopie)
    return {}


def lies_kalender(profil: Path) -> list[Kalender]:
    """Alle Kalender mit Art, Abholfrequenz, Datei und Stand."""
    registry = lies_registry(profil)

    zuordnung: dict[str, tuple[Path, int]] = {}
    for datei in kalenderdateien(profil):
        for kennung, menge in _verteilung(datei).items():
            frueher = zuordnung.get(kennung)
            if frueher is None or menge > frueher[1]:
                zuordnung[kennung] = (datei, menge)
        # Datei ohne Termine trotzdem zuordnen, wenn der Name die Kennung trägt
        if datei.stem not in zuordnung and datei.stem not in ("local", "cache"):
            zuordnung.setdefault(datei.stem, (datei, 0))

    ergebnis: list[Kalender] = []
    for kennung, kalender in registry.items():
        treffer = zuordnung.get(kennung)
        if treffer is not None:
            kalender.datei, kalender.anzahl = treffer
            kalender.zuletzt_geschrieben = datetime.fromtimestamp(
                kalender.datei.stat().st_mtime)
        ergebnis.append(kalender)

    bekannt = {k.kennung for k in ergebnis}
    for kennung, (datei, menge) in zuordnung.items():
        if kennung in bekannt:
            continue
        ergebnis.append(Kalender(
            kennung=kennung,
            name=f"(nicht in prefs.js, {kennung[:8]})",
            datei=datei,
            anzahl=menge,
            zuletzt_geschrieben=datetime.fromtimestamp(datei.stat().st_mtime),
        ))
    return ergebnis


def lies_termine(profil: Path, tage_voraus: int = 14, tage_zurueck: int = 0,
                 versteckt: list[str] | None = None) -> list[Termin]:
    versteckt = versteckt or []
    registry = lies_registry(profil)
    heute = date.today()
    von = datetime.combine(heute - timedelta(days=tage_zurueck), time(0, 0))
    bis = datetime.combine(heute + timedelta(days=tage_voraus), time(23, 59, 59))

    alle: list[Termin] = []
    for datei in kalenderdateien(profil):
        try:
            termine, _ = lies_datei(datei, von, bis, registry)
        except sqlite3.Error:
            continue
        alle += termine

    gefiltert = [
        t for t in alle
        if t.kalender_id not in versteckt
        and not (registry.get(t.kalender_id) and registry[t.kalender_id].abgeschaltet)
        and von <= t.beginn <= bis
    ]
    gefiltert.sort(key=lambda t: (t.beginn, not t.ganztags, t.titel))
    return gefiltert
