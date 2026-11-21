"""Render check: open a built quiz in headless Edge with #selftest and read the self-test result.

Usage: python render_check.py <built.html>
Runs the normal and the no-localStorage variant; exit 0 only if both print SELFTEST OK.
"""
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BROWSERS = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
)


# No network from the render check (CLAUDE.md): every host name fails to resolve (Google Fonts falls back to
# system fonts, which also proves the quiz works offline), and the browser's own background traffic is off.
NO_NETWORK = ("--host-resolver-rules=MAP * ~NOTFOUND", "--disable-background-networking",
             "--disable-component-update", "--no-pings", "--disable-sync", "--disable-domain-reliability")


def _browser() -> Path:
    for p in BROWSERS:
        if p.exists():
            return p
    raise RuntimeError("no Edge or Chrome found at: " + ", ".join(map(str, BROWSERS)))


def _run(html_path: Path, fragment: str) -> subprocess.CompletedProcess:
    uri = Path(html_path).resolve().as_uri() + fragment
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as profile:
        return subprocess.run(
            [str(_browser()), "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
             f"--user-data-dir={profile}", *NO_NETWORK, "--virtual-time-budget=5000", "--dump-dom", uri],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)


def dump_dom(html_path: Path, fragment: str = "") -> str:
    """The page's DOM after its scripts ran, opened with an optional #fragment."""
    return _run(html_path, fragment).stdout


def render(html_path: Path, nostorage: bool = False) -> str:
    """The self-test result line, e.g. "SELFTEST OK modes=3 sim=30 img=0 code=0" or "SELFTEST FAIL <step>: ...".

    Raises RuntimeError (with the browser's stderr) when the page produced no result line, twice: headless Edge
    rarely dumps the page before the asynchronous self-test has written its line (about 1 load in 500), so a
    missing line gets one more run. A SELFTEST FAIL line is never retried."""
    for _ in range(2):
        r = _run(html_path, "#selftest-nostorage" if nostorage else "#selftest")
        m = re.search(r'<pre id="selftest">(.*?)</pre>', r.stdout, re.S)
        if m:
            break
    if not m:
        raise RuntimeError(f"no self-test result in the page (exit {r.returncode}): {r.stderr[-2000:]}")
    return html.unescape(m.group(1)).strip()


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 2
    ok = True
    for nostorage in (False, True):
        try:
            res = render(Path(argv[0]), nostorage)
        except RuntimeError as e:
            res = f"SELFTEST FAIL browser: {e}"
        print(("nostorage: " if nostorage else "normal:    ") + res)
        ok = ok and res.startswith("SELFTEST OK")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
