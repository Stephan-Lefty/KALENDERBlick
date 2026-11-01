"""Baut ein Thunderbird-Profil nach, wie es auf der Platte aussieht."""

from __future__ import annotations

import sqlite3
from datetime import datetime, time, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:                     # pragma: no cover
    ZoneInfo = None

SCHEMA = """
CREATE TABLE cal_events (
  cal_id TEXT, id TEXT, time_created INTEGER, last_modified INTEGER,
  title TEXT, priority INTEGER, privacy TEXT, ical_status TEXT,
  flags INTEGER, event_start INTEGER, event_start_tz TEXT,
  event_end INTEGER, event_end_tz TEXT, event_stamp INTEGER,
  alarm_last_ack INTEGER, recurrence_id INTEGER, recurrence_id_tz TEXT,
  offline_journal INTEGER);
CREATE TABLE cal_recurrence (
  item_id TEXT, cal_id TEXT, icalString TEXT, is_negative BOOLEAN);
CREATE TABLE cal_properties (
  item_id TEXT, cal_id TEXT, recurrence_id INTEGER, recurrence_id_tz TEXT,
  key TEXT, value BLOB);
CREATE TABLE cal_todos (cal_id TEXT, id TEXT, title TEXT);
"""

FLAG_GANZTAGS = 8
FLAG_WIEDERHOLUNG = 16


def zone_aus(tz: str | None):
    """Aus '/mozilla.org/20050126_1/Europe/Berlin' wird Europe/Berlin."""
    if not tz or ZoneInfo is None:
        return timezone.utc
    name = tz.rsplit("/", 2)
    name = "/".join(name[-2:]) if len(name) >= 2 else tz
    try:
        return ZoneInfo(name)
    except Exception:
        return timezone.utc


def mikro(zeitpunkt: datetime, tz: str | None = None) -> int:
    """Wie Thunderbird speichert: Mikrosekunden seit 1970 in UTC.

    Eine Uhrzeit ohne Zeitzone gilt als Ortszeit in der angegebenen Zone -
    genau so, wie der Benutzer sie in Thunderbird eingetragen hat.
    """
    if zeitpunkt.tzinfo is None:
        zeitpunkt = zeitpunkt.replace(tzinfo=zone_aus(tz))
    return int(zeitpunkt.timestamp() * 1_000_000)


def tag_mikro(tag) -> int:
    return mikro(datetime.combine(tag, time(0, 0), tzinfo=timezone.utc))


class Profil:
    def __init__(self, wurzel: Path):
        self.wurzel = wurzel
        self.profil = wurzel / ".thunderbird" / "abc123.default"
        (self.profil / "calendar-data").mkdir(parents=True)
        (wurzel / ".thunderbird" / "profiles.ini").write_text(
            "[Install4F96D1932A9F858E]\n"
            "Default=abc123.default\n"
            "Locked=1\n\n"
            "[Profile0]\n"
            "Name=default\n"
            "IsRelative=1\n"
            f"Path=abc123.default\n"
            "Default=1\n",
            encoding="utf-8",
        )
        self.prefs: list[str] = []

    # ------------------------------------------------------------------

    def kalender(self, kennung: str, name: str, farbe="#3584e4", art="storage",
                 abholung: int | None = None, abgeschaltet=False) -> sqlite3.Connection:
        self.prefs += [
            f'user_pref("calendar.registry.{kennung}.name", "{name}");',
            f'user_pref("calendar.registry.{kennung}.color", "{farbe}");',
            f'user_pref("calendar.registry.{kennung}.type", "{art}");',
        ]
        if abholung is not None:
            self.prefs.append(
                f'user_pref("calendar.registry.{kennung}.refreshInterval", {abholung});')
        if abgeschaltet:
            self.prefs.append(f'user_pref("calendar.registry.{kennung}.disabled", true);')

        datei = self.profil / "calendar-data" / f"{kennung}.sqlite"
        verbindung = sqlite3.connect(datei)
        verbindung.executescript(SCHEMA)
        verbindung.commit()
        return verbindung

    def schreibe_prefs(self) -> None:
        kopf = ("// Mozilla User Preferences\n\n"
                'user_pref("app.update.lastUpdateTime.background", 1762000000);\n')
        (self.profil / "prefs.js").write_text(
            kopf + "\n".join(self.prefs) + "\n", encoding="utf-8")


def termin(verbindung, cal_id, kennung, titel, beginn: datetime, ende: datetime,
           tz="/mozilla.org/20050126_1/Europe/Berlin", ganztags=False,
           rrule: str | None = None, exdate: str | None = None,
           recurrence_id: datetime | None = None, ort: str = "") -> None:
    flags = 0
    if ganztags:
        flags |= FLAG_GANZTAGS
    if rrule:
        flags |= FLAG_WIEDERHOLUNG

    verbindung.execute(
        "INSERT INTO cal_events (cal_id, id, title, flags, event_start, event_start_tz,"
        " event_end, event_end_tz, recurrence_id, recurrence_id_tz, privacy, ical_status)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (cal_id, kennung, titel, flags,
         mikro(beginn) if ganztags else mikro(beginn, tz), None if ganztags else tz,
         mikro(ende) if ganztags else mikro(ende, tz), None if ganztags else tz,
         mikro(recurrence_id, tz) if recurrence_id else None,
         tz if recurrence_id else None,
         "PUBLIC", "CONFIRMED"),
    )
    if rrule:
        verbindung.execute(
            "INSERT INTO cal_recurrence (item_id, cal_id, icalString, is_negative)"
            " VALUES (?,?,?,0)", (kennung, cal_id, rrule))
    if exdate:
        verbindung.execute(
            "INSERT INTO cal_recurrence (item_id, cal_id, icalString, is_negative)"
            " VALUES (?,?,?,1)", (kennung, cal_id, exdate))
    if ort:
        verbindung.execute(
            "INSERT INTO cal_properties (item_id, cal_id, key, value) VALUES (?,?,?,?)",
            (kennung, cal_id, "LOCATION", ort))
    verbindung.commit()
