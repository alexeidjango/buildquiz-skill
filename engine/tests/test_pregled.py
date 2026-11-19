import json
import re
import tomllib

import pytest

from banka_api import normalize
from conftest import MINI, MINI_CYR, REPO, kopija
from izgradi import izgradi_html
from pregled import pregledaj
from ucitaj import proveri_cfg, ucitaj_kviz


def napravi(tmp_path, folder, cfg_path=None, ime="kviz.html"):
    k = ucitaj_kviz(folder, cfg_path)
    out = tmp_path / "š folder" / ime
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(izgradi_html(k.cfg, k.banka, k.folder), encoding="utf-8")
    return out


def toml(oblasti: dict, sim: str, ostalo: str = "") -> str:
    o = "\n".join(f'{g} = "{n}"' for g, n in oblasti.items())
    return (f'title = "T"\nnaslov = "N"\npodnaslov = "P"\nuvod = "U"\nkljuc_skladista = "t-v1"\n'
            f'izlaz = "t.html"\nizvor = "."\n{ostalo}\n[oblasti]\n{o}\n\n[simulacija]\n{sim}\n')


def test_mini_selftest(tmp_path):
    out = napravi(tmp_path, MINI)
    assert pregledaj(out).startswith("SELFTEST OK modes=3 sim=3")
    assert pregledaj(out, nostorage=True).startswith("SELFTEST OK modes=3 sim=3")


def test_sastav_selftest(tmp_path):
    q = kopija(MINI, tmp_path / "q")
    s = (q / "kviz.toml").read_text(encoding="utf-8").replace("broj = 3", "sastav = { A = 1, B = 1 }")
    (q / "kviz.toml").write_text(s, encoding="utf-8")
    assert pregledaj(napravi(tmp_path, q)).startswith("SELFTEST OK modes=3 sim=2")


def test_mini_cyr_selftest(tmp_path):
    rez = pregledaj(napravi(tmp_path, MINI_CYR))
    assert rez.startswith("SELFTEST OK modes=3 sim=3") and "img=1" in rez


def test_failure_is_reported(tmp_path):
    k = ucitaj_kviz(MINI)
    out = tmp_path / "prazno.html"
    out.write_text(izgradi_html(k.cfg, [], k.folder), encoding="utf-8")
    assert pregledaj(out).startswith("SELFTEST FAIL")


POSTOJECI = {
    "urcp/kviz": ({"O": "osnove i program", "M": "metrike i analiza", "Z": "životni ciklus", "P": "procena rizika"},
                  "prolaz = 15\nbroj = 30", 30),
    "zastitamreza/kviz": ({"Z": "zero trust, OS i etika", "K": "kontrola pristupa", "F": "zaštitni zid",
                           "N": "napadi i izviđanje"}, "prolaz = 15\nbroj = 30", 30),
    "english/kviz": ({"R": "reči iz tekstova", "T": "trendovi i grafikoni", "K": "kolokacije i tvorba",
                      "G": "kondicionali 0–3", "M": "mešoviti kondicionali", "A": "inverzija, alternative za if",
                      "X": "mock test"}, "prolaz = 8\nsastav = { R = 4, T = 4, K = 2, M = 2, G = 1, A = 2 }", 15),
}


@pytest.mark.parametrize("ime", list(POSTOJECI))
def test_existing_banks(tmp_path, ime):
    folder = REPO / ime
    if not (folder / "banka.py").exists():
        pytest.skip(f"{ime} missing")
    oblasti, sim, n = POSTOJECI[ime]
    (tmp_path / "k.toml").write_text(toml(oblasti, sim), encoding="utf-8")
    assert pregledaj(napravi(tmp_path, folder, tmp_path / "k.toml")).startswith(f"SELFTEST OK modes=3 sim={n}")


def test_verovatnoca_code_bank(tmp_path):
    src = REPO / "verovatnoca/kviz/kviz_verovatnoca_k1.html"
    if not src.exists():
        pytest.skip("verovatnoca missing")
    m = re.search(r'<script id="bank" type="application/json">(.*?)</script>', src.read_text(encoding="utf-8"), re.S)
    banka = [normalize(p) for p in json.loads(m.group(1))]
    cfg = proveri_cfg(tomllib.loads(
        toml({"P": "pandas", "S": "numpy", "R": "grafik"}, "prolaz = 2\nsastav = { P = 1, S = 1, R = 1 }")))
    out = tmp_path / "v.html"
    html = izgradi_html(cfg, banka, tmp_path)
    assert "function highlight(" in html
    out.write_text(html, encoding="utf-8")
    rez = pregledaj(out)
    assert rez.startswith("SELFTEST OK modes=3 sim=3") and "code=1" in rez


def test_biologija_bank(tmp_path):
    folder = REPO / "biologija/kviz"
    if not (folder / "banka.py").exists():
        pytest.skip("biologija missing")
    (tmp_path / "k.toml").write_text(toml(
        {"J": "Једноћелијски организми", "V": "Вегетативни органи биљака", "R": "Размножавање и раст биљака",
         "T": "Тест са стр. 72–73"}, "broj = 20", "pismo = 'cyr'"), encoding="utf-8")
    rez = pregledaj(napravi(tmp_path, folder, tmp_path / "k.toml"))
    assert rez.startswith("SELFTEST OK modes=3 sim=20") and "img=1" in rez


def test_render_check_makes_no_network_requests(tmp_path):
    import http.server
    import threading
    pozivi = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            pozivi.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        stranica = tmp_path / "mreza.html"
        stranica.write_text(f'<body><img src="http://localhost:{port}/a.png">'
                            f'<link rel="stylesheet" href="http://kviz.localhost:{port}/b.css">'
                            "<script>const p = document.createElement('pre'); p.id = 'selftest';"
                            "p.textContent = 'SELFTEST OK'; document.body.appendChild(p);</script></body>",
                            encoding="utf-8")
        assert pregledaj(stranica) == "SELFTEST OK"
    finally:
        srv.shutdown()
    assert pozivi == []


def test_comment_script_text_still_plays(tmp_path):
    k = ucitaj_kviz(MINI)
    k.banka[-1]["q"] = "XSS primer: <!--<script> Glavni grad Srbije je:"
    k.banka[-1]["opts"][1]["why"] = "P1 <!--<script>alert(1)</script>"
    out = tmp_path / "k.html"
    out.write_text(izgradi_html(k.cfg, k.banka, k.folder), encoding="utf-8")
    assert pregledaj(out).startswith("SELFTEST OK")
