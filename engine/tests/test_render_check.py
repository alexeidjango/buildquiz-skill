import re
import tomllib

import pytest

from conftest import MINI, MINI_CYR, REPO, build_quiz, copy_quiz
from build import build_html
from legacy import VEROVATNOCA_PAGE, is_legacy_quiz, legacy_bank, legacy_html_bank, legacy_images
from load import load_quiz, validate_config
from render_check import dump_dom, render


def toml(areas: dict, sim: str, rest: str = 'language = "sr-Latn"') -> str:
    o = "\n".join(f'{g} = "{n}"' for g, n in areas.items())
    return (f'title = "T"\nheading = "N"\nsubtitle = "P"\nintro = "U"\nstorage_key = "t-v1"\n'
            f'output = "t.html"\ncitation = "."\n{rest}\n[areas]\n{o}\n\n[simulation]\n{sim}\n')


def build_legacy(tmp_path, folder, cfg_text):
    """Build one of the author's old-format quiz folders (read through tests/legacy.py) into tmp_path."""
    cfg = validate_config(tomllib.loads(cfg_text))
    pictures = legacy_images(folder, tmp_path / "pics") if (folder / "slike").exists() else tmp_path
    out = tmp_path / "š folder" / "legacy.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(cfg, legacy_bank(folder), pictures), encoding="utf-8")
    return out


def test_mini_selftest(tmp_path):
    out = build_quiz(tmp_path, MINI)
    assert render(out).startswith("SELFTEST OK modes=3 sim=3")
    assert render(out, nostorage=True).startswith("SELFTEST OK modes=3 sim=3")


def test_mix_selftest(tmp_path):
    q = copy_quiz(MINI, tmp_path / "q")
    s = (q / "quiz.toml").read_text(encoding="utf-8").replace("count = 3", "mix = { A = 1, B = 1 }")
    (q / "quiz.toml").write_text(s, encoding="utf-8")
    assert render(build_quiz(tmp_path, q)).startswith("SELFTEST OK modes=3 sim=2")


def test_mini_cyr_selftest(tmp_path):
    res = render(build_quiz(tmp_path, MINI_CYR))
    assert res.startswith("SELFTEST OK modes=3 sim=3") and "img=1" in res


def test_failure_is_reported(tmp_path):
    quiz = load_quiz(MINI)
    out = tmp_path / "empty.html"
    out.write_text(build_html(quiz.cfg, [], quiz.folder), encoding="utf-8")
    assert render(out).startswith("SELFTEST FAIL")


EXISTING = {
    "urcp/kviz": ({"O": "osnove i program", "M": "metrike i analiza", "Z": "životni ciklus", "P": "procena rizika"},
                  "pass_mark = 15\ncount = 30", 30),
    "zastitamreza/kviz": ({"Z": "zero trust, OS i etika", "K": "kontrola pristupa", "F": "zaštitni zid",
                           "N": "napadi i izviđanje"}, "pass_mark = 15\ncount = 30", 30),
    "english/kviz": ({"R": "reči iz tekstova", "T": "trendovi i grafikoni", "K": "kolokacije i tvorba",
                      "G": "kondicionali 0–3", "M": "mešoviti kondicionali", "A": "inverzija, alternative za if",
                      "X": "mock test"}, "pass_mark = 8\nmix = { R = 4, T = 4, K = 2, M = 2, G = 1, A = 2 }", 15),
}


@pytest.mark.parametrize("name", list(EXISTING))
def test_existing_banks(tmp_path, name):
    folder = REPO / name
    if not is_legacy_quiz(folder):
        pytest.skip(f"{name} missing")
    areas, sim, n = EXISTING[name]
    assert render(build_legacy(tmp_path, folder, toml(areas, sim))).startswith(f"SELFTEST OK modes=3 sim={n}")


def test_verovatnoca_code_bank(tmp_path):
    src = REPO / VEROVATNOCA_PAGE
    if not src.exists():
        pytest.skip("verovatnoca missing")
    bank = legacy_html_bank(src)
    cfg = validate_config(tomllib.loads(
        toml({"P": "pandas", "S": "numpy", "R": "grafik"}, "pass_mark = 2\nmix = { P = 1, S = 1, R = 1 }")))
    out = tmp_path / "v.html"
    page = build_html(cfg, bank, tmp_path)
    assert "function highlight(" in page
    out.write_text(page, encoding="utf-8")
    res = render(out)
    assert res.startswith("SELFTEST OK modes=3 sim=3") and "code=1" in res


