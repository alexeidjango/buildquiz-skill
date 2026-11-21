"""Read the author's quiz folders made before the engine had English names, for the acceptance tests.

Those quizzes (urcp, zastitamreza, english, biologija, verovatnoca) were built by hand before this engine
existed and use Serbian names: banka.py with its own Q() and a BANKA list, question fields g / van / kljuc /
knjiga, pictures in slike/. This module converts them, in memory or in a temp copy, into the current format.
The source folders are never written. This is the only file in the repo that knows the old names.
"""
import importlib
import json
import re
import shutil
import sys
from pathlib import Path

from bank_api import normalize

VEROVATNOCA_PAGE = "verovatnoca/kviz/kviz_verovatnoca_k1.html"  # an old built page (code questions)
_OLD_MODULES = ("banka", "termini", "kljuc", "knjiga")
_FIELDS = {"g": "area", "van": "off_source", "kljuc": "items", "knjiga": "items"}


def _convert(p: dict) -> dict:
    q = {}
    for k, v in p.items():
        new = _FIELDS.get(k, k)
        if new == "items":
            q.setdefault("items", [])
            q["items"] += list(v)
        else:
            q[new] = v
    if not q.get("items"):
        q.pop("items", None)
    return normalize(q)


def _purge():
    for name in list(sys.modules):
        if name in _OLD_MODULES or name.startswith("banka_"):
            del sys.modules[name]


def is_legacy_quiz(folder: Path) -> bool:
    """True if folder holds an old-format quiz (the acceptance tests skip when the author's folders are absent)."""
    return (Path(folder) / "banka.py").exists()


def legacy_bank(folder: Path) -> list[dict]:
    """The questions of an old-format quiz folder (its banka.py), converted to the current fields."""
    folder = Path(folder).resolve()
    sys.dont_write_bytecode = True
    _purge()
    sys.path.insert(0, str(folder))
    importlib.invalidate_caches()
    try:
        old = importlib.import_module("banka").BANKA
        return [_convert(p) for p in old]
    finally:
        _purge()
        sys.path[:] = [p for p in sys.path if p != str(folder)]


def legacy_html_bank(path: Path) -> list[dict]:
    """The questions stored in an old built quiz page (<script id="bank">), converted to the current fields."""
    m = re.search(r'<script id="bank" type="application/json">(.*?)</script>',
                  Path(path).read_text(encoding="utf-8"), re.S)
    return [_convert(p) for p in json.loads(m.group(1))]


def legacy_images(folder: Path, dst: Path) -> Path:
    """Copy an old quiz folder's slike/ to dst/images/ (where the builder looks) and return dst."""
    shutil.copytree(Path(folder) / "slike", Path(dst) / "images", dirs_exist_ok=True)
    return Path(dst)
