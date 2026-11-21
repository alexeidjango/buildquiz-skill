"""Extract text from a folder of course materials into <folder>/_text/, one .txt per source file.

Usage: python read_sources.py <source-folder>          extract; list images Claude must read (READ lines)
       python read_sources.py <source-folder> --terms  print a first TERMS block from **bold** words in _text/

PDF (text per page, scanned pages rendered), docx, pptx (text per slide, pictures of near-empty slides),
txt/md (copied), jpg/png (upright preview + full-resolution top/bottom halves), heic/heif (converted first).
A .txt newer than its source is never rewritten, so transcriptions survive reruns.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageOps

PLACEHOLDER = "[TO READ: {image}]"
HEIC_ERROR = "[HEIC NOT CONVERTED: {file}]"
PREVIEW_MAX = 1600  # the preview fits 1600x1600; pictures.py coordinates are in this space
HALF = 0.55  # _a = top 55 %, _b = bottom 55 % of the full-resolution page
IMAGES = {".jpg", ".jpeg", ".png"}
HEIC = {".heic", ".heif"}
SKIP_FILES = {"desktop.ini", "thumbs.db"}
NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

_PS_HEIC = r"""
Add-Type -AssemblyName PresentationCore
$in = [IO.File]::OpenRead($env:BUILDQUIZ_SRC)
try {
  $dec = [Windows.Media.Imaging.BitmapDecoder]::Create($in, 'None', 'OnLoad')
  $enc = New-Object Windows.Media.Imaging.JpegBitmapEncoder
  $enc.QualityLevel = 92
  $enc.Frames.Add($dec.Frames[0])
  $out = [IO.File]::Create($env:BUILDQUIZ_DST); try { $enc.Save($out) } finally { $out.Close() }
} finally { $in.Close() }
"""


@dataclass
class Report:
    new: list[Path] = field(default_factory=list)
    skipped: list[Path] = field(default_factory=list)
    to_read: list[tuple[Path, Path]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def heic_to_jpg(src: Path, dst: Path) -> None:
    """Convert HEIC/HEIF to JPEG with the Windows imaging component (no installs). Raises RuntimeError."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, BUILDQUIZ_SRC=str(src), BUILDQUIZ_DST=str(dst))  # paths go in as data, never as code
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_HEIC], env=env,
                       capture_output=True, text=True, errors="replace", timeout=120)
    if r.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
        dst.unlink(missing_ok=True)
        raise RuntimeError((r.stderr or r.stdout).strip()[-1500:] or f"exit {r.returncode}")


def _pages(image: Image.Image, base: Path) -> list[Path]:
    """Write the upright preview <base>.jpg and the halves <base>_a.jpg / _b.jpg. Returns the three paths."""
    base.parent.mkdir(parents=True, exist_ok=True)
    image = image.convert("RGB")
    w, h = image.size
    half = round(h * HALF)
    preview = image.copy()
    preview.thumbnail((PREVIEW_MAX, PREVIEW_MAX))
    paths = [base.with_name(base.name + s) for s in (".jpg", "_a.jpg", "_b.jpg")]
    preview.save(paths[0], "JPEG", quality=90)
    image.crop((0, 0, w, half)).save(paths[1], "JPEG", quality=90)
    image.crop((0, h - half, w, h)).save(paths[2], "JPEG", quality=90)
    return paths


def _marker(text_dir: Path, paths: list[Path]) -> str:
    return PLACEHOLDER.format(image=" | ".join(p.relative_to(text_dir).as_posix() for p in paths))


def _pdf(src: Path, base: Path, text_dir: Path, min_chars: int) -> str:
    import pdfplumber
    lines = []
    with pdfplumber.open(src) as pdf:
        for n, page in enumerate(pdf.pages, 1):
            t = page.extract_text() or ""
            lines.append(f"=== p{n}")
            if t.strip():
                lines.append(t)
            if len(re.sub(r"\s", "", t)) < min_chars:
                image = page.to_image(resolution=150).original
                b = base.with_name(f"{base.name}_p{n}")
                b.parent.mkdir(parents=True, exist_ok=True)
                image.save(b.with_name(b.name + ".png"))  # full render: the source image for pictures.py
                lines.append(_marker(text_dir, _pages(image, b)))
    return "\n".join(lines)


