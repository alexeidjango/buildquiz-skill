import shutil
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).parent
ENGINE = TESTS.parent
SKILL = ENGINE.parent
REPO = ENGINE.parents[3]  # the project root (the folder holding .claude/)
FIXTURES = TESTS / "fixtures"
MINI = FIXTURES / "mini"
MINI_CYR = FIXTURES / "mini_cyr"

sys.dont_write_bytecode = True
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))


def copy_quiz(src: Path, dst: Path) -> Path:
    """Copy a fixture quiz to dst (without __pycache__) and return dst."""
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


def build_quiz(tmp_path: Path, folder: Path, cfg_path: Path | None = None, name: str = "quiz.html") -> Path:
    """Load a quiz folder, build it into a temp folder with a non-ASCII name, return the page path."""
    from build import build_html
    from load import load_quiz
    quiz = load_quiz(folder, cfg_path)
    out = tmp_path / "š folder" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(quiz.cfg, quiz.bank, quiz.folder), encoding="utf-8")
    return out


def build_mini(tmp_path: Path) -> Path:
    return build_quiz(tmp_path, MINI)


@pytest.fixture
def mini_copy(tmp_path):
    return copy_quiz(MINI, tmp_path / "mini")
