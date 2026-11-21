"""Build a quiz: template.html + quiz.toml + bank + pictures -> one offline HTML file.

Usage: python build.py <quiz-folder> [--config PATH] [--out PATH]
"""
import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

from load import QuizError, load_quiz  # noqa: E402

TEMPLATE = ENGINE / "template.html"
PLACEHOLDERS = ("TITLE", "HEADING", "SUBTITLE", "INTRO", "SIM_DESC", "AREAS", "CONFIG", "BANK", "IMAGES", "LANG")

# Words Python writes into the HTML; every other screen text is in the T table inside template.html.
UI = {
    "sr-Latn": {"all": "Sve", "random": ("nasumično", "nasumična", "nasumičnih"),
                "questions": ("pitanje", "pitanja", "pitanja"), "pass_mark": "prolaz", "score": "rezultat na kraju"},
    "sr-Cyrl": {"all": "Све", "random": ("насумично", "насумична", "насумичних"),
                "questions": ("питање", "питања", "питања"), "pass_mark": "пролаз", "score": "резултат на крају"},
}


def _form(n: int, forms: tuple[str, str, str]) -> str:
    """Serbian plural: 1, 21 -> first; 2-4, 22-24 -> second; else third."""
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return forms[1]
    return forms[2]


def sim_desc(cfg: dict) -> str:
    """The subtitle of the third mode, e.g. "30 nasumičnih pitanja, prolaz 15, rezultat na kraju"."""
    ui = UI[cfg["language"]]
    sim = cfg["simulation"]
    if sim.get("mix"):
        mix = sim["mix"]
        n = sum(mix.values())
        parts = " + ".join(f"{mix[g]} {cfg['areas'][g].lower()}" for g in cfg["areas"] if g in mix)
        desc = f"{n} {_form(n, ui['questions'])}: {parts}"
    else:
        n = sim["count"]
        desc = f"{n} {_form(n, ui['random'])} {_form(n, ui['questions'])}"
    if sim.get("pass_mark"):
        desc += f", {ui['pass_mark']} {sim['pass_mark']}"
    return f"{desc}, {ui['score']}"


def _json_in_script(obj, **kw) -> str:
    # Inside a <script> tag, "</script" closes the tag and "<!--<script" stops the real "</script>" from closing
    # it. Escaping every "<" (valid in JSON and in JS) rules out both.
    return json.dumps(obj, ensure_ascii=False, **kw).replace("<", "\\u003c")


def _areas_html(cfg: dict) -> str:
    e = html.escape
    rows = ['        <button class="choice" style="grid-column:1/-1" type="button" data-shape="radio" data-val="all" '
            'aria-pressed="true"><span class="mark"></span><span class="ctext">'
            f'{UI[cfg["language"]]["all"]} <span class="csub" id="cntAll"></span></span></button>']
    for g, label in cfg["areas"].items():
        rows.append(f'        <button class="choice" type="button" data-shape="radio" data-val="{g}" '
                    'aria-pressed="false"><span class="mark"></span><span class="ctext">'
                    f'{e(label)} <span class="csub" id="cnt{g}"></span></span></button>')
    return "\n".join(rows)


def _images(bank: list[dict], folder: Path) -> dict[str, str]:
    images = {}
    for p in bank:
        img = p.get("img")
        if img and img not in images:
            path = folder / "images" / f"{img}.jpg"
            if not path.exists():
                raise FileNotFoundError(f"missing picture images/{img}.jpg (question {p['id']})")
            images[img] = "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
    return images


def build_html(cfg: dict, bank: list[dict], folder: Path) -> str:
    """The finished page. folder is the quiz folder, whose images/ holds the pictures."""
    template = TEMPLATE.read_text(encoding="utf-8")
    for name in PLACEHOLDERS:
        assert template.count(f"__{name}__") == 1, f"template.html must contain __{name}__ exactly once"
    sim = cfg["simulation"]
    config = {"areas": cfg["areas"], "passMark": sim.get("pass_mark"), "count": sim.get("count"),
              "mix": sim.get("mix"), "storageKey": cfg["storage_key"], "offSourceLabel": cfg["off_source_label"],
              "language": cfg["language"]}
    values = {
        "TITLE": html.escape(cfg["title"]),
        "HEADING": html.escape(cfg["heading"]),
        "SUBTITLE": html.escape(cfg["subtitle"]),
        "INTRO": html.escape(cfg["intro"]),
        "SIM_DESC": html.escape(sim_desc(cfg)),
        "AREAS": _areas_html(cfg),
        "CONFIG": _json_in_script(config),
        "BANK": _json_in_script(bank, indent=0),
        "IMAGES": _json_in_script(_images(bank, Path(folder))),
        "LANG": cfg["language"],
    }
    # One pass, so placeholder-like text inside the inserted values is never replaced again.
    return re.sub(r"__(" + "|".join(PLACEHOLDERS) + r")__", lambda m: values[m.group(1)], template)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Build a quiz HTML from a quiz folder.")
    ap.add_argument("folder", type=Path, help="quiz folder (with quiz.toml and bank.py)")
    ap.add_argument("--config", type=Path, help="quiz.toml to use instead of <folder>/quiz.toml")
    ap.add_argument("--out", type=Path, help="output file (default: <folder>/<output from quiz.toml>)")
    a = ap.parse_args(argv)
    try:
        quiz = load_quiz(a.folder, a.config)
    except QuizError as e:
        print(f"ERROR {e}")
        return 1
    if quiz.load_errors:
        for e in quiz.load_errors:
            print(f"ERROR load: {e}")
        return 1
    try:
        page = build_html(quiz.cfg, quiz.bank, quiz.folder)
    except FileNotFoundError as e:
        print(f"ERROR {e}")
        return 1
    out = a.out or quiz.folder / quiz.cfg["output"]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    pictures = len({p["img"] for p in quiz.bank if p.get("img")})
    print(f"built: {len(quiz.bank)} questions, {pictures} images, {out.stat().st_size / 1e6:.1f} MB -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