def test_biologija_bank(tmp_path):
    folder = REPO / "biologija/kviz"
    if not is_legacy_quiz(folder):
        pytest.skip("biologija missing")
    cfg = toml({"J": "Једноћелијски организми", "V": "Вегетативни органи биљака", "R": "Размножавање и раст биљака",
                "T": "Тест са стр. 72–73"}, "count = 20",
               'language = "sr-Cyrl"\ncyrillic_only = true\nlatin_allowed = ["n"]')
    res = render(build_legacy(tmp_path, folder, cfg))
    assert res.startswith("SELFTEST OK modes=3 sim=20") and "img=1" in res


def test_render_check_makes_no_network_requests(tmp_path):
    import http.server
    import threading
    calls = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            calls.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        page = tmp_path / "network.html"
        page.write_text(f'<body><img src="http://localhost:{port}/a.png">'
                        f'<link rel="stylesheet" href="http://quiz.localhost:{port}/b.css">'
                        "<script>const p = document.createElement('pre'); p.id = 'selftest';"
                        "p.textContent = 'SELFTEST OK'; document.body.appendChild(p);</script></body>",
                        encoding="utf-8")
        assert render(page) == "SELFTEST OK"
    finally:
        srv.shutdown()
    assert calls == []


def test_comment_script_text_still_plays(tmp_path):
    quiz = load_quiz(MINI)
    quiz.bank[-1]["q"] = "XSS primer: <!--<script> Glavni grad Srbije je:"
    quiz.bank[-1]["opts"][1]["why"] = "P1 <!--<script>alert(1)</script>"
    out = tmp_path / "k.html"
    out.write_text(build_html(quiz.cfg, quiz.bank, quiz.folder), encoding="utf-8")
    assert render(out).startswith("SELFTEST OK")


@pytest.mark.parametrize("lang, n, text", [
    ("ru", 21, "21 случайный вопрос"), ("ru", 22, "22 случайных вопроса"), ("ru", 25, "25 случайных вопросов"),
    ("sr-Latn", 21, "21 nasumično pitanje"), ("sr-Latn", 22, "22 nasumična pitanja"),
    ("sr-Latn", 11, "11 nasumičnih pitanja"), ("en", 1, "1 random question"), ("en", 2, "2 random questions")])
def test_plural_forms_in_subtitle(tmp_path, lang, n, text):
    q = copy_quiz(MINI, tmp_path / "q")
    s = (q / "quiz.toml").read_text(encoding="utf-8")
    s = s.replace('language = "sr-Latn"', f'language = "{lang}"').replace("count = 3", f"count = {n}")
    (q / "quiz.toml").write_text(s.replace("pass_mark = 2\n", ""), encoding="utf-8")
    dom = dump_dom(build_quiz(tmp_path, q))
    m = re.search(r'id="simDesc"[^>]*>([^<]*)<', dom)
    assert m and m.group(1).startswith(text + ","), m and m.group(1)


@pytest.mark.parametrize("lang", ["en", "sr-Latn", "sr-Cyrl", "ru"])
def test_selftest_each_default_language(tmp_path, lang):
    q = copy_quiz(MINI, tmp_path / "q")
    s = (q / "quiz.toml").read_text(encoding="utf-8").replace('language = "sr-Latn"', f'language = "{lang}"')
    (q / "quiz.toml").write_text(s, encoding="utf-8")
    assert render(build_quiz(tmp_path, q)).startswith("SELFTEST OK modes=3 sim=3")


def test_selftest_reports_languages(tmp_path):
    out = build_quiz(tmp_path, MINI)
    res = render(out)
    assert res.startswith("SELFTEST OK") and " langs=4" in res, res
    assert render(out, nostorage=True).startswith("SELFTEST OK")


def test_switcher_markup(tmp_path):
    dom = dump_dom(build_quiz(tmp_path, MINI))
    assert re.search(r'<select[^>]*id="langPick"', dom)
    assert re.findall(r'<option value="([^"]+)"', dom) == ["en", "sr-Latn", "sr-Cyrl", "ru"]
    assert re.search(r'<option value="sr-Latn"[^>]*selected', dom)
