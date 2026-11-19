"""Load a quiz folder: kviz.toml (validated), banka.py + banka_<area>.py, termini.py, kljuc.py."""
import importlib
import re
import sys
import tomllib
import traceback
from dataclasses import dataclass
from pathlib import Path

from banka_api import normalize

ENGINE = Path(__file__).resolve().parent
OBAVEZNO = ("title", "naslov", "podnaslov", "uvod", "kljuc_skladista", "izlaz", "izvor")
OZNAKA_VAN = {"lat": "van slajdova", "cyr": "ван ових страна"}


class KvizGreska(Exception):
    """Invalid kviz.toml or an unloadable banka.py; the message names the field or file."""


@dataclass
class Kviz:
    folder: Path
    cfg: dict
    banka: list[dict]
    termini: dict[str, str]
    termini_oblast: dict[str, str | None]
    kljuc: dict[str, str | None] | None
    greske_ucitavanja: list[str]


def _ceo_broj(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool) and v >= 1


def proveri_cfg(cfg: dict) -> dict:
    """Validate a parsed kviz.toml and fill in defaults. Raises KvizGreska naming the field."""
    for polje in OBAVEZNO:
        if not isinstance(cfg.get(polje), str) or not cfg[polje].strip():
            raise KvizGreska(f"{polje}: required non-empty string")
    if not cfg["izlaz"].endswith(".html"):
        raise KvizGreska("izlaz: must end with .html")
    try:
        re.compile(cfg["izvor"])
    except re.error as e:
        raise KvizGreska(f"izvor: invalid regex: {e}") from None
    pismo = cfg.setdefault("pismo", "lat")
    if pismo not in OZNAKA_VAN:
        raise KvizGreska('pismo: must be "lat" or "cyr"')
    for polje in ("oznaka_van", "artifact"):
        if polje in cfg and not isinstance(cfg[polje], str):
            raise KvizGreska(f"{polje}: must be a string")
    cfg.setdefault("oznaka_van", OZNAKA_VAN[pismo])
    cfg.setdefault("artifact", "")
    lat = cfg.setdefault("latinica_dozvoljena", [])
    if not isinstance(lat, list) or not all(isinstance(x, str) for x in lat):
        raise KvizGreska("latinica_dozvoljena: must be a list of strings")

    oblasti = cfg.get("oblasti")
    if not isinstance(oblasti, dict) or not 2 <= len(oblasti) <= 7:
        raise KvizGreska("oblasti: 2 to 7 areas required")
    for slovo, naziv in oblasti.items():
        if not re.fullmatch(r"[A-Z]", slovo):
            raise KvizGreska(f"oblasti: key {slovo!r} must be one uppercase letter A-Z")
        if not isinstance(naziv, str) or not naziv.strip():
            raise KvizGreska(f"oblasti: label for {slovo} must be a non-empty string")

    sim = cfg.get("simulacija")
    if not isinstance(sim, dict):
        raise KvizGreska("simulacija: table required")
    if "prolaz" in sim and not _ceo_broj(sim["prolaz"]):
        raise KvizGreska("simulacija.prolaz: must be an integer >= 1")
    if ("broj" in sim) == ("sastav" in sim):
        raise KvizGreska("simulacija: exactly one of broj or sastav is required")
    if "broj" in sim and not _ceo_broj(sim["broj"]):
        raise KvizGreska("simulacija.broj: must be an integer >= 1")
    if "sastav" in sim:
        sastav = sim["sastav"]
        if not isinstance(sastav, dict) or not sastav:
            raise KvizGreska("simulacija.sastav: must be a table area -> count")
        for slovo, n in sastav.items():
            if slovo not in oblasti:
                raise KvizGreska(f"simulacija.sastav: area {slovo} is not in oblasti")
            if not _ceo_broj(n):
                raise KvizGreska(f"simulacija.sastav: count for {slovo} must be an integer >= 1")
    return cfg


def _ocisti_module():
    for ime in list(sys.modules):
        if ime in ("banka", "termini", "kljuc") or (ime.startswith("banka_") and ime != "banka_api"):
            del sys.modules[ime]


def _greska(datoteka: str, e: BaseException) -> str:
    return f"{datoteka}: " + traceback.format_exception_only(type(e), e)[-1].strip()


def ucitaj_kviz(folder: Path, cfg_path: Path | None = None, oblasti: str | None = None) -> Kviz:
    """Load a quiz folder. With oblasti (e.g. "J"), only those areas' banka_<area>.py files are imported."""
    folder = Path(folder).resolve()
    cfg_path = Path(cfg_path) if cfg_path else folder / "kviz.toml"
    try:
        cfg = tomllib.loads(cfg_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise KvizGreska(f"kviz.toml: not found at {cfg_path}") from None
    except tomllib.TOMLDecodeError as e:
        raise KvizGreska(f"kviz.toml: {e}") from None
    cfg = proveri_cfg(cfg)
    if oblasti is not None:
        oblasti = oblasti.strip().upper()
        nepoznata = sorted(set(oblasti) - set(cfg["oblasti"]))
        if not oblasti or nepoznata:
            raise KvizGreska(f"oblast {oblasti!r}: give area letters from kviz.toml [oblasti] "
                             f"({''.join(cfg['oblasti'])})" + (f"; unknown: {''.join(nepoznata)}" if nepoznata else ""))
    slova = [g for g in cfg["oblasti"] if oblasti is None or g in oblasti]

    sys.dont_write_bytecode = True
    for p in (str(ENGINE), str(folder)):
        while p in sys.path:
            sys.path.remove(p)
    sys.path[:0] = [str(folder), str(ENGINE)]
    _ocisti_module()
    importlib.invalidate_caches()
    try:
        try:
            banka_mod = importlib.import_module("banka")
        except Exception as e:  # noqa: BLE001 - reported to the user
            raise KvizGreska(_greska("banka.py", e)) from None
        pitanja = banka_mod.BANKA
        greske = []
        for g in slova:
            ime = f"banka_{g.lower()}"
            if not (folder / f"{ime}.py").exists() or ime in sys.modules:
                continue  # missing, or already imported by an older banka.py itself
            pre = len(pitanja)
            try:
                importlib.import_module(ime)
            except Exception as e:  # noqa: BLE001 - one broken area file must not stop the others
                del pitanja[pre:]
                greske.append(_greska(f"{ime}.py", e))
        banka = [normalize(p) for p in pitanja if p["g"] in slova]

        termini, termini_oblast = {}, {}
        if (folder / "termini.py").exists():
            for kljuc_, v in importlib.import_module("termini").TERMINI.items():
                if isinstance(v, dict):
                    for ime_, rx in v.items():
                        termini[ime_], termini_oblast[ime_] = rx, kljuc_
                else:
                    termini[kljuc_], termini_oblast[kljuc_] = v, None

        kljuc = None
        if (folder / "kljuc.py").exists():
            k = getattr(importlib.import_module("kljuc"), "KLJUC", None)
            if isinstance(k, dict):
                kljuc = dict(k)
            elif k is not None:
                kljuc = {i: None for i in k}
    finally:
        _ocisti_module()
        sys.path[:] = [p for p in sys.path if p != str(folder)]
    return Kviz(folder, cfg, banka, termini, termini_oblast, kljuc, greske)
