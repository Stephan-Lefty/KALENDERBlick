#!/usr/bin/env python3
"""Baut das kalenderblick-Icon im Haus-Stil (wie HANDYHelfer): Blauverlauf
senkrecht von BLAU_HELL nach BLAU_TIEF, die bestehende Kalender+Monitor-
Zeichnung weiß darüber, der Namenszug unten zweifarbig passend zur
Groß-/Kleinschreibung der App - KALENDER weiß, Blick hellblau.

Zwei Fassungen, weil der Namenszug bei 16-32 Pixel (Kontrollleiste) nicht
mehr lesbar ist: icon.png mit Namenszug für 48 Pixel aufwärts,
icon-klein.png ohne für 16-32 Pixel - dort füllt die Zeichnung dafür mehr
von der Fläche. packaging/symbole-erzeugen.py wählt pro Zielgröße die
passende Datei.

Die Zeichnung wird nicht neu gemalt, sondern aus der alten, flachen
Fassung (assets/icon-alt.png) als reine Linienmaske herausgerechnet -
genau wie bei Denkzettel aus der DialOS-Vorlage.

Braucht Pillow, numpy und scipy:
    pamac install python-pillow python-numpy python-scipy

Aufruf:
    python3 assets/icon-bauen.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage

ASSETS = Path(__file__).resolve().parent
VORLAGE = ASSETS / "icon-alt.png"

S = 4                 # Supersampling gegen Treppenkanten
N = 1024 * S          # Arbeitsgröße

# Aus assets/farben.md - Verlauf oben nach unten über die volle Höhe
BLAU_HELL = (14, 138, 246)
BLAU_TIEF = (0, 71, 167)
WEISS = (255, 255, 255)
BLAU_LEUCHT = (108, 182, 255)

ECKRADIUS_ANTEIL = 0.225   # an der Vorlage abgemessen


def _schriftart(groesse: int) -> ImageFont.FreeTypeFont:
    for pfad in (
        "/usr/share/fonts/noto/NotoSans-Bold.ttf",
        "/usr/share/fonts/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(pfad).exists():
            return ImageFont.truetype(pfad, groesse)
    return ImageFont.load_default()


def _linienmaske(vorlage: Image.Image, n: int) -> Image.Image:
    """Weiß auf durchsichtig, egal was vorher Hintergrund war.

    Die alte Fassung trägt an allen vier runden Ecken einen hauchdünnen,
    1 Pixel breiten Geisterbogen - ein Artefakt ihrer eigenen Entstehung,
    unabhängig von jeder Skalierung hier. Zusammenhängende Flächen mit
    einem Füllgrad unter 10% sind so ein Bogen, keine echte Zeichnung -
    die Kalender- und Monitorformen liegen alle deutlich darüber.
    """
    vorlage = vorlage.convert("RGBA")
    daten = np.asarray(vorlage)
    hell = (daten[..., 0] > 200) & (daten[..., 1] > 200) & (daten[..., 2] > 200) & (daten[..., 3] > 200)

    beschriftet, anzahl = ndimage.label(hell)
    bereinigt = np.zeros_like(hell)
    for i in range(1, anzahl + 1):
        masse = beschriftet == i
        pixel = masse.sum()
        if pixel < 50:
            continue
        ys, xs = np.where(masse)
        breite = xs.max() - xs.min() + 1
        hoehe = ys.max() - ys.min() + 1
        if breite < 5 or hoehe < 5:
            continue   # Haarlinie - bei 1 Pixel Höhe wäre der Füllgrad immer 100%
        if pixel / (breite * hoehe) > 0.1:
            bereinigt |= masse

    alpha = np.where(bereinigt, 255, 0).astype(np.uint8)
    alpha_bild = Image.fromarray(alpha, mode="L").filter(ImageFilter.GaussianBlur(radius=1.2))
    weiss = Image.new("RGBA", vorlage.size, WEISS + (0,))
    weiss.putalpha(alpha_bild)
    return weiss.resize((n, n), Image.LANCZOS)


def _verlaufsgrund(n: int, eckradius: int) -> Image.Image:
    grund = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    verlauf = Image.new("RGB", (1, n))
    for y in range(n):
        t = y / (n - 1)
        zeile = tuple(round(BLAU_HELL[k] + (BLAU_TIEF[k] - BLAU_HELL[k]) * t) for k in range(3))
        verlauf.putpixel((0, y), zeile)
    verlauf = verlauf.resize((n, n))
    maske = Image.new("L", (n, n), 0)
    ImageDraw.Draw(maske).rounded_rectangle((0, 0, n - 1, n - 1), radius=eckradius, fill=255)
    grund.paste(verlauf, (0, 0), maske)
    return grund


def _komposition(linien_quelle: Image.Image, mit_text: bool) -> Image.Image:
    eckradius = round(N * ECKRADIUS_ANTEIL)
    grund = _verlaufsgrund(N, eckradius)

    linien = linien_quelle
    if mit_text:
        # Zeichnung verkleinern und nach oben schieben - unten wird Platz
        # für den Namenszug gebraucht.
        zeichnung_hoehe = round(N * 0.62)
        ziel_y = round(N * 0.06)
    else:
        # Ohne Text darf die Zeichnung die Fläche besser ausnutzen - bei
        # 16-32 Pixel (Kontrollleiste) zählt jedes Pixel für die Lesbarkeit.
        zeichnung_hoehe = round(N * 0.8)
        ziel_y = round(N * 0.1)
    linien = linien.resize((zeichnung_hoehe, zeichnung_hoehe), Image.LANCZOS)
    ziel_x = (N - zeichnung_hoehe) // 2
    grund.alpha_composite(linien, (ziel_x, ziel_y))

    if mit_text:
        # Namenszug: KALENDER weiß, Blick hellblau, eine Zeile, zentriert -
        # Schriftgröße so lange verkleinert, bis beide Teile zusammen in
        # die Zielbreite passen.
        zeichner = ImageDraw.Draw(grund)
        teil_a, teil_b = "KALENDER", "Blick"
        ziel_breite = N * 0.86
        schriftgroesse = round(N * 0.16)
        while schriftgroesse > 10:
            schrift = _schriftart(schriftgroesse)
            breite_a = zeichner.textlength(teil_a, font=schrift)
            breite_b = zeichner.textlength(teil_b, font=schrift)
            if breite_a + breite_b <= ziel_breite:
                break
            schriftgroesse -= round(N * 0.002)
        gesamt_breite = breite_a + breite_b
        start_x = (N - gesamt_breite) / 2
        text_y = round(N * 0.76)
        zeichner.text((start_x, text_y), teil_a, font=schrift, fill=WEISS)
        zeichner.text((start_x + breite_a, text_y), teil_b, font=schrift, fill=BLAU_LEUCHT)

    return grund.resize((1024, 1024), Image.LANCZOS)


def main() -> int:
    if not VORLAGE.exists():
        print(f"Vorlage fehlt: {VORLAGE}")
        return 1

    linien = _linienmaske(Image.open(VORLAGE), N)

    gross = _komposition(linien, mit_text=True)
    ziel_gross = ASSETS / "icon.png"
    gross.save(ziel_gross)
    print(f"geschrieben: {ziel_gross}  (48 Pixel aufwärts, mit Namenszug)")

    klein = _komposition(linien, mit_text=False)
    ziel_klein = ASSETS / "icon-klein.png"
    klein.save(ziel_klein)
    print(f"geschrieben: {ziel_klein}  (16-32 Pixel, ohne Namenszug)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
