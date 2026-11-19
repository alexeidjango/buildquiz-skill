"""Extract text from a folder of course materials into <folder>/_tekst/, one .txt per source file.

Usage: python citaj.py <source-folder>            extract; list images Claude must read (ČITAJ lines)
       python citaj.py <source-folder> --termini  print a first TERMINI block from **bold** words in _tekst/

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

PLACEHOLDER = "[ZA ČITANJE: {slika}]"
HEIC_GRESKA = "[HEIC NIJE KONVERTOVAN: {fajl}]"
PREGLED_MAX = 1600  # the preview fits 1600x1600; slike.py coordinates are in this space
POLOVINA = 0.55  # _a = top 55 %, _b = bottom 55 % of the full-resolution page
SLIKE = {".jpg", ".jpeg", ".png"}
HEIC = {".heic", ".heif"}
PRESKOCI_FAJLOVE = {"desktop.ini", "thumbs.db"}
NS_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NS_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"

_PS_HEIC = r"""
Add-Type -AssemblyName PresentationCore
$in = [IO.File]::OpenRead($env:CITAJ_SRC)
try {
  $dec = [Windows.Media.Imaging.BitmapDecoder]::Create($in, 'None', 'OnLoad')
  $enc = New-Object Windows.Media.Imaging.JpegBitmapEncoder
  $enc.QualityLevel = 92
  $enc.Frames.Add($dec.Frames[0])
  $out = [IO.File]::Create($env:CITAJ_DST); try { $enc.Save($out) } finally { $out.Close() }
} finally { $in.Close() }
"""


@dataclass
class Izvestaj:
    novi: list[Path] = field(default_factory=list)
    preskoceni: list[Path] = field(default_factory=list)
    za_citanje: list[tuple[Path, Path]] = field(default_factory=list)
    greske: list[str] = field(default_factory=list)


def heic_u_jpg(src: Path, dst: Path) -> None:
    """Convert HEIC/HEIF to JPEG with the Windows imaging component (no installs). Raises RuntimeError."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, CITAJ_SRC=str(src), CITAJ_DST=str(dst))  # paths go in as data, never as code
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_HEIC], env=env,
                       capture_output=True, text=True, errors="replace", timeout=120)
    if r.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
        dst.unlink(missing_ok=True)
        raise RuntimeError((r.stderr or r.stdout).strip()[-1500:] or f"exit {r.returncode}")


def _strane(slika: Image.Image, osnova: Path) -> list[Path]:
    """Write the upright preview <osnova>.jpg and the halves <osnova>_a.jpg / _b.jpg. Returns the three paths."""
    osnova.parent.mkdir(parents=True, exist_ok=True)
    slika = slika.convert("RGB")
    w, h = slika.size
    pola = round(h * POLOVINA)
    pregled = slika.copy()
    pregled.thumbnail((PREGLED_MAX, PREGLED_MAX))
    putevi = [osnova.with_name(osnova.name + s) for s in (".jpg", "_a.jpg", "_b.jpg")]
    pregled.save(putevi[0], "JPEG", quality=90)
    slika.crop((0, 0, w, pola)).save(putevi[1], "JPEG", quality=90)
    slika.crop((0, h - pola, w, h)).save(putevi[2], "JPEG", quality=90)
    return putevi


def _oznaka(tekst_dir: Path, putevi: list[Path]) -> str:
    return PLACEHOLDER.format(slika=" | ".join(p.relative_to(tekst_dir).as_posix() for p in putevi))


def _pdf(src: Path, osnova: Path, tekst_dir: Path, prag: int) -> str:
    import pdfplumber
    redovi = []
    with pdfplumber.open(src) as pdf:
        for n, strana in enumerate(pdf.pages, 1):
            t = strana.extract_text() or ""
            redovi.append(f"=== p{n}")
            if t.strip():
                redovi.append(t)
            if len(re.sub(r"\s", "", t)) < prag:
                slika = strana.to_image(resolution=150).original
                b = osnova.with_name(f"{osnova.name}_p{n}")
                b.parent.mkdir(parents=True, exist_ok=True)
                slika.save(b.with_name(b.name + ".png"))  # full render: the source image for slike.py
                redovi.append(_oznaka(tekst_dir, _strane(slika, b)))
    return "\n".join(redovi)