def _docx(src: Path) -> str:
    with zipfile.ZipFile(src) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    paragraphs = ("".join(t.text or "" for t in p.iter(NS_W + "t")) for p in root.iter(NS_W + "p"))
    return "\n".join(p for p in paragraphs if p.strip())


def _pptx(src: Path, base: Path, text_dir: Path, min_chars: int) -> str:
    lines = []
    with zipfile.ZipFile(src) as z:
        names = set(z.namelist())
        slides = sorted((int(m.group(1)), name) for name in names
                        if (m := re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name)))
        for n, name in slides:
            root = ET.fromstring(z.read(name))
            paragraphs = ["".join(t.text or "" for t in p.iter(NS_A + "t")) for p in root.iter(NS_A + "p")]
            t = "\n".join(p for p in paragraphs if p.strip())
            lines.append(f"=== s{n}")
            if t:
                lines.append(t)
            rels = f"ppt/slides/_rels/slide{n}.xml.rels"
            if len(re.sub(r"\s", "", t)) < min_chars and rels in names:
                for rel in ET.fromstring(z.read(rels)):
                    target = rel.get("Target", "")
                    if not rel.get("Type", "").endswith("/image"):
                        continue
                    media = "ppt/" + target.replace("../", "", 1) if target.startswith("../") else target.lstrip("/")
                    if media not in names:
                        continue
                    dst = base.with_name(f"{base.name}_s{n}_{Path(media).name}")
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(z.read(media))
                    lines.append(_marker(text_dir, [dst]))
    return "\n".join(lines)


def _image(src: Path, base: Path, text_dir: Path) -> str:
    with Image.open(src) as im:
        upright = ImageOps.exif_transpose(im)
        return _marker(text_dir, _pages(upright, base))


def _sources(folder: Path):
    for root, dirs, files in os.walk(folder):
        root = Path(root)
        dirs[:] = sorted(d for d in dirs if not (d.startswith((".", "_")) or d == "__pycache__"
                                                  or (root / d / "quiz.toml").exists()
                                                  or (root / d / "bank.py").exists()))
        for f in sorted(files):
            if not f.startswith(".") and f.lower() not in SKIP_FILES:
                yield root / f


