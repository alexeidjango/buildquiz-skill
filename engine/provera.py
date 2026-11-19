"""Bank check: integrity, source citations, pictures, script, term and book-item coverage, simulation size.

Usage: python provera.py <quiz-folder> [--config PATH] [--oblast LETTERS]
Exit 0 only when there are no problems. --oblast checks only those areas (other areas' files are not imported).
"""
import argparse
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

from ucitaj import Kviz, KvizGreska, ucitaj_kviz  # noqa: E402

LATINICA = re.compile(r"[A-Za-zČčĆćŠšĐđŽž]+")


def _pitanje(p: dict, cfg: dict, izvor: re.Pattern, videno: set, slike: Path) -> list[str]:
    pid = p.get("id", "?")
    problemi = []
    opts = p.get("opts") or []
    tekstovi = [o.get("t", "") for o in opts]
    if not 3 <= len(opts) <= 7:
        problemi.append(f"{pid}: {len(opts)} options (3 to 7 allowed)")
    if len({t.strip().lower() for t in tekstovi}) != len(tekstovi):
        problemi.append(f"{pid}: two options have the same text")
    ok = p.get("ok") or []
    if not ok or any(not 0 <= i < len(opts) for i in ok) or len(set(ok)) >= len(opts):
        problemi.append(f"{pid}: correct options {ok} (need at least one correct and one wrong)")
    for o in opts:
        why = o.get("why", "")
        if not why.strip():
            problemi.append(f"{pid}: empty why for option {o.get('t', '')[:40]!r}")
        elif not p.get("van") and not izvor.search(why):
            problemi.append(f"{pid}: why without a source citation: {why[:60]!r}")
    kljuc = (p.get("q"), p.get("img"))
    if kljuc in videno:
        problemi.append(f"{pid}: repeated question (same text and picture): {p.get('q', '')[:60]!r}")
    videno.add(kljuc)
    if p.get("g") not in cfg["oblasti"]:
        problemi.append(f"{pid}: area {p.get('g')!r} is not in oblasti")
    if "code" in p and not isinstance(p["code"], str):
        problemi.append(f"{pid}: code must be a string")
    if p.get("img") and not (slike / f"{p['img']}.jpg").exists():
        problemi.append(f"{pid}: missing picture slike/{p['img']}.jpg")
    if cfg["pismo"] == "cyr":
        dozvoljeno = set(cfg.get("latinica_dozvoljena", []))
        polja = [p.get("q", ""), p.get("note", "")] + [s for o in opts for s in (o.get("t", ""), o.get("why", ""))]
        lat = sorted({t for s in polja for t in LATINICA.findall(s or "")} - dozvoljeno)
        if lat:
            problemi.append(f"{pid}: Latin letters in a Cyrillic quiz: {', '.join(lat)}")
    return problemi


