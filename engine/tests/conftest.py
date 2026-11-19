import shutil
import sys
from pathlib import Path

import pytest

TESTS = Path(__file__).parent
ENGINE = TESTS.parent
REPO = ENGINE.parents[3]  # the project root (the folder holding .claude/)
FIXTURES = TESTS / "fixtures"
MINI = FIXTURES / "mini"
MINI_CYR = FIXTURES / "mini_cyr"

sys.dont_write_bytecode = True
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))


def kopija(src: Path, dst: Path) -> Path:
    """Copy a fixture quiz to dst (without __pycache__) and return dst."""
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
    return dst


@pytest.fixture
def mini_kopija(tmp_path):
    return kopija(MINI, tmp_path / "mini")
