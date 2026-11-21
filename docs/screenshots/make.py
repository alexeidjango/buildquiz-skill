"""Regenerate the README screenshots from the demo quiz (examples/demo-quiz), at iPhone size.

Usage: python docs/screenshots/make.py   (from the skill folder; needs Edge, like render_check.py)
Builds the demo into a temp folder, opens it headless with #shot=... states and the same no-network flags as
the render check, and saves docs/screenshots/<state>-<theme>.jpg plus start-sr-Cyrl.jpg.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
SKILL = HERE.parents[1]
ENGINE = SKILL / "engine"
sys.path.insert(0, str(ENGINE))
sys.dont_write_bytecode = True

from build import build_html  # noqa: E402
from load import load_quiz  # noqa: E402
from render_check import NO_NETWORK, _browser  # noqa: E402

WIDTH, HEIGHT, SCALE = 390, 844, 2  # iPhone 12-15 screen in CSS pixels
SHOTS = [(f"{state}-{theme}", f"shot={state}&theme={theme}")
         for theme in ("light", "dark") for state in ("start", "question", "results")]
SHOTS.append(("start-sr-Cyrl", "shot=start&theme=light&lang=sr-Cyrl"))


FRAME = """<!doctype html><meta charset="utf-8"><style>html,body{margin:0;background:#000}</style>
<iframe src="{src}" style="width:{w}px;height:{h}px;border:0;display:block"></iframe>"""


def shoot(page: Path, fragment: str, png: Path) -> None:
    # Edge on Windows will not lay out a window narrower than about 500 px, so the quiz runs in an iframe of
    # exactly the phone's size inside a wider window, and the shot is cropped to the iframe.
    frame = page.with_name("frame.html")
    frame.write_text(FRAME.replace("{src}", page.name + "#" + fragment).replace("{w}", str(WIDTH))
                     .replace("{h}", str(HEIGHT)), encoding="utf-8")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        subprocess.run([str(_browser()), "--headless=new", "--disable-gpu", "--no-first-run",
                        "--no-default-browser-check", f"--user-data-dir={profile}", *NO_NETWORK,
                        f"--window-size={WIDTH + 300},{HEIGHT}", f"--force-device-scale-factor={SCALE}",
                        "--hide-scrollbars", "--virtual-time-budget=3000", f"--screenshot={png}",
                        frame.resolve().as_uri()],
                       capture_output=True, timeout=180, check=True)
    with Image.open(png) as im:
        im.crop((0, 0, WIDTH * SCALE, HEIGHT * SCALE)).save(png)


def main() -> int:
    quiz = load_quiz(SKILL / "examples" / "demo-quiz")
    with tempfile.TemporaryDirectory() as tmp:
        page = Path(tmp) / "demo.html"
        page.write_text(build_html(quiz.cfg, quiz.bank, quiz.folder), encoding="utf-8")
        total = 0
        for name, fragment in SHOTS:
            png = Path(tmp) / f"{name}.png"
            shoot(page, fragment, png)
            out = HERE / f"{name}.jpg"
            with Image.open(png) as im:
                im.convert("RGB").save(out, "JPEG", quality=82, optimize=True, progressive=True)
            total += out.stat().st_size
            print(out.name, f"{out.stat().st_size // 1024} KB")
    print(f"total {total // 1024} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
