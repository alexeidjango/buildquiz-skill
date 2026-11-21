import re

from conftest import SKILL, build_quiz
from check import check
from load import load_quiz
from render_check import dump_dom, render

DEMO = SKILL / "examples" / "demo-quiz"


def test_demo_quiz_checks_clean():
    quiz = load_quiz(DEMO)
    assert check(quiz) == []
    assert len(quiz.bank) >= 15 and len(quiz.cfg["areas"]) == 3
    assert any(p.get("img") for p in quiz.bank)
    assert any(p["multi"] for p in quiz.bank) and any(p.get("off_source") for p in quiz.bank)


def test_demo_quiz_selftest(tmp_path):
    res = render(build_quiz(tmp_path, DEMO))
    assert res.startswith("SELFTEST OK") and "img=1" in res and "langs=4" in res, res


def test_shot_states(tmp_path):
    out = build_quiz(tmp_path, DEMO)
    dom = dump_dom(out, "#shot=question&lang=ru")
    assert re.search(r'<div class="explain no">', dom), "no explanation of a wrong answer"
    assert re.search(r'<div class="head"><span lang="ru">', dom)
    assert re.search(r'<figure class="qimg">', dom)
    dom = dump_dom(out, "#shot=results")
    m = re.search(r'class="score-big [a-z]+">(\d+) / (\d+)<', dom)
    assert m and (m.group(1), m.group(2)) == ("8", "10"), m and m.groups()
    dom = dump_dom(out, "#shot=start&theme=dark")
    assert 'data-theme="dark"' in dom and not re.search(r'id="setup"[^>]*class="[^"]*hide', dom)
