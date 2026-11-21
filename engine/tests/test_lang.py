import json
import re

from conftest import ENGINE
from load import available_languages

LANG = ENGINE / "lang"
PLACEHOLDER = re.compile(r"\{(\w+)\}")
PLURAL_CATEGORIES = {"zero", "one", "two", "few", "many", "other"}


def _load(code):
    return json.loads((LANG / f"{code}.json").read_text(encoding="utf-8"))


def placeholders(value) -> set[str]:
    """The {name} placeholders of a string value; of a plural object or list, those of all forms together."""
    if isinstance(value, dict):
        forms = value.values()
    elif isinstance(value, list):
        forms = value
    else:
        forms = [value]
    return {m for f in forms for m in PLACEHOLDER.findall(f)}


def test_language_files_match_english():
    ref = _load("en")
    for f in sorted(LANG.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        assert set(d) == {"name", "letters", "strings"}, f.name
        assert isinstance(d["name"], str) and d["name"].strip(), f.name
        assert len(d["letters"]) >= 8 and len(set(d["letters"])) == len(d["letters"]), f.name
        assert set(d["strings"]) == set(ref["strings"]), (f.name, set(d["strings"]) ^ set(ref["strings"]))
        for k, v in ref["strings"].items():
            w = d["strings"][k]
            assert type(w) is type(v), (f.name, k)
            if isinstance(v, dict):
                assert "other" in w and set(w) <= PLURAL_CATEGORIES, (f.name, k)
                assert all(isinstance(x, str) and x.strip() for x in w.values()), (f.name, k)
            elif isinstance(v, list):
                assert len(w) == len(v) and all(isinstance(x, str) and x.strip() for x in w), (f.name, k)
            else:
                assert w.strip(), (f.name, k)
            assert placeholders(w) == placeholders(v), (f.name, k)


def test_four_languages_present():
    assert {"en", "sr-Latn", "sr-Cyrl", "ru"} <= set(available_languages())
    assert available_languages() == sorted(available_languages())


def test_serbian_texts_unchanged():
    lat, cyr = _load("sr-Latn")["strings"], _load("sr-Cyrl")["strings"]
    assert (lat["start"], cyr["start"]) == ("Počni", "Почни")
    assert (lat["wrongExam"], cyr["wrongExam"]) == ("Netačno, 0 poena", "Нетачно, 0 поена")
    assert (lat["learn"], cyr["learn"]) == ("Uči", "Учи")
    assert lat["passNeeded"] == "Za prolaz treba {n} tačnih."
    assert lat["simRandom"]["other"] == "{n} nasumičnih pitanja"
    assert (lat["offSource"], cyr["offSource"]) == ("van slajdova", "ван слајдова")
    assert _load("sr-Cyrl")["letters"] == "абвгдђеж"


def test_cyrillic_languages_have_no_latin():
    for code in ("sr-Cyrl", "ru"):
        d = _load(code)
        texts = [d["name"], d["letters"]]
        for v in d["strings"].values():
            texts += list(v.values()) if isinstance(v, dict) else v if isinstance(v, list) else [v]
        latin = [w for t in texts for w in re.findall(r"[A-Za-z]+", PLACEHOLDER.sub("", t))]
        assert latin == [], (code, latin)
