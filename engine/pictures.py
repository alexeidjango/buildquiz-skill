"""Cut a figure out of a source page and cover its labels with numbers, for questions with pictures.

Coordinates are in the space of the page preview read_sources.py makes (<sources>/_text/_pages/<page>.jpg: the
upright page fitted into 1600x1600). The crop itself comes from the full-resolution original, so the output stays
sharp.

Usage:
  python pictures.py <quiz-folder> <id> <source-image> x0 y0 x1 y1 [--mask x0,y0,x1,y1,N]... [--number x,y,N]... [--width 900]
  python pictures.py <quiz-folder> --rebuild     rebuild every picture from the images_*.json records

  <id>      ASCII, starts with the area letter: A_paramecium (regex ^[A-Z]_[a-z0-9_]+$)
  --mask    white box over a printed label, with number N written in it (N may be empty: "x0,y0,x1,y1,")
  --number  number N written centred at x,y (for the book's empty answer circles)

Writes <quiz-folder>/images/<id>.jpg and records the call in <quiz-folder>/images_<area letter>.json.
"""
import json
import os
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

PREVIEW_MAX = 1600  # the same fit as read_sources.py's preview
FONT = r"C:\Windows\Fonts\arialbd.ttf"
COLOR = "#b3002d"
ID = re.compile(r"^[A-Z]_[a-z0-9_]+$")


def _font(size: int):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default(size)


def _preview_width(size: tuple[int, int]) -> int:
    """Width of read_sources.py's preview of an upright image of this size (same thumbnail rounding)."""
    t = Image.new("L", size)
    t.thumbnail((PREVIEW_MAX, PREVIEW_MAX))
    return t.width


def make(quiz: Path, id_: str, source: Path, box: tuple[float, float, float, float],
         masks: list[tuple[float, float, float, float, str]] = (),
         numbers: list[tuple[float, float, str]] = (), width: int = 900) -> Path:
    """Write <quiz>/images/<id_>.jpg cut from source (any orientation; EXIF is applied). Returns its path."""
    with Image.open(source) as raw:
        im = ImageOps.exif_transpose(raw).convert("RGB")
    k = im.width / _preview_width(im.size)
    x0, y0, x1, y1 = box
    crop = im.crop(tuple(round(v * k) for v in (x0, y0, x1, y1)))
    s = min(1.0, width / crop.width)  # never upscale: it only blurs
    crop = crop.resize((round(crop.width * s), round(crop.height * s)), Image.LANCZOS)
    d = ImageDraw.Draw(crop)

    def t(x, y):  # preview coords -> output coords
        return (x - x0) * k * s, (y - y0) * k * s

    for mx0, my0, mx1, my1, n in masks:
        a, b = t(mx0, my0)
        c, e = t(mx1, my1)
        d.rectangle((a, b, c, e), fill="white", outline="#999999", width=2)
        if n:
            size = max(26, int(min(e - b, (c - a) / max(1, len(n)) * 1.4) * 0.8))
            d.text(((a + c) / 2, (b + e) / 2), n, fill=COLOR, font=_font(size), anchor="mm")
    for bx, by, n in numbers:
        d.text(t(bx, by), n, fill=COLOR, font=_font(28), anchor="mm")
    path = Path(quiz) / "images" / f"{id_}.jpg"
    path.parent.mkdir(parents=True, exist_ok=True)
    crop.save(path, quality=80, optimize=True)
    return path


def _values(text: str, n: int, option: str) -> list:
    parts = text.split(",")
    if len(parts) != n:
        raise ValueError(f"{option} {text!r}: expected {n} comma-separated values")
    return [float(x) for x in parts[:-1]] + [parts[-1].strip()]


def _rebuild(quiz: Path) -> int:
    total = 0
    for records in sorted(quiz.glob("images_*.json")):
        for id_, r in json.loads(records.read_text(encoding="utf-8")).items():
            path = make(quiz, id_, quiz.parent / r["source"], tuple(r["box"]),
                        [tuple(m) for m in r["masks"]], [tuple(b) for b in r["numbers"]], r["width"])
            print(path)
            total += 1
    print(f"rebuilt: {total}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[1] == "--rebuild":
        return _rebuild(Path(argv[0]))
    if len(argv) < 7 or "-h" in argv or "--help" in argv:
        print(__doc__.strip())
        return 2
    quiz, id_, source = Path(argv[0]), argv[1], Path(argv[2])
    if not ID.match(id_):
        print(f"ERROR id {id_!r}: must match {ID.pattern} (ASCII, area letter first, e.g. A_paramecium)")
        return 1
    try:
        box = tuple(float(v) for v in argv[3:7])
        masks, numbers, width = [], [], 900
        rest = argv[7:]
        while rest:
            option, value, rest = rest[0], rest[1] if len(rest) > 1 else "", rest[2:]
            if option == "--mask":
                masks.append(tuple(_values(value, 5, option)))
            elif option == "--number":
                numbers.append(tuple(_values(value, 3, option)))
            elif option == "--width":
                width = int(value)
            else:
                raise ValueError(f"unknown option {option!r}")
    except ValueError as e:
        print(f"ERROR {e}")
        return 1
    if not source.exists():
        print(f"ERROR source image not found: {source}")
        return 1
    path = make(quiz, id_, source, box, masks, numbers, width)
    records_path = quiz / f"images_{id_[0]}.json"
    records = json.loads(records_path.read_text(encoding="utf-8")) if records_path.exists() else {}
    records[id_] = {"source": Path(os.path.relpath(source.resolve(), quiz.resolve().parent)).as_posix(),
                    "box": list(box), "masks": [list(m) for m in masks], "numbers": [list(b) for b in numbers],
                    "width": width}
    records_path.write_text(json.dumps(records, ensure_ascii=False, indent=1), encoding="utf-8")
    with Image.open(path) as im:
        print(path, im.size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
