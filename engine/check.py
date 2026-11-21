"""Bank check: integrity, source citations, pictures, script, term and book-item coverage, simulation size.

Usage: python check.py <quiz-folder> [--config PATH] [--area LETTERS]
Exit 0 only when there are no problems. --area checks only those areas (other areas' files are not imported).
"""
import argparse
import re
import sys
from pathlib import Path

ENGINE = Path(__file__).resolve().parent
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

from load import Quiz, QuizError, load_quiz  # noqa: E402

LATIN = re.compile(r"[A-Za-zČčĆćŠšĐđŽž]+")


def _question(p: dict, cfg: dict, citation: re.Pattern, seen: set, images: Path) -> list[str]:
    pid = p.get("id", "?")
    problems = []
    opts = p.get("opts") or []
    texts = [o.get("t", "") for o in opts]
    if not 3 <= len(opts) <= 7:
        problems.append(f"{pid}: {len(opts)} options (3 to 7 allowed)")
    if len({t.strip().lower() for t in texts}) != len(texts):
        problems.append(f"{pid}: two options have the same text")
    ok = p.get("ok") or []
    if not ok or any(not 0 <= i < len(opts) for i in ok) or len(set(ok)) >= len(opts):
        problems.append(f"{pid}: correct options {ok} (need at least one correct and one wrong)")
    for o in opts:
        why = o.get("why", "")
        if not why.strip():
            problems.append(f"{pid}: empty why for option {o.get('t', '')[:40]!r}")
        elif not p.get("off_source") and not citation.search(why):
            problems.append(f"{pid}: why without a source citation: {why[:60]!r}")
    key = (p.get("q"), p.get("img"))
    if key in seen:
        problems.append(f"{pid}: repeated question (same text and picture): {p.get('q', '')[:60]!r}")
    seen.add(key)
    if p.get("area") not in cfg["areas"]:
        problems.append(f"{pid}: area {p.get('area')!r} is not in [areas]")
    if "code" in p and not isinstance(p["code"], str):
        problems.append(f"{pid}: code must be a string")
    if p.get("img") and not (images / f"{p['img']}.jpg").exists():
        problems.append(f"{pid}: missing picture images/{p['img']}.jpg")
    if cfg["cyrillic_only"]:
        allowed = set(cfg.get("latin_allowed", []))
        fields = [p.get("q", ""), p.get("note", "")] + [s for o in opts for s in (o.get("t", ""), o.get("why", ""))]
        lat = sorted({t for s in fields for t in LATIN.findall(s or "")} - allowed)
        if lat:
            problems.append(f"{pid}: Latin letters in a Cyrillic quiz: {', '.join(lat)}")
    return problems


def check(quiz: Quiz, areas: str | None = None) -> list[str]:
    """One problem per line; an empty list means pass. With areas, coverage is checked only for those areas."""
    cfg = quiz.cfg
    problems = [f"load: {e}" for e in quiz.load_errors]
    citation = re.compile(cfg["citation"])
    seen, ids = set(), set()
    for p in quiz.bank:
        if p.get("id") in ids:
            problems.append(f"{p['id']}: duplicate id")
        ids.add(p.get("id"))
        problems += _question(p, cfg, citation, seen, quiz.folder / "images")

    def in_scope(area):
        return areas is None or (area is not None and area in areas)

    texts = [p["q"] for p in quiz.bank] + [p["opts"][i]["t"] for p in quiz.bank for i in p["ok"]
                                           if 0 <= i < len(p["opts"])]
    for name, rx in quiz.terms.items():
        if not in_scope(quiz.term_area.get(name)):
            continue
        try:
            r = re.compile(rx, re.IGNORECASE)
        except re.error:
            problems.append(f"terms: {name}: invalid regex {rx!r}")
            continue
        if not any(r.search(s) for s in texts):
            problems.append(f"terms: {name}: not covered by any question text or correct option")

    if quiz.items is not None:
        used = {i for p in quiz.bank for i in p.get("items", [])}
        for i, area in quiz.items.items():
            if in_scope(area) and i not in used:
                problems.append(f"items: {i}: no question covers this book/key item")
        for p in quiz.bank:
            for i in p.get("items", []):
                if i not in quiz.items:
                    problems.append(f"{p['id']}: unknown item id {i!r} (not in ITEMS)")

    if cfg["cyrillic_only"]:
        allowed = set(cfg.get("latin_allowed", []))
        fields = {f: cfg[f] for f in ("title", "heading", "subtitle", "intro", "off_source_label")}
        fields.update({f"areas.{g}": label for g, label in cfg["areas"].items()})
        for field, text in fields.items():
            lat = sorted(set(LATIN.findall(text or "")) - allowed)
            if lat:
                problems.append(f"config: {field}: Latin letters in a Cyrillic quiz: {', '.join(lat)}")

    for g in cfg["areas"]:
        if in_scope(g) and not any(p["area"] == g for p in quiz.bank):
            problems.append(f"config: area {g} ({cfg['areas'][g]}) has no questions")

    if areas is None:
        sim = cfg["simulation"]
        size = sim["count"] if "count" in sim else sum(sim["mix"].values())
        if sim.get("pass_mark") and sim["pass_mark"] > size:
            problems.append(f"config: simulation.pass_mark = {sim['pass_mark']} is more than the {size} questions "
                            "of a simulation, so it can never be passed")
        if "count" in sim and sim["count"] > len(quiz.bank):
            problems.append(f"config: simulation.count = {sim['count']} but the bank has {len(quiz.bank)} questions")
        for g, n in (sim.get("mix") or {}).items():
            have = sum(p["area"] == g for p in quiz.bank)
            if n > have:
                problems.append(f"config: simulation.mix.{g} = {n} but area {g} has {have} questions")
    return problems


def summary(quiz: Quiz) -> str:
    per = {g: sum(p["area"] == g for p in quiz.bank) for g in quiz.cfg["areas"]}
    return (f"questions: {len(quiz.bank)} ({', '.join(f'{g}: {n}' for g, n in per.items())})"
            f" | multi: {sum(bool(p.get('multi')) for p in quiz.bank)}"
            f" | off_source: {sum(bool(p.get('off_source')) for p in quiz.bank)}"
            f" | pictures: {sum(bool(p.get('img')) for p in quiz.bank)}"
            f" | terms: {len(quiz.terms)}"
            + (f" | items: {len(quiz.items)}" if quiz.items is not None else ""))


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Check a quiz bank. Exit 0 = no problems.")
    ap.add_argument("folder", type=Path, help="quiz folder (with quiz.toml and bank.py)")
    ap.add_argument("--config", type=Path, help="quiz.toml to use instead of <folder>/quiz.toml")
    ap.add_argument("--area", help="area letters to check, e.g. J or VR (other area files are not imported)")
    a = ap.parse_args(argv)
    try:
        quiz = load_quiz(a.folder, a.config, a.area)
    except QuizError as e:
        print(f"ERROR {e}")
        return 1
    problems = check(quiz, a.area.strip().upper() if a.area is not None else None)
    print(summary(quiz))
    for p in problems:
        print(f"ERROR {p}")
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