def _docx(src: Path) -> str:
    with zipfile.ZipFile(src) as z:
        koren = ET.fromstring(z.read("word/document.xml"))
    pasusi = ("".join(t.text or "" for t in p.iter(NS_W + "t")) for p in koren.iter(NS_W + "p"))
    return "\n".join(p for p in pasusi if p.strip())


def _pptx(src: Path, osnova: Path, tekst_dir: Path, prag: int) -> str:
    redovi = []
    with zipfile.ZipFile(src) as z:
        imena = set(z.namelist())
        slajdovi = sorted((int(m.group(1)), ime) for ime in imena
                          if (m := re.fullmatch(r"ppt/slides/slide(\d+)\.xml", ime)))
        for n, ime in slajdovi:
            koren = ET.fromstring(z.read(ime))
            pasusi = ["".join(t.text or "" for t in p.iter(NS_A + "t")) for p in koren.iter(NS_A + "p")]
            t = "\n".join(p for p in pasusi if p.strip())
            redovi.append(f"=== s{n}")
            if t:
                redovi.append(t)
            rels = f"ppt/slides/_rels/slide{n}.xml.rels"
            if len(re.sub(r"\s", "", t)) < prag and rels in imena:
                for rel in ET.fromstring(z.read(rels)):
                    cilj = rel.get("Target", "")
                    if not rel.get("Type", "").endswith("/image"):
                        continue
                    media = "ppt/" + cilj.replace("../", "", 1) if cilj.startswith("../") else cilj.lstrip("/")
                    if media not in imena:
                        continue
                    dst = osnova.with_name(f"{osnova.name}_s{n}_{Path(media).name}")
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    dst.write_bytes(z.read(media))
                    redovi.append(_oznaka(tekst_dir, [dst]))
    return "\n".join(redovi)


def _slika(src: Path, osnova: Path, tekst_dir: Path) -> str:
    with Image.open(src) as im:
        uspravna = ImageOps.exif_transpose(im)
        return _oznaka(tekst_dir, _strane(uspravna, osnova))


def _izvori(folder: Path):
    for koren, dirs, fajlovi in os.walk(folder):
        koren = Path(koren)
        dirs[:] = sorted(d for d in dirs if not (d.startswith((".", "_")) or d == "__pycache__"
                                                  or (koren / d / "kviz.toml").exists()
                                                  or (koren / d / "banka.py").exists()))
        for f in sorted(fajlovi):
            if not f.startswith(".") and f.lower() not in PRESKOCI_FAJLOVE:
                yield koren / f


