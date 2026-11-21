import pytest

from conftest import MINI, MINI_CYR, copy_quiz
from bank_api import normalize
from load import QuizError, load_quiz


def test_loads_fixture():
    quiz = load_quiz(MINI)
    assert len(quiz.bank) == 4
    assert [p["id"] for p in quiz.bank if p["area"] == "A"][0] == "A001"
    assert quiz.items == {"O1": "A"}
    assert quiz.term_area == {"crvena": "A", "glavni grad": "B"}
    assert quiz.terms == {"crvena": "crven", "glavni grad": "Beograd"}
    assert list(quiz.cfg["areas"]) == ["A", "B"]
    assert quiz.cfg["off_source_label"] is None
    assert quiz.cfg["language"] == "sr-Latn" and quiz.cfg["content_language"] == "sr-Latn"
    assert quiz.cfg["cyrillic_only"] is False
    assert quiz.load_errors == []


def test_cyr_defaults():
    cfg = load_quiz(MINI_CYR).cfg
    assert cfg["language"] == "ru" and cfg["content_language"] == "sr-Cyrl" and cfg["cyrillic_only"] is True
    assert cfg["off_source_label"] is None
    assert cfg["simulation"].get("pass_mark") is None


def test_areas_filter():
    quiz = load_quiz(MINI, areas="B")
    assert {p["area"] for p in quiz.bank} == {"B"}
    assert quiz.bank[0]["id"] == "B001"


def test_broken_area_file_is_reported(mini_copy):
    (mini_copy / "bank_b.py").write_text("from bank import Q\nQ(\n", encoding="utf-8")
    quiz = load_quiz(mini_copy, areas="A")
    assert len(quiz.bank) == 2 and quiz.load_errors == []
    quiz = load_quiz(mini_copy)
    assert {p["area"] for p in quiz.bank} == {"A"}
    assert len(quiz.load_errors) == 1 and "bank_b.py" in quiz.load_errors[0]


def test_multi_and_optional_fields():
    quiz = load_quiz(MINI)
    multi = next(p for p in quiz.bank if p["multi"])
    assert multi["ok"] == [0, 1] and multi["items"] == ["O1"]
    off = next(p for p in quiz.bank if p.get("off_source"))
    assert off["code"] == "x = 1"
    plain = quiz.bank[-1]
    assert "off_source" not in plain and "img" not in plain and "code" not in plain
    assert plain["note"] == "Pitanje iz geografije."
    assert next(p for p in quiz.bank if "img" in p)["img"] == "A_picture"


def test_normalize_int_ok():
    p = normalize({"ok": 2, "opts": [{"t": "a"}, {"t": "b"}, {"t": "c"}]})
    assert p["ok"] == [2] and p["multi"] is False


BASE = """title = "T"
heading = "N"
subtitle = "P"
intro = "U"
storage_key = "k-v1"
output = "k.html"
citation = "P1"
language = "sr-Latn"

[areas]
A = "Prva"
B = "Druga"

[simulation]
pass_mark = 2
count = 3
"""


@pytest.mark.parametrize("edit, field", [
    (lambda s: s.replace('citation = "P1"\n', ""), "citation"),
    (lambda s: s.replace('"k.html"', '"k.htm"'), "output"),
    (lambda s: s + "mix = { A = 1 }\n", "mix"),
    (lambda s: s.replace("count = 3", "mix = { A = 1, C = 1 }"), "mix"),
    (lambda s: s.replace('A = "Prva"', 'a = "Prva"'), "areas"),
    (lambda s: s.replace('B = "Druga"\n', ""), "areas"),
    (lambda s: s.replace('B = "Druga"\n', "".join(f'{c} = "x"\n' for c in "BCDEFGH")), "areas"),
    (lambda s: s.replace('citation = "P1"', 'citation = "("'), "citation"),
    (lambda s: s.replace('language = "sr-Latn"', 'language = "sr-Cirl"'), "language"),
    (lambda s: s.replace('language = "sr-Latn"', 'language = "sr-Latn"\ncyrillic_only = "yes"'), "cyrillic_only"),
])
def test_bad_config(tmp_path, edit, field):
    q = copy_quiz(MINI, tmp_path / "q")
    (q / "quiz.toml").write_text(edit(BASE), encoding="utf-8")
    with pytest.raises(QuizError, match=field):
        load_quiz(q)


def test_cfg_path_override_and_no_pycache(tmp_path):
    q = copy_quiz(MINI, tmp_path / "q")
    (tmp_path / "k.toml").write_text((q / "quiz.toml").read_text(encoding="utf-8"), encoding="utf-8")
    (q / "quiz.toml").unlink()
    quiz = load_quiz(q, cfg_path=tmp_path / "k.toml")
    assert len(quiz.bank) == 4
    assert not list(q.rglob("__pycache__"))


def test_two_quizzes_in_one_process(tmp_path):
    assert len(load_quiz(MINI).bank) == 4
    q = copy_quiz(MINI, tmp_path / "q")
    s = (q / "bank_b.py").read_text(encoding="utf-8")
    (q / "bank_b.py").write_text(s[:s.index('Q("B", "Glavni')], encoding="utf-8")
    (q / "terms.py").write_text('TERMS = {"A": {"crvena": r"crven"}}\n', encoding="utf-8")
    assert len(load_quiz(q).bank) == 3


def test_area_filter_is_case_insensitive_and_validated():
    assert {p["area"] for p in load_quiz(MINI, areas="b").bank} == {"B"}
    for bad in ("Z", "", "AZ"):
        with pytest.raises(QuizError, match="area"):
            load_quiz(MINI, areas=bad)


@pytest.mark.parametrize("edit, field", [('language = "xx"', "language"), ('content_language = "Serbian!"', "content_language")])
def test_language_config_errors(tmp_path, edit, field):
    q = copy_quiz(MINI, tmp_path / "q")
    if field == "language":
        text = BASE.replace('language = "sr-Latn"', edit)
    else:
        text = BASE.replace('language = "sr-Latn"', 'language = "sr-Latn"\n' + edit)
    (q / "quiz.toml").write_text(text, encoding="utf-8")
    with pytest.raises(QuizError) as e:
        load_quiz(q)
    assert str(e.value).startswith(field)
    if field == "language":
        assert "en, ru, sr-Cyrl, sr-Latn" in str(e.value)


def test_language_defaults_to_english(tmp_path):
    q = copy_quiz(MINI, tmp_path / "q")
    (q / "quiz.toml").write_text(BASE.replace('language = "sr-Latn"\n', ""), encoding="utf-8")
    cfg = load_quiz(q).cfg
    assert cfg["language"] == "en" and cfg["content_language"] == "en"
    (q / "quiz.toml").write_text(BASE.replace('language = "sr-Latn"', 'language = "ru"'), encoding="utf-8")
    cfg = load_quiz(q).cfg
    assert cfg["language"] == "ru" and cfg["content_language"] == "ru"