def proveri(k: Kviz, oblasti: str | None = None) -> list[str]:
    """One problem per line; an empty list means pass. With oblasti, coverage is checked only for those areas."""
    cfg = k.cfg
    problemi = [f"load: {g}" for g in k.greske_ucitavanja]
    izvor = re.compile(cfg["izvor"])
    videno, ids = set(), set()
    for p in k.banka:
        if p.get("id") in ids:
            problemi.append(f"{p['id']}: duplicate id")
        ids.add(p.get("id"))
        problemi += _pitanje(p, cfg, izvor, videno, k.folder / "slike")

    def u_opsegu(oblast):
        return oblasti is None or (oblast is not None and oblast in oblasti)

    izvori = [p["q"] for p in k.banka] + [p["opts"][i]["t"] for p in k.banka for i in p["ok"]
                                          if 0 <= i < len(p["opts"])]
    for ime, rx in k.termini.items():
        if not u_opsegu(k.termini_oblast.get(ime)):
            continue
        try:
            r = re.compile(rx, re.IGNORECASE)
        except re.error:
            problemi.append(f"termini: {ime}: neispravan regex {rx!r}")
            continue
        if not any(r.search(s) for s in izvori):
            problemi.append(f"termini: {ime}: not covered by any question text or correct option")

    if k.kljuc is not None:
        upotrebljeno = {i for p in k.banka for i in p.get("kljuc", [])}
        for i, oblast in k.kljuc.items():
            if u_opsegu(oblast) and i not in upotrebljeno:
                problemi.append(f"kljuc: {i}: no question covers this book/key item")
        for p in k.banka:
            for i in p.get("kljuc", []):
                if i not in k.kljuc:
                    problemi.append(f"{p['id']}: unknown key id {i!r} (not in KLJUC)")

    if cfg["pismo"] == "cyr":
        dozvoljeno = set(cfg.get("latinica_dozvoljena", []))
        polja = {f: cfg[f] for f in ("title", "naslov", "podnaslov", "uvod", "oznaka_van")}
        polja.update({f"oblasti.{g}": naziv for g, naziv in cfg["oblasti"].items()})
        for polje, tekst in polja.items():
            lat = sorted(set(LATINICA.findall(tekst)) - dozvoljeno)
            if lat:
                problemi.append(f"config: {polje}: Latin letters in a Cyrillic quiz: {', '.join(lat)}")

    for g in cfg["oblasti"]:
        if u_opsegu(g) and not any(p["g"] == g for p in k.banka):
            problemi.append(f"config: area {g} ({cfg['oblasti'][g]}) has no questions")

    if oblasti is None:
        sim = cfg["simulacija"]
        velicina = sim["broj"] if "broj" in sim else sum(sim["sastav"].values())
        if sim.get("prolaz") and sim["prolaz"] > velicina:
            problemi.append(f"config: simulacija.prolaz = {sim['prolaz']} is more than the {velicina} questions "
                            "of a simulation, so it can never be passed")
        if "broj" in sim and sim["broj"] > len(k.banka):
            problemi.append(f"config: simulacija.broj = {sim['broj']} but the bank has {len(k.banka)} questions")
        for g, n in (sim.get("sastav") or {}).items():
            imamo = sum(p["g"] == g for p in k.banka)
            if n > imamo:
                problemi.append(f"config: simulacija.sastav.{g} = {n} but area {g} has {imamo} questions")
    return problemi


def sazetak(k: Kviz) -> str:
    po = {g: sum(p["g"] == g for p in k.banka) for g in k.cfg["oblasti"]}
    return (f"pitanja: {len(k.banka)} ({', '.join(f'{g}: {n}' for g, n in po.items())})"
            f" | multi: {sum(bool(p.get('multi')) for p in k.banka)}"
            f" | van: {sum(bool(p.get('van')) for p in k.banka)}"
            f" | slike: {sum(bool(p.get('img')) for p in k.banka)}"
            f" | termini: {len(k.termini)}"
            + (f" | kljuc: {len(k.kljuc)}" if k.kljuc is not None else ""))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Check a quiz bank. Exit 0 = no problems.")
    ap.add_argument("folder", type=Path, help="quiz folder (with kviz.toml and banka.py)")
    ap.add_argument("--config", type=Path, help="kviz.toml to use instead of <folder>/kviz.toml")
    ap.add_argument("--oblast", help="area letters to check, e.g. J or VR (other area files are not imported)")
    a = ap.parse_args(argv)
    try:
        k = ucitaj_kviz(a.folder, a.config, a.oblast)
    except KvizGreska as e:
        print(f"GREŠKA {e}")
        return 1
    problemi = proveri(k, a.oblast.strip().upper() if a.oblast is not None else None)
    print(sazetak(k))
    for p in problemi:
        print(f"GREŠKA {p}")
    print("OK" if not problemi else f"{len(problemi)} problem(s)")
    return 1 if problemi else 0


if __name__ == "__main__":
    sys.exit(main())