def read_sources(folder: Path, min_chars: int = 40) -> Report:
    """Extract every source under folder into folder/_text/. See the module docstring."""
    folder = Path(folder)
    text_dir = folder / "_text"
    pages_dir = text_dir / "_pages"
    report = Report()
    reported = set()
    sources = list(_sources(folder))
    stems = {}
    for s in sources:
        stems[(s.parent, s.stem.lower())] = stems.get((s.parent, s.stem.lower()), 0) + 1
    for src in sources:
        rel = src.relative_to(folder)
        txt = text_dir / rel.parent / (rel.name + ".txt")
        ext = src.suffix.lower()
        # IMG_1.JPG next to IMG_1.png: page images must not overwrite each other, so add the extension
        name = src.stem if stems[(src.parent, src.stem.lower())] == 1 else f"{src.stem}_{ext[1:]}"
        base = pages_dir / rel.parent / name
        if ext not in {".pdf", ".docx", ".pptx", ".txt", ".md"} | IMAGES | HEIC:
            report.errors.append(f"{rel}: unsupported file type {ext or '(none)'}")
            continue
        if txt.exists() and txt.stat().st_mtime >= src.stat().st_mtime:
            report.skipped.append(src)
            continue
        try:
            if ext == ".pdf":
                content = _pdf(src, base, text_dir, min_chars)
            elif ext == ".docx":
                content = _docx(src)
            elif ext == ".pptx":
                content = _pptx(src, base, text_dir, min_chars)
            elif ext in (".txt", ".md"):
                content = src.read_text(encoding="utf-8", errors="replace")
            elif ext in IMAGES:
                content = _image(src, base, text_dir)
            else:
                converted = base.with_name(base.name + "_heic.jpg")
                try:
                    heic_to_jpg(src, converted)
                    content = _image(converted, base, text_dir)
                except RuntimeError as e:
                    content = HEIC_ERROR.format(file=rel.as_posix())
                    report.errors.append(f"{rel}: HEIC not converted: {e}")
                    reported.add(txt)
        except Exception as e:  # noqa: BLE001 - a broken source is reported, the others still run
            report.errors.append(f"{rel}: {type(e).__name__}: {e}")
            continue
        txt.parent.mkdir(parents=True, exist_ok=True)
        if txt.exists():
            old = txt.read_text(encoding="utf-8", errors="replace")
            if old.count("[TO READ:") < content.count("[TO READ:"):
                # The old .txt holds transcriptions (placeholders were replaced): never overwrite them.
                newer = txt.with_name(txt.name + ".new")
                newer.write_text(content + "\n", encoding="utf-8")
                report.errors.append(f"{rel}: source changed after it was transcribed; the transcription is kept "
                                     f"in {txt.name}, the new extraction is in {newer.name}: compare and merge by hand")
                continue
        txt.write_text(content + "\n", encoding="utf-8")
        report.new.append(src)

    if text_dir.exists():
        for txt in sorted(text_dir.rglob("*.txt")):
            if pages_dir in txt.parents:
                continue
            s = txt.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"\[TO READ: ([^\]]+)\]", s):
                report.to_read.append((txt, text_dir / m.group(1).split(" | ")[0]))
            if "[HEIC NOT CONVERTED" in s and txt not in reported:
                report.errors.append(f"{txt.relative_to(text_dir)}: HEIC not converted (from an earlier run)")
    return report


def suggest_terms(text_folder: Path) -> dict[str, str]:
    """Every **bold** phrase in the transcriptions (outside the NOTES section) -> a stem regex."""
    terms = {}
    for txt in sorted(Path(text_folder).rglob("*.txt")):
        skip = False
        for line in txt.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(("--- ", "=== ")):
                skip = line.startswith("--- NOTES")
                continue
            if skip:
                continue
            for m in re.finditer(r"\*\*(.+?)\*\*", line):
                name = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(":;,.").strip()
                if not name or name.lower() in {k.lower() for k in terms}:
                    continue
                words = [re.escape(w[:-2] if len(w) >= 6 else w[:-1] if len(w) >= 4 else w) for w in name.split(" ")]
                terms[name] = r"\w*\s+".join(words)
    return terms


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Extract course materials into <folder>/_text/.")
    ap.add_argument("folder", type=Path, help="source folder (slides, keys, photos, ...)")
    ap.add_argument("--terms", action="store_true", help="print a TERMS block from **bold** words in _text/")
    ap.add_argument("--min-chars", type=int, default=40,
                    help="a PDF page/slide with fewer characters is read as a picture")
    a = ap.parse_args(argv)
    if a.terms:
        print("TERMS = {")
        for name, rx in suggest_terms(a.folder / "_text").items():
            print(f"    {json.dumps(name, ensure_ascii=False)}: r\"{rx}\",")
        print("}")
        return 0
    report = read_sources(a.folder, a.min_chars)
    print(f"new: {len(report.new)} | skipped: {len(report.skipped)} | to read: {len(report.to_read)}"
          f" | errors: {len(report.errors)}")
    for txt, image in report.to_read:
        print(f"READ {txt} <- {image}")
    for e in report.errors:
        print(f"ERROR {e}")
    return 1 if report.errors else 0


if __name__ == "__main__":
    sys.exit(main())
