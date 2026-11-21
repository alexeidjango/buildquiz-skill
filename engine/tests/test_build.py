import html.parser
import io
import json
import re
import subprocess
import sys
import tokenize

import pytest

from conftest import ENGINE, MINI, MINI_CYR, SKILL, copy_quiz
from build import build_html, sim_desc
from load import load_quiz

BUILD = ENGINE / "build.py"
TEMPLATE = (ENGINE / "template.html").read_text(encoding="utf-8") if (ENGINE / "template.html").exists() else ""


def build(folder=MINI):
    quiz = load_quiz(folder)
    return build_html(quiz.cfg, quiz.bank, quiz.folder), quiz


def script(out, name):
    m = re.search(r'<script id="' + name + r'" type="application/json">\n(.*?)\n</script>', out, re.S)
    return json.loads(m.group(1))


def test_no_placeholder_left():
    out, _ = build()
    without_bank = re.sub(r'<script id="(bank|images)".*?</script>', "", out, flags=re.S)
    assert not re.search(r"__[A-Z_]+__", without_bank)


def test_area_buttons():
    out, _ = build()
    group = re.search(r'<div class="choicegrid two" id="areaPick">(.*?)</div>', out, re.S).group(1)
    assert len(re.findall(r"data-val=", group)) == 3
    assert 'data-val="all"' in group and "Prva oblast" in group and "Druga oblast" in group
    assert 'id="cntA"' in group and 'id="cntB"' in group


def test_cfg_json_roundtrip():
    out, _ = build()
    cfg = json.loads(re.search(r"const CFG = (.*?);\n", out).group(1))
    assert cfg["passMark"] == 2 and cfg["count"] == 3 and cfg["mix"] is None
    assert cfg["offSourceLabel"] == "van slajdova" and cfg["language"] == "sr-Latn"
    assert cfg["storageKey"] == "mini-v1"
    assert cfg["areas"] == {"A": "Prva oblast", "B": "Druga oblast"}


def test_bank_json_roundtrip():
    out, quiz = build()
    assert script(out, "bank") == quiz.bank
    assert len(quiz.bank) == 4


def test_hostile_text_is_escaped(tmp_path):
    quiz = load_quiz(MINI)
    evil = '</script><b>&"'
    p = quiz.bank[-1]
    p["q"] = "Pitanje " + evil
    p["opts"][1]["t"] = "Opcija " + evil
    p["opts"][1]["why"] = "P1 " + evil
    quiz.cfg["intro"] = "a < b & c"
    quiz.cfg["areas"]["B"] = "Druga " + evil
    out = build_html(quiz.cfg, quiz.bank, quiz.folder)
    assert script(out, "bank") == quiz.bank
    assert out.count("</script>") == TEMPLATE.count("</script>")
    assert "</script><b>" not in out
    assert "a &lt; b &amp; c" in out


def test_sim_desc_count():
    cfg = {"language": "sr-Latn", "areas": {"A": "X", "B": "Y"}, "simulation": {"count": 30, "pass_mark": 15}}
    assert sim_desc(cfg) == "30 nasumičnih pitanja, prolaz 15, rezultat na kraju"


def test_sim_desc_mix():
    cfg = {"language": "sr-Latn", "areas": {"A": "Prva oblast", "B": "Druga oblast"},
           "simulation": {"mix": {"B": 1, "A": 2}, "pass_mark": 2}}
    assert sim_desc(cfg) == "3 pitanja: 2 prva oblast + 1 druga oblast, prolaz 2, rezultat na kraju"


def test_sim_desc_learning():
    assert sim_desc(load_quiz(MINI_CYR).cfg) == "3 насумична питања, резултат на крају"
    cfg = {"language": "sr-Cyrl", "areas": {"A": "X", "B": "Y"}, "simulation": {"count": 21}}
    assert sim_desc(cfg) == "21 насумично питање, резултат на крају"
    cfg = {"language": "sr-Latn", "areas": {"A": "X", "B": "Y"}, "simulation": {"count": 12}}
    assert sim_desc(cfg) == "12 nasumičnih pitanja, rezultat na kraju"