def citaj(folder: Path, prag: int = 40) -> Izvestaj:
    """Extract every source under folder into folder/_tekst/. See the module docstring."""
    folder = Path(folder)
    tekst_dir = folder / "_tekst"
    slike_dir = tekst_dir / "_slike"
    iz = Izvestaj()
    prijavljeni = set()
    izvori = list(_izvori(folder))
    stabla = {}
    for s in izvori:
        stabla[(s.parent, s.stem.lower())] = stabla.get((s.parent, s.stem.lower()), 0) + 1
    for src in izvori:
        rel = src.relative_to(folder)
        txt = tekst_dir / rel.parent / (rel.name + ".txt")
        ext = src.suffix.lower()
        # IMG_1.JPG next to IMG_1.png: page images must not overwrite each other, so add the extension
        ime = src.stem if stabla[(src.parent, src.stem.lower())] == 1 else f"{src.stem}_{ext[1:]}"
        osnova = slike_dir / rel.parent / ime
        if ext not in {".pdf", ".docx", ".pptx", ".txt", ".md"} | SLIKE | HEIC:
            iz.greske.append(f"{rel}: unsupported file type {ext or '(none)'}")
            continue
        if txt.exists() and txt.stat().st_mtime >= src.stat().st_mtime:
            iz.preskoceni.append(src)
            continue
        try:
            if ext == ".pdf":
                sadrzaj = _pdf(src, osnova, tekst_dir, prag)
            elif ext == ".docx":
                sadrzaj = _docx(src)
            elif ext == ".pptx":
                sadrzaj = _pptx(src, osnova, tekst_dir, prag)
            elif ext in (".txt", ".md"):
                sadrzaj = src.read_text(encoding="utf-8", errors="replace")
            elif ext in SLIKE:
                sadrzaj = _slika(src, osnova, tekst_dir)
            else:
                konvertovana = osnova.with_name(osnova.name + "_heic.jpg")
                try:
                    heic_u_jpg(src, konvertovana)
                    sadrzaj = _slika(konvertovana, osnova, tekst_dir)
                except RuntimeError as e:
                    sadrzaj = HEIC_GRESKA.format(fajl=rel.as_posix())
                    iz.greske.append(f"{rel}: HEIC not converted: {e}")
                    prijavljeni.add(txt)
        except Exception as e:  # noqa: BLE001 - a broken source is reported, the others still run
            iz.greske.append(f"{rel}: {type(e).__name__}: {e}")
            continue
        txt.parent.mkdir(parents=True, exist_ok=True)
        if txt.exists():
            staro = txt.read_text(encoding="utf-8", errors="replace")
            if staro.count("[ZA ČITANJE:") < sadrzaj.count("[ZA ČITANJE:"):
                # The old .txt holds transcriptions (placeholders were replaced): never overwrite them.
                novo = txt.with_name(txt.name + ".novo")
                novo.write_text(sadrzaj + "\n", encoding="utf-8")
                iz.greske.append(f"{rel}: source changed after it was transcribed; the transcription is kept in "
                                 f"{txt.name}, the new extraction is in {novo.name}: compare and merge by hand")
                continue
        txt.write_text(sadrzaj + "\n", encoding="utf-8")
        iz.novi.append(src)

    if tekst_dir.exists():
        for txt in sorted(tekst_dir.rglob("*.txt")):
            if slike_dir in txt.parents:
                continue
            s = txt.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r"\[ZA ČITANJE: ([^\]]+)\]", s):
                iz.za_citanje.append((txt, tekst_dir / m.group(1).split(" | ")[0]))
            if "[HEIC NIJE KONVERTOVAN" in s and txt not in prijavljeni:
                iz.greske.append(f"{txt.relative_to(tekst_dir)}: HEIC not converted (from an earlier run)")
    return iz


def predlozi_termine(tekst_folder: Path) -> dict[str, str]:
    """Every **bold** phrase in the transcriptions (outside НАПОМЕНЕ/NAPOMENE) -> a stem regex."""
    termini = {}
    for txt in sorted(Path(tekst_folder).rglob("*.txt")):
        preskoci = False
        for red in txt.read_text(encoding="utf-8", errors="replace").splitlines():
            if red.startswith(("--- ", "=== ")):
                preskoci = red.startswith(("--- НАПОМЕНЕ", "--- NAPOMENE"))
                continue
            if preskoci:
                continue
            for m in re.finditer(r"\*\*(.+?)\*\*", red):
                ime = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(":;,.").strip()
                if not ime or ime.lower() in {k.lower() for k in termini}:
                    continue
                reci = [re.escape(w[:-2] if len(w) >= 6 else w[:-1] if len(w) >= 4 else w) for w in ime.split(" ")]
                termini[ime] = r"\w*\s+".join(reci)
    return termini


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Extract course materials into <folder>/_tekst/.")
    ap.add_argument("folder", type=Path, help="source folder (slides, keys, photos, ...)")
    ap.add_argument("--termini", action="store_true", help="print a TERMINI block from **bold** words in _tekst/")
    ap.add_argument("--prag", type=int, default=40, help="a PDF page/slide with fewer characters is read as a picture")
    a = ap.parse_args(argv)
    if a.termini:
        print("TERMINI = {")
        for ime, rx in predlozi_termine(a.folder / "_tekst").items():
            print(f"    {json.dumps(ime, ensure_ascii=False)}: r\"{rx}\",")
        print("}")
        return 0
    iz = citaj(a.folder, a.prag)
    print(f"novi: {len(iz.novi)} | preskočeni: {len(iz.preskoceni)} | za čitanje: {len(iz.za_citanje)}"
          f" | greške: {len(iz.greske)}")
    for txt, slika in iz.za_citanje:
        print(f"ČITAJ {txt} <- {slika}")
    for g in iz.greske:
        print(f"GREŠKA {g}")
    return 1 if iz.greske else 0


if __name__ == "__main__":
    sys.exit(main())
