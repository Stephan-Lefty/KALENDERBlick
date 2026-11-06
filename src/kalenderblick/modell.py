"""Was ein Termin ist und wie man ihn darstellt."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
# Für schmale Fenster. Zwei Buchstaben sind im Deutschen eindeutig -
# anders als bei einem, wo Montag, Mittwoch und Donnerstag, Dienstag
# zusammenfielen.
WOCHENTAGE_KURZ = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni",
          "Juli", "August", "September", "Oktober", "November", "Dezember"]


@dataclass
class Termin:
    titel: str
    beginn: datetime
    ende: datetime
    ganztags: bool = False
    ort: str = ""
    kalender_id: str = ""
    kalender_name: str = ""
    farbe: str = "#3584e4"
    kennung: str = ""

    # ------------------------------------------------------------------

    @property
    def tag(self) -> date:
        return self.beginn.date()

    @property
    def dauer(self) -> timedelta:
        return self.ende - self.beginn

    def zeitangabe(self) -> str:
        if self.ganztags:
            return "ganztägig"
        if self.beginn.date() != self.ende.date():
            return self.beginn.strftime("%H:%M") + " – " + self.ende.strftime("%d.%m. %H:%M")
        if self.beginn == self.ende:
            return self.beginn.strftime("%H:%M")
        return self.beginn.strftime("%H:%M") + " – " + self.ende.strftime("%H:%M")

    def laeuft_gerade(self, jetzt: datetime | None = None) -> bool:
        jetzt = jetzt or datetime.now()
        if self.ganztags:
            return self.beginn.date() <= jetzt.date() <= self.ende.date()
        return self.beginn <= jetzt < self.ende

    def ist_vorbei(self, jetzt: datetime | None = None) -> bool:
        jetzt = jetzt or datetime.now()
        if self.ganztags:
            return self.ende.date() < jetzt.date()
        return self.ende <= jetzt


def tagesueberschrift(tag: date, heute: date | None = None,
                      kurz: bool = False) -> str:
    """Die Überschrift über einem Tagesblock.

    **Immer mit Datum**, und ohne Jahr - das steht ohnehin fest.
    „Mittwoch" allein beantwortet nicht, der wievielte das ist; wer
    einen Termin eintragen oder absagen will, braucht die Zahl. Bis
    November 2026 stand bei den Tagen der laufenden Woche nur der
    Wochentag, bei ferneren das volle Datum - zwei Formen
    nebeneinander, von denen die eine zu wenig sagte.

    Mit `kurz` wird aus „Mittwoch, 5. November" ein „Mi, 5.11." Das
    ist für schmale Fenster: Ausgeschrieben passt die längste
    Überschrift ab 14 pt nicht mehr in das kleinste Widget (220 px).
    """
    heute = heute or date.today()
    abstand = (tag - heute).days
    datum = (f"{tag.day}.{tag.month}." if kurz
             else f"{tag.day}. {MONATE[tag.month - 1]}")

    if abstand == 0:
        name = "Heute"
    elif abstand == 1:
        name = "Morgen"
    elif abstand == -1:
        name = "Gestern"
    else:
        name = (WOCHENTAGE_KURZ if kurz else WOCHENTAGE)[tag.weekday()]
    return f"{name}, {datum}"


def nach_tagen(termine: list[Termin]) -> list[tuple[date, list[Termin]]]:
    """Termine nach Tagen bündeln, ganztägige zuerst."""
    gebuendelt: dict[date, list[Termin]] = {}
    for termin in termine:
        gebuendelt.setdefault(termin.tag, []).append(termin)
    ergebnis = []
    for tag in sorted(gebuendelt):
        eintraege = sorted(gebuendelt[tag], key=lambda t: (not t.ganztags, t.beginn))
        ergebnis.append((tag, eintraege))
    return ergebnis


def naechster(termine: list[Termin], jetzt: datetime | None = None) -> Termin | None:
    """Der Termin, der gerade läuft oder als nächster ansteht."""
    jetzt = jetzt or datetime.now()
    laufend = [t for t in termine if t.laeuft_gerade(jetzt) and not t.ganztags]
    if laufend:
        return min(laufend, key=lambda t: t.ende)
    kommend = [t for t in termine if not t.ist_vorbei(jetzt)]
    if not kommend:
        return None
    return min(kommend, key=lambda t: (t.beginn, t.ganztags))


def kurzfassung(termin: Termin | None, jetzt: datetime | None = None) -> str:
    """Eine Zeile für den Mauszeiger-Hinweis."""
    if termin is None:
        return "Keine Termine in Sicht"
    jetzt = jetzt or datetime.now()
    if termin.ganztags:
        return f"{tagesueberschrift(termin.tag, jetzt.date())}: {termin.titel}"
    if termin.laeuft_gerade(jetzt):
        rest = int((termin.ende - jetzt).total_seconds() // 60)
        return f"Läuft noch {rest} min: {termin.titel}"
    abstand = termin.beginn - jetzt
    minuten = int(abstand.total_seconds() // 60)
    if minuten < 60:
        return f"In {minuten} min: {termin.titel}"
    if termin.tag == jetzt.date():
        return f"Heute {termin.beginn.strftime('%H:%M')}: {termin.titel}"
    return (f"{tagesueberschrift(termin.tag, jetzt.date())} "
            f"{termin.beginn.strftime('%H:%M')}: {termin.titel}")


# Länger geschnittene Titel sprengen in der kleinsten Uhr (220 px) die
# zwei Zeilen, die dort unter dem Datum Platz haben - und eine
# wachsende Zeile schiebt die Uhrzeit aus der Mitte.
UHR_TITEL_ZEICHEN = 30


def uhr_zeile(termin: Termin | None, jetzt: datetime | None = None,
              zeichen: int = UHR_TITEL_ZEICHEN) -> str:
    """Der nächste Termin als eine knappe Zeile unter der Uhr.

    Knapper als [`kurzfassung`], und das ist der Unterschied: Der
    Mauszeiger-Hinweis darf ausführlich sein, weil er über allem
    schwebt. Hier steht die Zeile *in* der Uhr und muss sich dem
    Platz fügen.

    Deshalb keine Minutenangaben („In 12 min") - die wären eine Zeile
    weiter unten eine zweite Uhr neben der Uhr. Was zählt, ist der
    Zeitpunkt; wie lange es noch dauert, rechnet man sich daneben
    selbst aus.
    """
    if termin is None:
        return "Keine Termine"
    jetzt = jetzt or datetime.now()
    titel = termin.titel.strip() or "(ohne Titel)"
    if len(titel) > zeichen:
        titel = titel[:zeichen - 1].rstrip() + "…"
    if termin.ganztags:
        wann = ("Heute" if termin.tag == jetzt.date()
                else tagesueberschrift(termin.tag, jetzt.date(), kurz=True))
        return f"{wann}: {titel}"
    if termin.laeuft_gerade(jetzt):
        return f"Jetzt: {titel}"
    uhrzeit = termin.beginn.strftime("%H:%M")
    if termin.tag == jetzt.date():
        return f"{uhrzeit} {titel}"
    return f"{tagesueberschrift(termin.tag, jetzt.date(), kurz=True)} {uhrzeit} {titel}"
