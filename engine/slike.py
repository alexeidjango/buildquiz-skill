"""Cut a figure out of a source page and cover its labels with numbers, for questions with pictures.

Coordinates are in the space of the page preview citaj.py makes (<source>/_tekst/_slike/<page>.jpg: the upright
page fitted into 1600x1600). The crop itself comes from the full-resolution original, so the output stays sharp.

Usage:
  python slike.py <quiz-folder> <id> <source-image> x0 y0 x1 y1 [--maska x0,y0,x1,y1,N]... [--broj x,y,N]... [--sirina 900]
  python slike.py <quiz-folder> --obnovi        rebuild every picture from the slike_*.json records

  <id>      ASCII, starts with the area letter: A_paramecijum (regex ^[A-Z]_[a-z0-9_]+$)
  --maska   white box over a printed label, with number N written in it (N may be empty: "x0,y0,x1,y1,")
  --broj    number N written centred at x,y (for the book's empty answer circles)

Writes <quiz-folder>/slike/<id>.jpg and records the call in <quiz-folder>/slike_<area letter>.json.
"""
import json
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

PREGLED_MAX = 1600  # the same fit as citaj.py's preview
FONT = r"C:\Windows\Fonts\arialbd.ttf"
BOJA = "#b3002d"
ID = re.compile(r"^[A-Z]_[a-z0-9_]+$")


def _font(velicina: int):
    try:
        return ImageFont.truetype(FONT, velicina)
    except OSError:
        return ImageFont.load_default(velicina)


def _sirina_pregleda(velicina: tuple[int, int]) -> int:
    """Width of citaj.py's preview of an upright image of this size (same thumbnail rounding)."""
    t = Image.new("L", velicina)
    t.thumbnail((PREGLED_MAX, PREGLED_MAX))
    return t.width


def napravi(kviz: Path, id_: str, izvor: Path, box: tuple[float, float, float, float],
            maske: list[tuple[float, float, float, float, str]] = (),
            brojevi: list[tuple[float, float, str]] = (), sirina: int = 900) -> Path:
    """Write <kviz>/slike/<id_>.jpg cut from izvor (any orientation; EXIF is applied). Returns its path."""
    with Image.open(izvor) as sirova:
        im = ImageOps.exif_transpose(sirova).convert("RGB")
    k = im.width / _sirina_pregleda(im.size)
    x0, y0, x1, y1 = box
    isecak = im.crop(tuple(round(v * k) for v in (x0, y0, x1, y1)))
    s = min(1.0, sirina / isecak.width)  # never upscale: it only blurs
    isecak = isecak.resize((round(isecak.width * s), round(isecak.height * s)), Image.LANCZOS)
    d = ImageDraw.Draw(isecak)

    def t(x, y):  # preview coords -> output coords
        return (x - x0) * k * s, (y - y0) * k * s

    for mx0, my0, mx1, my1, n in maske:
        a, b = t(mx0, my0)
        c, e = t(mx1, my1)
        d.rectangle((a, b, c, e), fill="white", outline="#999999", width=2)
        if n:
            vel = max(26, int(min(e - b, (c - a) / max(1, len(n)) * 1.4) * 0.8))
            d.text(((a + c) / 2, (b + e) / 2), n, fill=BOJA, font=_font(vel), anchor="mm")
    for bx, by, n in brojevi:
        d.text(t(bx, by), n, fill=BOJA, font=_font(28), anchor="mm")
    put = Path(kviz) / "slike" / f"{id_}.jpg"
    put.parent.mkdir(parents=True, exist_ok=True)
    isecak.save(put, quality=80, optimize=True)
    return put


def _brojevi(tekst: str, n: int, opcija: str) -> list:
    delovi = tekst.split(",")
    if len(delovi) != n:
        raise ValueError(f"{opcija} {tekst!r}: expected {n} comma-separated values")
    return [float(x) for x in delovi[:-1]] + [delovi[-1].strip()]


def _obnovi(kviz: Path) -> int:
    ukupno = 0
    for spisak in sorted(kviz.glob("slike_*.json")):
        for id_, z in json.loads(spisak.read_text(encoding="utf-8")).items():
            put = napravi(kviz, id_, kviz.parent / z["izvor"], tuple(z["box"]),
                          [tuple(m) for m in z["maske"]], [tuple(b) for b in z["brojevi"]], z["sirina"])
            print(put)
            ukupno += 1
    print(f"obnovljeno: {ukupno}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[1] == "--obnovi":
        return _obnovi(Path(argv[0]))
    if len(argv) < 7 or "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 2
    kviz, id_, izvor = Path(argv[0]), argv[1], Path(argv[2])
    if not ID.match(id_):
        print(f"GREŠKA id {id_!r}: must match {ID.pattern} (ASCII, area letter first, e.g. A_paramecijum)")
        return 1
    try:
        box = tuple(float(v) for v in argv[3:7])
        maske, brojevi, sirina = [], [], 900
        ostalo = argv[7:]
        while ostalo:
            opcija, vrednost, ostalo = ostalo[0], ostalo[1] if len(ostalo) > 1 else "", ostalo[2:]
            if opcija == "--maska":
                maske.append(tuple(_brojevi(vrednost, 5, opcija)))
            elif opcija == "--broj":
                brojevi.append(tuple(_brojevi(vrednost, 3, opcija)))
            elif opcija == "--sirina":
                sirina = int(vrednost)
            else:
                raise ValueError(f"unknown option {opcija!r}")
    except ValueError as e:
        print(f"GREŠKA {e}")
        return 1
    if not izvor.exists():
        print(f"GREŠKA source image not found: {izvor}")
        return 1
    put = napravi(kviz, id_, izvor, box, maske, brojevi, sirina)
    spisak_put = kviz / f"slike_{id_[0]}.json"
    spisak = json.loads(spisak_put.read_text(encoding="utf-8")) if spisak_put.exists() else {}
    spisak[id_] = {"izvor": Path(os.path.relpath(izvor.resolve(), kviz.resolve().parent)).as_posix(),
                   "box": list(box), "maske": [list(m) for m in maske], "brojevi": [list(b) for b in brojevi],
                   "sirina": sirina}
    spisak_put.write_text(json.dumps(spisak, ensure_ascii=False, indent=1), encoding="utf-8")
    with Image.open(put) as im:
        print(put, im.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
