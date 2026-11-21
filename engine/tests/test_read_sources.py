import os
import shutil
import subprocess
import sys
import zipfile

import pytest
from PIL import Image, ImageDraw

from read_sources import PLACEHOLDER, read_sources, suggest_terms
from conftest import ENGINE, REPO

READ_SOURCES = ENGINE / "read_sources.py"


def jpg(path, w=400, h=300, orientation=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (w, h), "white")
    ImageDraw.Draw(im).rectangle((0, 0, w // 4, h // 4), fill="red")
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    im.save(path, "JPEG", exif=exif.tobytes())
    return path


def text(src, name):
    return (src / "_text" / name).read_text(encoding="utf-8")


def test_text_pdf(tmp_path):
    pdf = REPO / "zastitamreza/K1/03 Kontrola pristupa/03 Kontrola pristupa.pdf"
    if not pdf.exists():
        pytest.skip("ZRM sources missing")
    shutil.copy(pdf, tmp_path / pdf.name)
    report = read_sources(tmp_path)
    t = text(tmp_path, pdf.name + ".txt")
    assert "=== p1" in t and "Kontrola pristupa" in t
    assert report.new == [tmp_path / pdf.name]
    assert all(txt.name == pdf.name + ".txt" for txt, _ in report.to_read)


def test_scanned_pdf(tmp_path):
    im = Image.new("RGB", (800, 1100), "white")
    ImageDraw.Draw(im).text((50, 50), "SKENIRANA STRANA", fill="black")
    im.save(tmp_path / "sken.pdf", "PDF")
    report = read_sources(tmp_path)
    assert len(report.to_read) == 1
    txt, image = report.to_read[0]
    assert image.exists() and image.with_suffix(".png").exists()  # preview .jpg + full 150-dpi render .png
    assert image.with_name(image.stem + "_a.jpg").exists() and image.with_name(image.stem + "_b.jpg").exists()
    assert "=== p1" in txt.read_text(encoding="utf-8")
    assert "[TO READ: " in txt.read_text(encoding="utf-8")


def _zip(path, parts):
    with zipfile.ZipFile(path, "w") as z:
        for name, content in parts.items():
            z.writestr(name, content)


W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


def slide(text):
    return (f'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" {A}><p:cSld><p:spTree>'
            f'<p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>')


def test_docx(tmp_path):
    _zip(tmp_path / "d.docx", {"word/document.xml": f'<w:document {W}><w:body><w:p><w:r><w:t>Zdravo </w:t></w:r>'
                                                    '<w:r><w:t>svete</w:t></w:r></w:p></w:body></w:document>'})
    read_sources(tmp_path)
    assert "Zdravo svete" in text(tmp_path, "d.docx.txt")


def test_pptx(tmp_path):
    _zip(tmp_path / "p.pptx", {"ppt/slides/slide2.xml": slide("Drugi slajd " + "x" * 50),
                               "ppt/slides/slide10.xml": slide("Deseti slajd " + "y" * 50),
                               "ppt/slides/slide1.xml": slide("Prvi slajd " + "z" * 50)})
    report = read_sources(tmp_path)
    t = text(tmp_path, "p.pptx.txt")
    assert t.index("=== s1") < t.index("Prvi slajd") < t.index("=== s2") < t.index("Drugi slajd") < t.index("=== s10")
    assert report.to_read == []


def test_pptx_picture_slide(tmp_path):
    from io import BytesIO
    b = BytesIO()
    Image.new("RGB", (50, 50), "blue").save(b, "PNG")
    rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            'Target="../media/image1.png"/></Relationships>')
    _zip(tmp_path / "p.pptx", {"ppt/slides/slide1.xml": slide(""), "ppt/slides/_rels/slide1.xml.rels": rels,
                               "ppt/media/image1.png": b.getvalue()})
    report = read_sources(tmp_path)
    assert len(report.to_read) == 1 and report.to_read[0][1].exists()
    assert "[TO READ: " in text(tmp_path, "p.pptx.txt")


def test_jpg(tmp_path):
    jpg(tmp_path / "strana.jpg", 2000, 1500, orientation=6)
    report = read_sources(tmp_path)
    t = text(tmp_path, "strana.jpg.txt")
    assert "[TO READ: _pages/strana.jpg" in t and "strana_a.jpg" in t and "strana_b.jpg" in t
    pages = tmp_path / "_text" / "_pages"
    preview = Image.open(pages / "strana.jpg")
    assert preview.height > preview.width and max(preview.size) <= 1600
    for half in ("strana_a.jpg", "strana_b.jpg"):
        assert Image.open(pages / half).size == (1500, 1100)  # 55 % of the upright 2000 px height
    assert report.to_read == [(tmp_path / "_text" / "strana.jpg.txt", pages / "strana.jpg")]


def test_predlozi_termine(tmp_path):
    t = tmp_path / "_text"
    t.mkdir()
    (t / "a.txt").write_text("=== x\n--- MAIN TEXT\nДве **контрактилне вакуоле** раде. Једна **год** годишње.\n"
                             "--- NOTES\nОвде **не узимај** ово.\n", encoding="utf-8")
    assert suggest_terms(t) == {"контрактилне вакуоле": r"контрактил\w*\s+вакуо", "год": r"год"}


def test_heic_failure_reported(tmp_path):
    (tmp_path / "slika.heic").write_bytes(os.urandom(2000))
    report = read_sources(tmp_path)
    assert len(report.errors) == 1 and "slika.heic" in report.errors[0]
    assert "[HEIC NOT CONVERTED" in text(tmp_path, "slika.heic.txt")
    assert len(read_sources(tmp_path).errors) == 1  # still reported on a rerun


def test_unsupported(tmp_path):
    (tmp_path / "fajl.xyz").write_text("x")
    report = read_sources(tmp_path)
    assert len(report.errors) == 1 and "fajl.xyz" in report.errors[0]
    assert not (tmp_path / "_text" / "fajl.xyz.txt").exists()


def test_rerun_keeps_transcriptions(tmp_path):
    jpg(tmp_path / "s.jpg")
    read_sources(tmp_path)
    txt = tmp_path / "_text" / "s.jpg.txt"
    s = txt.read_text(encoding="utf-8")
    begin = s.index("[TO READ:")
    txt.write_text(s[:begin] + "PREPISANO" + s[s.index("]", begin) + 1:], encoding="utf-8")
    report = read_sources(tmp_path)
    assert "PREPISANO" in txt.read_text(encoding="utf-8")
    assert report.skipped == [tmp_path / "s.jpg"] and report.to_read == []


def test_diacritic_and_space_names(tmp_path):
    jpg(tmp_path / "Zaštita (test)" / "slajd š.jpg")
    report = read_sources(tmp_path)
    assert (tmp_path / "_text" / "Zaštita (test)" / "slajd š.jpg.txt").exists()
    assert report.to_read[0][1] == tmp_path / "_text" / "_pages" / "Zaštita (test)" / "slajd š.jpg"


def test_placeholder_format():
    assert PLACEHOLDER.format(image="_pages/x.jpg") == "[TO READ: _pages/x.jpg]"


def test_cli(tmp_path):
    jpg(tmp_path / "s.jpg")
    r = subprocess.run([sys.executable, READ_SOURCES, str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "READ" in r.stdout, r.stdout + r.stderr
    (tmp_path / "f.xyz").write_text("x")
    r = subprocess.run([sys.executable, READ_SOURCES, str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "ERROR" in r.stdout


def test_touched_source_keeps_transcription(tmp_path):
    path = jpg(tmp_path / "s.jpg")
    read_sources(tmp_path)
    txt = tmp_path / "_text" / "s.jpg.txt"
    txt.write_text("=== s | страна 5\nPREPISANO\n", encoding="utf-8")
    newer = txt.stat().st_mtime + 100
    os.utime(path, (newer, newer))  # e.g. the photo folder copied again from the phone
    report = read_sources(tmp_path)
    assert "PREPISANO" in txt.read_text(encoding="utf-8")
    assert len(report.errors) == 1 and "s.jpg" in report.errors[0]
    assert (tmp_path / "_text" / "s.jpg.txt.new").exists()


def test_same_stem_sources_get_separate_previews(tmp_path):
    jpg(tmp_path / "IMG_1.jpg")
    Image.new("RGB", (300, 200), "blue").save(tmp_path / "IMG_1.png")
    report = read_sources(tmp_path)
    pictures = [s for _, s in report.to_read]
    assert len(pictures) == 2 and len(set(pictures)) == 2 and all(s.exists() for s in pictures)
