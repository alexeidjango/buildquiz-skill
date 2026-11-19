import pytest

from conftest import MINI, MINI_CYR, kopija
from banka_api import normalize
from ucitaj import KvizGreska, ucitaj_kviz


def test_loads_fixture():
    k = ucitaj_kviz(MINI)
    assert len(k.banka) == 4
    assert [p["id"] for p in k.banka if p["g"] == "A"][0] == "A001"
    assert k.kljuc == {"O1": "A"}
    assert k.termini_oblast == {"crvena": "A", "glavni grad": "B"}
    assert k.termini == {"crvena": "crven", "glavni grad": "Beograd"}
    assert list(k.cfg["oblasti"]) == ["A", "B"]
    assert k.cfg["oznaka_van"] == "van slajdova"
    assert k.cfg["pismo"] == "lat"
    assert k.greske_ucitavanja == []


def test_cyr_defaults():
    cfg = ucitaj_kviz(MINI_CYR).cfg
    assert cfg["pismo"] == "cyr"
    assert cfg["oznaka_van"] == "ван ових страна"
    assert cfg["simulacija"].get("prolaz") is None


def test_oblasti_filter():
    k = ucitaj_kviz(MINI, oblasti="B")
    assert {p["g"] for p in k.banka} == {"B"}
    assert k.banka[0]["id"] == "B001"


def test_broken_area_file_is_reported(mini_kopija):
    (mini_kopija / "banka_b.py").write_text("from banka import Q\nQ(\n", encoding="utf-8")
    k = ucitaj_kviz(mini_kopija, oblasti="A")
    assert len(k.banka) == 2 and k.greske_ucitavanja == []
    k = ucitaj_kviz(mini_kopija)
    assert {p["g"] for p in k.banka} == {"A"}
    assert len(k.greske_ucitavanja) == 1 and "banka_b.py" in k.greske_ucitavanja[0]


def test_multi_and_optional_fields():
    k = ucitaj_kviz(MINI)
    multi = next(p for p in k.banka if p["multi"])
    assert multi["ok"] == [0, 1] and multi["kljuc"] == ["O1"]
    van = next(p for p in k.banka if p.get("van"))
    assert van["code"] == "x = 1"
    obicno = k.banka[-1]
    assert "van" not in obicno and "img" not in obicno and "code" not in obicno
    assert obicno["note"] == "Pitanje iz geografije."
    assert next(p for p in k.banka if "img" in p)["img"] == "A_slika"


def test_normalize_int_ok():
    p = normalize({"ok": 2, "opts": [{"t": "a"}, {"t": "b"}, {"t": "c"}]})
    assert p["ok"] == [2] and p["multi"] is False


OSNOVA = """title = "T"
naslov = "N"
podnaslov = "P"
uvod = "U"
kljuc_skladista = "k-v1"
izlaz = "k.html"
izvor = "P1"
pismo = "lat"

[oblasti]
A = "Prva"
B = "Druga"

[simulacija]
prolaz = 2
broj = 3
"""


@pytest.mark.parametrize("izmena, polje", [
    (lambda s: s.replace('izvor = "P1"\n', ""), "izvor"),
    (lambda s: s.replace('"k.html"', '"k.htm"'), "izlaz"),
    (lambda s: s + "sastav = { A = 1 }\n", "sastav"),
    (lambda s: s.replace("broj = 3", "sastav = { A = 1, C = 1 }"), "sastav"),
    (lambda s: s.replace('A = "Prva"', 'a = "Prva"'), "oblasti"),
    (lambda s: s.replace('B = "Druga"\n', ""), "oblasti"),
    (lambda s: s.replace('B = "Druga"\n', "".join(f'{c} = "x"\n' for c in "BCDEFGH")), "oblasti"),
    (lambda s: s.replace('izvor = "P1"', 'izvor = "("'), "izvor"),
    (lambda s: s.replace('pismo = "lat"', 'pismo = "cir"'), "pismo"),
])
def test_bad_config(tmp_path, izmena, polje):
    q = kopija(MINI, tmp_path / "q")
    (q / "kviz.toml").write_text(izmena(OSNOVA), encoding="utf-8")
    with pytest.raises(KvizGreska, match=polje):
        ucitaj_kviz(q)


def test_cfg_path_override_and_no_pycache(tmp_path):
    q = kopija(MINI, tmp_path / "q")
    (tmp_path / "k.toml").write_text((q / "kviz.toml").read_text(encoding="utf-8"), encoding="utf-8")
    (q / "kviz.toml").unlink()
    k = ucitaj_kviz(q, cfg_path=tmp_path / "k.toml")
    assert len(k.banka) == 4
    assert not list(q.rglob("__pycache__"))


def test_two_quizzes_in_one_process(tmp_path):
    assert len(ucitaj_kviz(MINI).banka) == 4
    q = kopija(MINI, tmp_path / "q")
    s = (q / "banka_b.py").read_text(encoding="utf-8")
    (q / "banka_b.py").write_text(s[:s.index('Q("B", "Glavni')], encoding="utf-8")
    (q / "termini.py").write_text('TERMINI = {"A": {"crvena": r"crven"}}\n', encoding="utf-8")
    assert len(ucitaj_kviz(q).banka) == 3


def test_oblast_is_case_insensitive_and_validated():
    assert {p["g"] for p in ucitaj_kviz(MINI, oblasti="b").banka} == {"B"}
    for lose in ("Z", "", "AZ"):
        with pytest.raises(KvizGreska, match="oblast"):
            ucitaj_kviz(MINI, oblasti=lose)
