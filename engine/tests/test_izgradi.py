import html.parser
import json
import re
import subprocess
import sys

import pytest

from conftest import ENGINE, MINI, MINI_CYR, kopija
from izgradi import izgradi_html, sim_opis
from ucitaj import ucitaj_kviz

IZGRADI = ENGINE / "izgradi.py"
SABLON = (ENGINE / "sablon.html").read_text(encoding="utf-8") if (ENGINE / "sablon.html").exists() else ""


def build(folder=MINI):
    k = ucitaj_kviz(folder)
    return izgradi_html(k.cfg, k.banka, k.folder), k


def skripta(out, ime):
    m = re.search(r'<script id="' + ime + r'" type="application/json">\n(.*?)\n</script>', out, re.S)
    return json.loads(m.group(1))


def test_no_placeholder_left():
    out, _ = build()
    bez_banke = re.sub(r'<script id="(bank|slike)".*?</script>', "", out, flags=re.S)
    assert not re.search(r"__[A-ZŠ]+__", bez_banke)


def test_area_buttons():
    out, _ = build()
    grupa = re.search(r'<div class="choicegrid two" id="areaPick">(.*?)</div>', out, re.S).group(1)
    assert len(re.findall(r"data-val=", grupa)) == 3
    assert 'data-val="all"' in grupa and "Prva oblast" in grupa and "Druga oblast" in grupa
    assert 'id="cntA"' in grupa and 'id="cntB"' in grupa


def test_cfg_json_roundtrip():
    out, _ = build()
    cfg = json.loads(re.search(r"const CFG = (.*?);\n", out).group(1))
    assert cfg["prolaz"] == 2 and cfg["broj"] == 3 and cfg["sastav"] is None
    assert cfg["oznakaVan"] == "van slajdova" and cfg["pismo"] == "lat" and cfg["kljuc"] == "mini-v1"
    assert cfg["oblasti"] == {"A": "Prva oblast", "B": "Druga oblast"}


def test_bank_json_roundtrip():
    out, k = build()
    assert skripta(out, "bank") == k.banka
    assert len(k.banka) == 4


def test_hostile_text_is_escaped(tmp_path):
    k = ucitaj_kviz(MINI)
    zlo = '</script><b>&"'
    p = k.banka[-1]
    p["q"] = "Pitanje " + zlo
    p["opts"][1]["t"] = "Opcija " + zlo
    p["opts"][1]["why"] = "P1 " + zlo
    k.cfg["uvod"] = "a < b & c"
    k.cfg["oblasti"]["B"] = "Druga " + zlo
    out = izgradi_html(k.cfg, k.banka, k.folder)
    assert skripta(out, "bank") == k.banka
    assert out.count("</script>") == SABLON.count("</script>")
    assert "</script><b>" not in out
    assert "a &lt; b &amp; c" in out


def test_sim_opis_broj():
    cfg = {"pismo": "lat", "oblasti": {"A": "X", "B": "Y"}, "simulacija": {"broj": 30, "prolaz": 15}}
    assert sim_opis(cfg) == "30 nasumičnih pitanja, prolaz 15, rezultat na kraju"


def test_sim_opis_sastav():
    cfg = {"pismo": "lat", "oblasti": {"A": "Prva oblast", "B": "Druga oblast"},
           "simulacija": {"sastav": {"B": 1, "A": 2}, "prolaz": 2}}
    assert sim_opis(cfg) == "3 pitanja: 2 prva oblast + 1 druga oblast, prolaz 2, rezultat na kraju"


def test_sim_opis_learning():
    assert sim_opis(ucitaj_kviz(MINI_CYR).cfg) == "3 насумична питања, резултат на крају"
    cfg = {"pismo": "cyr", "oblasti": {"A": "X", "B": "Y"}, "simulacija": {"broj": 21}}
    assert sim_opis(cfg) == "21 насумично питање, резултат на крају"
    cfg = {"pismo": "lat", "oblasti": {"A": "X", "B": "Y"}, "simulacija": {"broj": 12}}
    assert sim_opis(cfg) == "12 nasumičnih pitanja, rezultat na kraju"


def test_cli_writes_out(tmp_path):
    out = tmp_path / "x.html"
    r = subprocess.run([sys.executable, IZGRADI, str(MINI), "--out", str(out)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert out.exists() and "izgrađeno: 4 pitanja" in r.stdout


def test_pictures_embedded(tmp_path):
    out, _ = build()
    slike = skripta(out, "slike")
    assert list(slike) == ["A_slika"] and slike["A_slika"].startswith("data:image/jpeg;base64,")
    q = kopija(MINI, tmp_path / "q")
    (q / "slike" / "A_slika.jpg").unlink()
    k = ucitaj_kviz(q)
    with pytest.raises(Exception, match="A_slika"):
        izgradi_html(k.cfg, k.banka, k.folder)


class _Tekst(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.u_skripti = 0
        self.delovi = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.u_skripti += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.u_skripti -= 1

    def handle_data(self, data):
        if not self.u_skripti:
            self.delovi.append(data)


def test_cyrillic_ui_has_no_latin():
    out, _ = build(MINI_CYR)
    p = _Tekst()
    p.feed(out)
    tekst = " ".join(p.delovi)
    cyr = re.search(r"/\*T\.cyr\*/(.*?)/\*T\.cyr end\*/", out, re.S).group(1)
    stringovi = " ".join(re.findall(r"'((?:[^'\\]|\\.)*)'", cyr))
    lat = re.findall(r"[A-Za-zČčĆćŠšĐđŽž]{3,}", tekst + " " + stringovi)
    assert lat == [], lat
    assert 'lang="sr-Cyrl"' in out
