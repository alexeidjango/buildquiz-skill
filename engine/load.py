"""Load a quiz folder: quiz.toml (validated), bank.py + bank_<area>.py, terms.py, items.py."""
import importlib
import re
import sys
import tomllib
import traceback
from dataclasses import dataclass
from pathlib import Path

from bank_api import normalize

ENGINE = Path(__file__).resolve().parent
LANG_DIR = ENGINE / "lang"
REQUIRED = ("title", "heading", "subtitle", "intro", "storage_key", "output", "citation")
LANGUAGE_TAG = re.compile(r"[a-z]{2,3}(-[A-Za-z0-9]{2,8})*")  # used with fullmatch; subtags as BCP 47 sizes them
QUIZ_MODULES = ("bank", "terms", "items")


def available_languages() -> list[str]:
    """Screen language codes: one engine/lang/<code>.json file each, sorted."""
    return sorted(p.stem for p in LANG_DIR.glob("*.json"))


class QuizError(Exception):
    """Invalid quiz.toml or an unloadable bank.py; the message names the field or file."""


@dataclass
class Quiz:
    folder: Path
    cfg: dict
    bank: list[dict]
    terms: dict[str, str]
    term_area: dict[str, str | None]
    items: dict[str, str | None] | None
    load_errors: list[str]


def _positive_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def validate_config(cfg: dict) -> dict:
    """Validate a parsed quiz.toml and fill in defaults. Raises QuizError naming the field."""
    for field in REQUIRED:
        if not isinstance(cfg.get(field), str) or not cfg[field].strip():
            raise QuizError(f"{field}: required non-empty string")
    if not cfg["output"].endswith(".html"):
        raise QuizError("output: must end with .html")
    try:
        re.compile(cfg["citation"])
    except re.error as e:
        raise QuizError(f"citation: invalid regex: {e}") from None
    language = cfg.setdefault("language", "en")
    if language not in available_languages():
        raise QuizError(f"language: {language!r} has no file in engine/lang/; available: "
                        f"{', '.join(available_languages())}")
    content = cfg.setdefault("content_language", language)
    if not isinstance(content, str) or not LANGUAGE_TAG.fullmatch(content):
        raise QuizError(f"content_language: {content!r} is not a language tag such as \"sr-Cyrl\" or \"en\"")
    if not isinstance(cfg.setdefault("cyrillic_only", False), bool):
        raise QuizError("cyrillic_only: must be true or false")
    for field in ("off_source_label", "artifact"):
        if field in cfg and not isinstance(cfg[field], str):
            raise QuizError(f"{field}: must be a string")
    cfg.setdefault("off_source_label", None)  # None: the tag comes from the screen language and switches with it
    cfg.setdefault("artifact", "")
    allowed = cfg.setdefault("latin_allowed", [])
    if not isinstance(allowed, list) or not all(isinstance(x, str) for x in allowed):
        raise QuizError("latin_allowed: must be a list of strings")

    areas = cfg.get("areas")
    if not isinstance(areas, dict) or not 2 <= len(areas) <= 7:
        raise QuizError("areas: 2 to 7 areas required")
    for letter, label in areas.items():
        if not re.fullmatch(r"[A-Z]", letter):
            raise QuizError(f"areas: key {letter!r} must be one uppercase letter A-Z")
        if not isinstance(label, str) or not label.strip():
            raise QuizError(f"areas: label for {letter} must be a non-empty string")

    sim = cfg.get("simulation")
    if not isinstance(sim, dict):
        raise QuizError("simulation: table required")
    if "pass_mark" in sim and not _positive_int(sim["pass_mark"]):
        raise QuizError("simulation.pass_mark: must be an integer >= 1")
    if ("count" in sim) == ("mix" in sim):
        raise QuizError("simulation: exactly one of count or mix is required")
    if "count" in sim and not _positive_int(sim["count"]):
        raise QuizError("simulation.count: must be an integer >= 1")
    if "mix" in sim:
        mix = sim["mix"]
        if not isinstance(mix, dict) or not mix:
            raise QuizError("simulation.mix: must be a table area -> count")
        for letter, n in mix.items():
            if letter not in areas:
                raise QuizError(f"simulation.mix: area {letter} is not in [areas]")
            if not _positive_int(n):
                raise QuizError(f"simulation.mix: count for {letter} must be an integer >= 1")
    return cfg


def _purge_modules():
    for name in list(sys.modules):
        if name in QUIZ_MODULES or (name.startswith("bank_") and name != "bank_api"):
            del sys.modules[name]


def _error(file: str, e: BaseException) -> str:
    return f"{file}: " + traceback.format_exception_only(type(e), e)[-1].strip()


def load_quiz(folder: Path, cfg_path: Path | None = None, areas: str | None = None) -> Quiz:
    """Load a quiz folder. With areas (e.g. "J"), only those areas' bank_<area>.py files are imported."""
    folder = Path(folder).resolve()
    cfg_path = Path(cfg_path) if cfg_path else folder / "quiz.toml"
    try:
        cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise QuizError(f"quiz.toml: not found at {cfg_path}") from None
    except tomllib.TOMLDecodeError as e:
        raise QuizError(f"quiz.toml: {e}") from None
    cfg = validate_config(cfg)
    if areas is not None:
        areas = areas.strip().upper()
        unknown = sorted(set(areas) - set(cfg["areas"]))
        if not areas or unknown:
            raise QuizError(f"area {areas!r}: give area letters from quiz.toml [areas] "
                            f"({''.join(cfg['areas'])})" + (f"; unknown: {''.join(unknown)}" if unknown else ""))
    letters = [g for g in cfg["areas"] if areas is None or g in areas]

    sys.dont_write_bytecode = True
    for p in (str(ENGINE), str(folder)):
        while p in sys.path:
            sys.path.remove(p)
    sys.path[:0] = [str(folder), str(ENGINE)]
    _purge_modules()
    importlib.invalidate_caches()
    try:
        try:
            bank_module = importlib.import_module("bank")
        except Exception as e:  # noqa: BLE001 - reported to the user
            raise QuizError(_error("bank.py", e)) from None
        questions = bank_module.BANK
        errors = []
        for g in letters:
            name = f"bank_{g.lower()}"
            if not (folder / f"{name}.py").exists() or name in sys.modules:
                continue  # missing, or already imported by bank.py itself
            before = len(questions)
            try:
                importlib.import_module(name)
            except Exception as e:  # noqa: BLE001 - one broken area file must not stop the others
                del questions[before:]
                errors.append(_error(f"{name}.py", e))
        bank = [normalize(p) for p in questions if p["area"] in letters]

        terms, term_area = {}, {}
        if (folder / "terms.py").exists():
            for key, v in importlib.import_module("terms").TERMS.items():
                if isinstance(v, dict):
                    for name, rx in v.items():
                        terms[name], term_area[name] = rx, key
                else:
                    terms[key], term_area[key] = v, None

        items = None
        if (folder / "items.py").exists():
            found = getattr(importlib.import_module("items"), "ITEMS", None)
            if isinstance(found, dict):
                items = dict(found)
            elif found is not None:
                items = {i: None for i in found}
    finally:
        _purge_modules()
        sys.path[:] = [p for p in sys.path if p != str(folder)]
    return Quiz(folder, cfg, bank, terms, term_area, items, errors)
