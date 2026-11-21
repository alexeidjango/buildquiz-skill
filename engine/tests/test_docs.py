import re
import tomllib

from conftest import ENGINE, SKILL
from load import validate_config

SKILL_MD = (SKILL / "SKILL.md").read_text(encoding="utf-8")
README = (SKILL / "README.md").read_text(encoding="utf-8")
EXAMPLE = SKILL / "reference" / "quiz.toml.example"


def test_example_config_loads():
    text = EXAMPLE.read_text(encoding="utf-8")
    cfg = validate_config(tomllib.loads(text))
    assert cfg["language"] and cfg["content_language"]
    for key in ("language", "content_language", "cyrillic_only", "latin_allowed", "off_source_label"):
        assert re.search(rf"^#? ?{key} =", text, re.M), key


def test_skill_md_commands_exist():
    for doc in (SKILL_MD, README):
        for name in re.findall(r"python E/(\w+)\.py", doc) + re.findall(r"engine/(\w+)\.py", doc):
            assert (ENGINE / f"{name}.py").exists(), name
        for name in re.findall(r"reference/([\w.-]+\w)", doc):
            assert (SKILL / "reference" / name).exists(), name


def test_checkpoint_asks_language():
    step3 = SKILL_MD[SKILL_MD.index("### 3."):SKILL_MD.index("### 4.")]
    assert "screen language" in step3 and "cyrillic_only" in step3
    for name in ("English", "Srpski", "Српски", "Русский"):
        assert name in step3, name


def test_readme_explains_adding_a_language():
    assert "## Adding a screen language" in README and "en.json" in README


def test_book_quizzes_set_off_source_label():
    steps = SKILL_MD[SKILL_MD.index("### 2."):SKILL_MD.index("### 4.")]
    assert "off_source_label" in steps and "book" in steps.lower()