def test_cli_writes_out(tmp_path):
    out = tmp_path / "x.html"
    r = subprocess.run([sys.executable, BUILD, str(MINI), "--out", str(out)],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    assert out.exists() and "built: 4 questions" in r.stdout


def test_pictures_embedded(tmp_path):
    out, _ = build()
    pictures = script(out, "images")
    assert list(pictures) == ["A_picture"] and pictures["A_picture"].startswith("data:image/jpeg;base64,")
    q = copy_quiz(MINI, tmp_path / "q")
    (q / "images" / "A_picture.jpg").unlink()
    quiz = load_quiz(q)
    with pytest.raises(Exception, match="A_picture"):
        build_html(quiz.cfg, quiz.bank, quiz.folder)


class _Text(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.in_script += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.in_script -= 1

    def handle_data(self, data):
        if not self.in_script:
            self.parts.append(data)


def test_cyrillic_ui_has_no_latin():
    out, _ = build(MINI_CYR)
    p = _Text()
    p.feed(out)
    text = " ".join(p.parts)
    cyr = re.search(r"/\*T\.sr-Cyrl\*/ 'sr-Cyrl': \{(.*?)/\*T\.sr-Cyrl end\*/", out, re.S).group(1)
    strings = " ".join(re.findall(r"'((?:[^'\\]|\\.)*)'", cyr))
    lat = re.findall(r"[A-Za-zČčĆćŠšĐđŽž]{3,}", text + " " + strings)
    assert lat == [], lat
    assert 'lang="sr-Cyrl"' in out


# Old Serbian names that must not come back (tests/legacy.py, which reads the author's old quizzes, is exempt).
OLD = re.compile(r"\b(banka|ucitaj|provera|izgradi|pregled|citaj|sablon|termini|kljuc|oblasti?|naslov|podnaslov|"
                 r"uvod|izlaz|izvor|pismo|prolaz|sastav|simulacija|slike|GREŠKA|ČITAJ|_tekst|kviz)\w*", re.I)
FILE_LIKE = re.compile(r"^--?\w[\w-]*$|\.(py|toml|json|html|jpg)$")


def _names_py(src: str):
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type in (tokenize.NAME, tokenize.COMMENT):
            yield tok.start[0], tok.string
        elif tok.type == tokenize.STRING:
            body = re.sub(r"^[rbfuRBFU]*('''|\"\"\"|'|\")|('''|\"\"\"|'|\")$", "", tok.string)
            if FILE_LIKE.search(body):
                yield tok.start[0], body


def _names_toml(src: str):
    for n, line in enumerate(src.splitlines(), 1):
        m = re.match(r"\s*\[([^\]]+)\]|\s*([\w.-]+)\s*=", line)
        if m:
            yield n, m.group(1) or m.group(2)


def _names_html(src: str):
    for n, line in enumerate(src.splitlines(), 1):
        yield n, re.sub(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\]|\\.)*`", "", line)
        for m in re.finditer(r'\b(?:id|class|data-[\w-]+)="([^"]*)"', line):
            yield n, m.group(1)


def test_no_old_names_in_repo():
    hits = []
    for p in sorted(SKILL.rglob("*")):
        if not p.is_file() or ".git" in p.parts or ".superpowers" in p.parts or "__pycache__" in p.parts:
            continue
        if p.name == "legacy.py":
            continue
        src = p.read_text(encoding="utf-8", errors="replace")
        names = {".py": _names_py, ".toml": _names_toml, ".html": _names_html}.get(p.suffix)
        if names is None:
            continue
        for n, name in names(src):
            if p.name == "test_build.py" and "OLD = re.compile" in src.splitlines()[n - 1]:
                continue
            for m in OLD.finditer(name):
                hits.append(f"{p.relative_to(SKILL)}:{n}: {m.group(0)}")
    assert hits == []
