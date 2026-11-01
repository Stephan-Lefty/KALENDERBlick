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


def finde_profile() -> list[Path]:
    """Alle Profile, Standardprofil zuerst."""
    gefunden: list[Path] = []
    for wurzel in profil_wurzeln():
        ini = wurzel / "profiles.ini"
        if not ini.exists():
            continue
        leser = configparser.ConfigParser()
        try:
            leser.read(ini, encoding="utf-8")
        except (OSError, configparser.Error):
            continue

        standard: list[Path] = []
        weitere: list[Path] = []
        for abschnitt in leser.sections():
            werte = leser[abschnitt]
            pfad = werte.get("Path")
            if not pfad:
                continue
            voll = Path(pfad) if werte.get("IsRelative", "1") == "0" else wurzel / pfad
            if not voll.is_dir():
                continue
            if werte.get("Default", "0") == "1" or abschnitt.startswith("Install"):
                standard.append(voll)
            else:
                weitere.append(voll)
        gefunden += standard + weitere

    # Kein profiles.ini? Dann nach calendar-data suchen.
    if not gefunden:
        for wurzel in profil_wurzeln():
            if wurzel.is_dir():
                gefunden += [p.parent for p in wurzel.glob("*/calendar-data") if p.is_dir()]

    einmalig: list[Path] = []
    for pfad in gefunden:
        if pfad not in einmalig:
            einmalig.append(pfad)
    return einmalig


def waehle_profil(vorgabe: str = "") -> Path:
    if vorgabe:
        pfad = Path(os.path.expanduser(vorgabe))
        if not pfad.is_dir():
            raise ThunderbirdFehler(f"Das angegebene Profil gibt es nicht: {pfad}")
        return pfad

    profile = finde_profile()
    if not profile:
        raise ThunderbirdFehler(
            "Es wurde kein Thunderbird-Profil gefunden.\n"
            "Gesucht wurde in: " + ", ".join(str(p) for p in profil_wurzeln())
        )
    # Das Profil mit den meisten Kalenderdateien gewinnt
    with_daten = [p for p in profile if list((p / "calendar-data").glob("*.sqlite"))]
    return with_daten[0] if with_daten else profile[0]


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
    """Kopie anlegen, damit ein laufender Thunderbird nicht stört."""
    paths.lege_ordner_an()
    ziel = paths.arbeits_ordner() / datei.name
    shutil.copy2(datei, ziel)
    for anhang in ("-wal", "-shm"):
        begleiter = datei.with_name(datei.name + anhang)
        if begleiter.exists():
            shutil.copy2(begleiter, ziel.with_name(ziel.name + anhang))
        else:
            ziel.with_name(ziel.name + anhang).unlink(missing_ok=True)
    return ziel


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


def _entfalte(regeln: list[tuple[str, bool]], beginn: datetime,
              von: datetime, bis: datetime) -> list[datetime]:
    """Aus RRULE, RDATE und EXDATE die Termine im Zeitfenster errechnen."""
    if rrulestr is None:
        return [beginn] if von <= beginn <= bis else []

    zeilen_positiv = []
    ausnahmen: set[datetime] = set()

    for text, negativ in regeln:
        for zeile in str(text).splitlines():
            zeile = zeile.strip()
            if not zeile:
                continue
            kopf = zeile.split(":", 1)[0].split(";", 1)[0].upper()
            if kopf == "EXDATE" or (negativ and kopf in ("RDATE", "")):
                for zeitpunkt in _lies_datumsliste(zeile):
                    ausnahmen.add(zeitpunkt)
            elif kopf in ("RRULE", "RDATE", "EXRULE"):
                if kopf == "EXRULE":
                    continue            # seit RFC 5545 abgeschafft, selten
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

    return [z for z in zeitpunkte if z not in ausnahmen]


def _lies_datumsliste(zeile: str) -> list[datetime]:
    teil = zeile.split(":", 1)[1] if ":" in zeile else ""
    ergebnis = []
    for stueck in teil.split(","):
        stueck = stueck.strip().rstrip("Z")
        for muster in ("%Y%m%dT%H%M%S", "%Y%m%d"):
            try:
                ergebnis.append(datetime.strptime(stueck, muster))
                break
            except ValueError:
                continue
    return ergebnis


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

def lies_kalender(profil: Path) -> list[Kalender]:
    """Alle Kalender mit Art, Abholfrequenz und Stand der Datei."""
    registry = lies_registry(profil)
    dateien = kalenderdateien(profil)

    nach_kennung: dict[str, Path] = {}
    for datei in dateien:
        nach_kennung[datei.stem] = datei

    ergebnis: list[Kalender] = []
    for kennung, kalender in registry.items():
        datei = nach_kennung.get(kennung)
        if datei is None:
            for name in ("local", "cache"):
                if name in nach_kennung and kalender.art == "storage":
                    datei = nach_kennung[name]
                    break
        if datei is not None:
            kalender.datei = datei
            kalender.zuletzt_geschrieben = datetime.fromtimestamp(datei.stat().st_mtime)
        ergebnis.append(kalender)

    # Dateien ohne Eintrag in prefs.js
    bekannt = {k.kennung for k in ergebnis}
    for stamm, datei in nach_kennung.items():
        if stamm not in bekannt and stamm not in ("local", "cache"):
            ergebnis.append(Kalender(
                kennung=stamm, name=f"(unbenannt, {stamm[:8]})", datei=datei,
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
