import subprocess
import sys

from conftest import ENGINE, MINI, MINI_CYR
from check import check, summary
from load import load_quiz

CHECK = ENGINE / "check.py"


def mini():
    return load_quiz(MINI)


def question(k, text):
    return next(p for p in k.bank if p["q"].startswith(text))


def one(problems, part):
    assert len(problems) == 1, problems
    assert part in problems[0], problems


def test_fixture_passes():
    assert check(mini()) == []
    assert check(load_quiz(MINI_CYR)) == []


def test_two_options():
    k = mini()
    p = question(k, "Glavni grad")
    p["opts"] = p["opts"][:2]
    one(check(k), p["id"])


def test_duplicate_options():
    k = mini()
    p = question(k, "Glavni grad")
    p["opts"][2]["t"] = p["opts"][1]["t"].upper()
    one(check(k), p["id"])


def test_all_correct():
    k = mini()
    p = question(k, "Glavni grad")
    p["ok"] = [0, 1, 2]
    one(check(k), p["id"])


def test_empty_why():
    k = mini()
    p = question(k, "Glavni grad")
    p["opts"][1]["why"] = "  "
    one(check(k), p["id"])


def test_repeated_question():
    k = mini()
    p = question(k, "Glavni grad")
    p["q"] = question(k, "Koliko je x")["q"]
    one(check(k), p["id"])


def test_same_question_different_picture_ok():
    k = mini()
    question(k, "Koje su boje")["q"] = question(k, "Šta je prikazano")["q"]
    assert check(k) == []


def test_unknown_area():
    k = mini()
    p = question(k, "Glavni grad")
    p["area"] = "Z"
    one(check(k), p["id"])


def test_why_without_source():
    k = mini()
    p = question(k, "Glavni grad")
    p["opts"][1]["why"] = "Novi Sad nije glavni grad."
    one(check(k), p["id"])


def test_off_source_why_without_citation_ok():
    k = mini()
    p = question(k, "Glavni grad")
    p["off_source"] = True
    p["opts"][1]["why"] = "Opšte znanje."
    assert check(k) == []


def test_uncovered_term():
    k = mini()
    k.terms["nepostojeći"] = r"xyzzy"
    k.term_area["nepostojeći"] = None
    one(check(k), "terms: nepostojeći")


def test_bad_term_regex():
    k = mini()
    k.terms["loš"] = r"("
    k.term_area["loš"] = "A"
    one(check(k), "terms: loš: invalid regex")


def test_unused_key_number():
    k = mini()
    k.items["O2"] = "B"
    one(check(k), "items: O2")


def test_unknown_key_id():
    k = mini()
    p = question(k, "Glavni grad")
    p["items"] = ["O9"]
    one(check(k), "O9")


def test_missing_picture():
    k = mini()
    p = question(k, "Šta je prikazano")
    p["img"] = "A_nema"
    one(check(k), "A_nema")


def test_latin_in_cyr_quiz():
    k = load_quiz(MINI_CYR)
    p = question(k, "Главни град")
    p["opts"][0]["why"] = "стр. 5: Београд, 3 cm на мапи."
    one(check(k), p["id"])
    k.cfg["latin_allowed"] = ["cm"]
    assert check(k) == []


def test_area_ignores_broken_other_area(mini_copy):
    (mini_copy / "bank_b.py").write_text("from bank import Q\nQ(\n", encoding="utf-8")
    r = subprocess.run([sys.executable, CHECK, str(mini_copy), "--area", "A"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run([sys.executable, CHECK, str(mini_copy)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "bank_b.py" in r.stdout


def test_area_limits_coverage():
    k = load_quiz(MINI, areas="A")
    assert check(k, areas="A") == []


def test_sim_larger_than_bank():
    k = mini()
    k.cfg["simulation"]["count"] = 99
    one(check(k), "config:")
    k = mini()
    del k.cfg["simulation"]["count"]
    k.cfg["simulation"]["mix"] = {"A": 9}
    p = check(k)
    one(p, "config:")
    assert "A" in p[0]


def test_summary():
    s = summary(mini())
    assert "4" in s and "A: 2" in s and "B: 2" in s


def test_cli_exit_codes(mini_copy):
    r = subprocess.run([sys.executable, CHECK, str(MINI)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    s = (mini_copy / "bank_b.py").read_text(encoding="utf-8")
    (mini_copy / "bank_b.py").write_text(s.replace("P1, sl. 5: Beograd.", "Beograd."), encoding="utf-8")
    r = subprocess.run([sys.executable, CHECK, str(mini_copy)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "ERROR" in r.stdout


def test_area_lowercase_checks_that_area(mini_copy):
    s = (mini_copy / "bank_b.py").read_text(encoding="utf-8")
    (mini_copy / "bank_b.py").write_text(s.replace("P1, sl. 5: Beograd.", "Beograd."), encoding="utf-8")
    for area, code_ in (("b", 1), ("B", 1), ("Z", 1), ("a", 0)):
        r = subprocess.run([sys.executable, CHECK, str(mini_copy), "--area", area],
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == code_, (area, r.stdout)


def test_latin_in_cyr_config():
    k = load_quiz(MINI_CYR)
    k.cfg["intro"] = "Mali kviz za decu."
    k.cfg["areas"]["A"] = "Prva oblast"
    p = check(k)
    assert len(p) == 2 and all(x.startswith("config:") for x in p), p


def test_pass_mark_above_sim_size():
    k = mini()
    k.cfg["simulation"]["pass_mark"] = 9
    one(check(k), "pass_mark")


def test_empty_area():
    k = mini()
    k.cfg["areas"]["C"] = "Treća oblast"
    one(check(k), "C")
