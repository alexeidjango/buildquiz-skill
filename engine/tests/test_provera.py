import subprocess
import sys

from conftest import ENGINE, MINI, MINI_CYR
from provera import proveri, sazetak
from ucitaj import ucitaj_kviz

PROVERA = ENGINE / "provera.py"


def mini():
    return ucitaj_kviz(MINI)


def pitanje(k, tekst):
    return next(p for p in k.banka if p["q"].startswith(tekst))


def jedan(problemi, deo):
    assert len(problemi) == 1, problemi
    assert deo in problemi[0], problemi


def test_fixture_passes():
    assert proveri(mini()) == []
    assert proveri(ucitaj_kviz(MINI_CYR)) == []


def test_two_options():
    k = mini()
    p = pitanje(k, "Glavni grad")
    p["opts"] = p["opts"][:2]
    jedan(proveri(k), p["id"])


def test_duplicate_options():
    k = mini()
    p = pitanje(k, "Glavni grad")
    p["opts"][2]["t"] = p["opts"][1]["t"].upper()
    jedan(proveri(k), p["id"])


def test_all_correct():
    k = mini()
    p = pitanje(k, "Glavni grad")
    p["ok"] = [0, 1, 2]
    jedan(proveri(k), p["id"])


def test_empty_why():
    k = mini()
    p = pitanje(k, "Glavni grad")
    p["opts"][1]["why"] = "  "
    jedan(proveri(k), p["id"])


def test_repeated_question():
    k = mini()
    p = pitanje(k, "Glavni grad")
    p["q"] = pitanje(k, "Koliko je x")["q"]
    jedan(proveri(k), p["id"])


def test_same_question_different_picture_ok():
    k = mini()
    pitanje(k, "Koje su boje")["q"] = pitanje(k, "Šta je prikazano")["q"]
    assert proveri(k) == []


def test_unknown_area():
    k = mini()
    p = pitanje(k, "Glavni grad")
    p["g"] = "Z"
    jedan(proveri(k), p["id"])


def test_why_without_source():
    k = mini()
    p = pitanje(k, "Glavni grad")
    p["opts"][1]["why"] = "Novi Sad nije glavni grad."
    jedan(proveri(k), p["id"])


def test_van_why_without_source_ok():
    k = mini()
    p = pitanje(k, "Glavni grad")
    p["van"] = True
    p["opts"][1]["why"] = "Opšte znanje."
    assert proveri(k) == []


def test_uncovered_term():
    k = mini()
    k.termini["nepostojeći"] = r"xyzzy"
    k.termini_oblast["nepostojeći"] = None
    jedan(proveri(k), "termini: nepostojeći")


def test_bad_term_regex():
    k = mini()
    k.termini["loš"] = r"("
    k.termini_oblast["loš"] = "A"
    jedan(proveri(k), "termini: loš: neispravan regex")


def test_unused_key_number():
    k = mini()
    k.kljuc["O2"] = "B"
    jedan(proveri(k), "kljuc: O2")


def test_unknown_key_id():
    k = mini()
    p = pitanje(k, "Glavni grad")
    p["kljuc"] = ["O9"]
    jedan(proveri(k), "O9")


def test_missing_picture():
    k = mini()
    p = pitanje(k, "Šta je prikazano")
    p["img"] = "A_nema"
    jedan(proveri(k), "A_nema")


def test_latin_in_cyr_quiz():
    k = ucitaj_kviz(MINI_CYR)
    p = pitanje(k, "Главни град")
    p["opts"][0]["why"] = "стр. 5: Београд, 3 cm на мапи."
    jedan(proveri(k), p["id"])
    k.cfg["latinica_dozvoljena"] = ["cm"]
    assert proveri(k) == []


def test_oblast_ignores_broken_other_area(mini_kopija):
    (mini_kopija / "banka_b.py").write_text("from banka import Q\nQ(\n", encoding="utf-8")
    r = subprocess.run([sys.executable, PROVERA, str(mini_kopija), "--oblast", "A"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    r = subprocess.run([sys.executable, PROVERA, str(mini_kopija)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "banka_b.py" in r.stdout


def test_oblast_limits_coverage():
    k = ucitaj_kviz(MINI, oblasti="A")
    assert proveri(k, oblasti="A") == []


def test_sim_larger_than_bank():
    k = mini()
    k.cfg["simulacija"]["broj"] = 99
    jedan(proveri(k), "config:")
    k = mini()
    del k.cfg["simulacija"]["broj"]
    k.cfg["simulacija"]["sastav"] = {"A": 9}
    p = proveri(k)
    jedan(p, "config:")
    assert "A" in p[0]


def test_sazetak():
    s = sazetak(mini())
    assert "4" in s and "A: 2" in s and "B: 2" in s


def test_cli_exit_codes(mini_kopija):
    r = subprocess.run([sys.executable, PROVERA, str(MINI)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    s = (mini_kopija / "banka_b.py").read_text(encoding="utf-8")
    (mini_kopija / "banka_b.py").write_text(s.replace("P1, sl. 5: Beograd.", "Beograd."), encoding="utf-8")
    r = subprocess.run([sys.executable, PROVERA, str(mini_kopija)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "GREŠKA" in r.stdout


def test_oblast_lowercase_checks_that_area(mini_kopija):
    s = (mini_kopija / "banka_b.py").read_text(encoding="utf-8")
    (mini_kopija / "banka_b.py").write_text(s.replace("P1, sl. 5: Beograd.", "Beograd."), encoding="utf-8")
    for oblast, kod in (("b", 1), ("B", 1), ("Z", 1), ("a", 0)):
        r = subprocess.run([sys.executable, PROVERA, str(mini_kopija), "--oblast", oblast],
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == kod, (oblast, r.stdout)


def test_latin_in_cyr_config():
    k = ucitaj_kviz(MINI_CYR)
    k.cfg["uvod"] = "Mali kviz za decu."
    k.cfg["oblasti"]["A"] = "Prva oblast"
    p = proveri(k)
    assert len(p) == 2 and all(x.startswith("config:") for x in p), p


def test_prolaz_above_sim_size():
    k = mini()
    k.cfg["simulacija"]["prolaz"] = 9
    jedan(proveri(k), "prolaz")


def test_empty_area():
    k = mini()
    k.cfg["oblasti"]["C"] = "Treća oblast"
    jedan(proveri(k), "C")
