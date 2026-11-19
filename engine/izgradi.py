"""Build a quiz: sablon.html + kviz.toml + bank + pictures -> one offline HTML file.

Usage: python izgradi.py <quiz-folder> [--config PATH] [--out PATH]
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

from ucitaj import KvizGreska, ucitaj_kviz  # noqa: E402

SABLON = ENGINE / "sablon.html"
PLACEHOLDERI = ("TITLE", "NASLOV", "PODNASLOV", "UVOD", "SIM_OPIS", "OBLASTI", "PODESAVANJA", "BANKA", "SLIKE", "LANG")

# Words Python writes into the HTML; every other UI string is in the T table inside sablon.html.
UI = {
    "lat": {"lang": "sr-Latn", "sve": "Sve", "nasumicnih": ("nasumično", "nasumična", "nasumičnih"),
            "pitanja": ("pitanje", "pitanja", "pitanja"), "prolaz": "prolaz", "rezultat": "rezultat na kraju"},
    "cyr": {"lang": "sr-Cyrl", "sve": "Све", "nasumicnih": ("насумично", "насумична", "насумичних"),
            "pitanja": ("питање", "питања", "питања"), "prolaz": "пролаз", "rezultat": "резултат на крају"},
}


def _oblik(n: int, oblici: tuple[str, str, str]) -> str:
    """Serbian plural: 1, 21 -> first; 2-4, 22-24 -> second; else third."""
    if n % 10 == 1 and n % 100 != 11:
        return oblici[0]
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return oblici[1]
    return oblici[2]


def sim_opis(cfg: dict) -> str:
    """The subtitle of the third mode, e.g. "30 nasumičnih pitanja, prolaz 15, rezultat na kraju"."""
    ui = UI[cfg.get("pismo", "lat")]
    sim = cfg["simulacija"]
    if sim.get("sastav"):
        sastav = sim["sastav"]
        n = sum(sastav.values())
        delovi = " + ".join(f"{sastav[g]} {cfg['oblasti'][g].lower()}" for g in cfg["oblasti"] if g in sastav)
        opis = f"{n} {_oblik(n, ui['pitanja'])}: {delovi}"
    else:
        n = sim["broj"]
        opis = f"{n} {_oblik(n, ui['nasumicnih'])} {_oblik(n, ui['pitanja'])}"
    if sim.get("prolaz"):
        opis += f", {ui['prolaz']} {sim['prolaz']}"
    return f"{opis}, {ui['rezultat']}"


def _json_u_skripti(obj, **kw) -> str:
    # Inside a <script> tag, "</script" closes the tag and "<!--<script" stops the real "</script>" from closing
    # it. Escaping every "<" (valid in JSON and in JS) rules out both.
    return json.dumps(obj, ensure_ascii=False, **kw).replace("<", "\\u003c")


def _oblasti_html(cfg: dict) -> str:
    e = html.escape
    redovi = ['        <button class="choice" style="grid-column:1/-1" type="button" data-shape="radio" data-val="all" '
              'aria-pressed="true"><span class="mark"></span><span class="ctext">'
              f'{UI[cfg["pismo"]]["sve"]} <span class="csub" id="cntAll"></span></span></button>']
    for g, naziv in cfg["oblasti"].items():
        redovi.append(f'        <button class="choice" type="button" data-shape="radio" data-val="{g}" '
                      'aria-pressed="false"><span class="mark"></span><span class="ctext">'
                      f'{e(naziv)} <span class="csub" id="cnt{g}"></span></span></button>')
    return "\n".join(redovi)


def _slike(banka: list[dict], folder: Path) -> dict[str, str]:
    slike = {}
    for p in banka:
        img = p.get("img")
        if img and img not in slike:
            put = folder / "slike" / f"{img}.jpg"
            if not put.exists():
                raise FileNotFoundError(f"missing picture slike/{img}.jpg (question {p['id']})")
            slike[img] = "data:image/jpeg;base64," + base64.b64encode(put.read_bytes()).decode("ascii")
    return slike


def izgradi_html(cfg: dict, banka: list[dict], folder: Path) -> str:
    """The finished page. folder is the quiz folder, whose slike/ holds the pictures."""
    sablon = SABLON.read_text(encoding="utf-8")
    for ime in PLACEHOLDERI:
        assert sablon.count(f"__{ime}__") == 1, f"sablon.html must contain __{ime}__ exactly once"
    sim = cfg["simulacija"]
    podesavanja = {"oblasti": cfg["oblasti"], "prolaz": sim.get("prolaz"), "broj": sim.get("broj"),
                   "sastav": sim.get("sastav"), "kljuc": cfg["kljuc_skladista"], "oznakaVan": cfg["oznaka_van"],
                   "pismo": cfg["pismo"]}
    vrednosti = {
        "TITLE": html.escape(cfg["title"]),
        "NASLOV": html.escape(cfg["naslov"]),
        "PODNASLOV": html.escape(cfg["podnaslov"]),
        "UVOD": html.escape(cfg["uvod"]),
        "SIM_OPIS": html.escape(sim_opis(cfg)),
        "OBLASTI": _oblasti_html(cfg),
        "PODESAVANJA": _json_u_skripti(podesavanja),
        "BANKA": _json_u_skripti(banka, indent=0),
        "SLIKE": _json_u_skripti(_slike(banka, Path(folder))),
        "LANG": UI[cfg["pismo"]]["lang"],
    }
    # One pass, so placeholder-like text inside the inserted values is never replaced again.
    return re.sub(r"__(" + "|".join(PLACEHOLDERI) + r")__", lambda m: vrednosti[m.group(1)], sablon)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Build a quiz HTML from a quiz folder.")
    ap.add_argument("folder", type=Path, help="quiz folder (with kviz.toml and banka.py)")
    ap.add_argument("--config", type=Path, help="kviz.toml to use instead of <folder>/kviz.toml")
    ap.add_argument("--out", type=Path, help="output file (default: <folder>/<izlaz from kviz.toml>)")
    a = ap.parse_args(argv)
    try:
        k = ucitaj_kviz(a.folder, a.config)
    except KvizGreska as e:
        print(f"GREŠKA {e}")
        return 1
    if k.greske_ucitavanja:
        for g in k.greske_ucitavanja:
            print(f"GREŠKA load: {g}")
        return 1
    try:
        out_html = izgradi_html(k.cfg, k.banka, k.folder)
    except FileNotFoundError as e:
        print(f"GREŠKA {e}")
        return 1
    izlaz = a.out or k.folder / k.cfg["izlaz"]
    izlaz.parent.mkdir(parents=True, exist_ok=True)
    izlaz.write_text(out_html, encoding="utf-8")
    slike = len({p["img"] for p in k.banka if p.get("img")})
    print(f"izgrađeno: {len(k.banka)} pitanja, {slike} slika, {izlaz.stat().st_size / 1e6:.1f} MB -> {izlaz}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
