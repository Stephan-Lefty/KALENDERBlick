"""iCalendar auswerten - gemeinsam genutzt von Evolution und ICS-Abos.

Evolution legt seine Kalender als .ics-Dateien ab, abonnierte Kalender
kommen als .ics über das Netz - gelesen werden beide gleich. Deshalb
liegt die Auswertung hier und nicht in einem der beiden Module.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from pathlib import Path

from .modell import Termin

try:
    from icalendar import Calendar as _ICalendar
except ImportError:                                    # pragma: no cover
    _ICalendar = None                                  # type: ignore[assignment]

try:
    from dateutil.rrule import rrulestr
except ImportError:                                    # pragma: no cover
    rrulestr = None                                    # type: ignore[assignment]


class ICalFehler(Exception):
    """Daten unlesbar."""


class BibliothekFehlt(ICalFehler):
    """Das Paket „icalendar“ ist nicht da.

    Eigene Ausnahme, damit sie nicht zusammen mit kaputten Einzeldateien
    abgefangen wird: Ein unbrauchbarer Termin darf übersprungen werden,
    eine fehlende Bibliothek niemals - sonst stünde da ein Kalender ganz
    ohne Termine, und niemand erführe den Grund.
    """


_FEHLT_TEXT = (
    "Zum Lesen von iCalendar-Daten fehlt das Paket „icalendar“.\n"
    "Installation: pamac install python-icalendar  (Arch/Manjaro)\n"
    "              sudo apt install python3-icalendar  (Debian)"
)


def _pruefe_bibliothek() -> None:
    if _ICalendar is None:
        raise BibliothekFehlt(_FEHLT_TEXT)


def oeffne_datei(datei: Path):
    _pruefe_bibliothek()
    try:
        return _ICalendar.from_ical(datei.read_bytes())
    except (OSError, ValueError) as fehler:
        raise ICalFehler(f"{datei.name} ist unlesbar: {fehler}") from fehler


def oeffne_text(roh: bytes | str):
    _pruefe_bibliothek()
    try:
        return _ICalendar.from_ical(roh)
    except ValueError as fehler:
        raise ICalFehler(f"unlesbare iCalendar-Daten: {fehler}") from fehler


def zaehle_termine(datei: Path) -> int:
    """Wie viele Einträge die Datei enthält - 0, wenn sie unlesbar ist."""
    try:
        return sum(1 for _ in oeffne_datei(datei).walk("VEVENT"))
    except BibliothekFehlt:
        raise
    except Exception:
        return 0


def als_naiv(wert):
    """Zeitpunkte auf Ortszeit ohne Zeitzone bringen.

    Der Rest des Programms rechnet durchgehend mit naiven Zeitpunkten in
    Ortszeit; iCalendar liefert je nach Eintrag mit oder ohne Zone.
    """
    if isinstance(wert, datetime):
        if wert.tzinfo is not None:
            return wert.astimezone().replace(tzinfo=None)
        return wert
    # reines Datum = ganztägiger Termin
    return datetime.combine(wert, time(0, 0))


def _entfalte(teil, beginn: datetime, von: datetime, bis: datetime) -> list[datetime]:
    """Wiederholungen auflösen, Ausnahmen abziehen."""
    regel = teil.get("RRULE")
    if regel is None or rrulestr is None:
        return [beginn] if von <= beginn <= bis else []

    try:
        satz = rrulestr(regel.to_ical().decode(), dtstart=beginn, forceset=True)
    except (ValueError, TypeError):
        return [beginn] if von <= beginn <= bis else []

    ausnahmen = set()
    exdate = teil.get("EXDATE")
    for eintrag in (exdate if isinstance(exdate, list) else [exdate] if exdate else []):
        for wert in getattr(eintrag, "dts", []):
            ausnahmen.add(als_naiv(wert.dt).replace(microsecond=0))

    try:
        zeitpunkte = list(satz.between(von, bis, inc=True))
    except (ValueError, TypeError):
        return [beginn] if von <= beginn <= bis else []

    return [z for z in zeitpunkte if z.replace(microsecond=0) not in ausnahmen]


def termine_eines_eintrags(teil, kennung: str, name: str, farbe: str,
                           von: datetime, bis: datetime) -> list[Termin]:
    """Einen VEVENT in null, einen oder viele Termine übersetzen."""
    beginn_feld = teil.get("DTSTART")
    if beginn_feld is None:
        return []
    beginn = als_naiv(beginn_feld.dt)
    ganztags = not isinstance(beginn_feld.dt, datetime)

    ende_feld = teil.get("DTEND")
    if ende_feld is not None:
        ende = als_naiv(ende_feld.dt)
    else:
        dauer_feld = teil.get("DURATION")
        ende = beginn + (dauer_feld.dt if dauer_feld is not None else timedelta())
    if ende < beginn:
        ende = beginn
    dauer = ende - beginn

    titel = str(teil.get("SUMMARY", "")).strip() or "(ohne Titel)"
    ort = str(teil.get("LOCATION", "")).strip()
    uid = str(teil.get("UID", ""))

    return [
        Termin(
            titel=titel,
            beginn=zeitpunkt,
            ende=zeitpunkt + dauer,
            ganztags=ganztags,
            ort=ort,
            kalender_id=kennung,
            kalender_name=name,
            farbe=farbe,
            kennung=f"{uid}@{zeitpunkt.isoformat()}",
        )
        for zeitpunkt in _entfalte(teil, beginn, von, bis)
    ]


def termine_aus(kalenderdaten, kennung: str, name: str, farbe: str,
                von: datetime, bis: datetime) -> list[Termin]:
    """Alle Termine eines geöffneten Kalenders im Zeitfenster."""
    termine: list[Termin] = []
    for teil in kalenderdaten.walk("VEVENT"):
        try:
            termine += termine_eines_eintrags(teil, kennung, name, farbe, von, bis)
        except Exception:
            # Ein kaputter Eintrag soll nicht die ganze Liste kippen.
            continue
    return termine
