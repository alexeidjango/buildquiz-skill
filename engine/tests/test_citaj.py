import os
import shutil
import subprocess
import sys
import zipfile

import pytest
from PIL import Image, ImageDraw

from citaj import PLACEHOLDER, citaj, predlozi_termine
from conftest import ENGINE, REPO

CITAJ = ENGINE / "citaj.py"


def jpg(put, w=400, h=300, orijentacija=None):
    put.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (w, h), "white")
    ImageDraw.Draw(im).rectangle((0, 0, w // 4, h // 4), fill="red")
    exif = Image.Exif()
    if orijentacija:
        exif[0x0112] = orijentacija
    im.save(put, "JPEG", exif=exif.tobytes())
    return put


def tekst(src, ime):
    return (src / "_tekst" / ime).read_text(encoding="utf-8")


def test_text_pdf(tmp_path):
    pdf = REPO / "zastitamreza/K1/03 Kontrola pristupa/03 Kontrola pristupa.pdf"
    if not pdf.exists():
        pytest.skip("ZRM sources missing")
    shutil.copy(pdf, tmp_path / pdf.name)
    iz = citaj(tmp_path)
    t = tekst(tmp_path, pdf.name + ".txt")
    assert "=== p1" in t and "Kontrola pristupa" in t
    assert iz.novi == [tmp_path / pdf.name]
    assert all(txt.name == pdf.name + ".txt" for txt, _ in iz.za_citanje)


def test_scanned_pdf(tmp_path):
    im = Image.new("RGB", (800, 1100), "white")
    ImageDraw.Draw(im).text((50, 50), "SKENIRANA STRANA", fill="black")
    im.save(tmp_path / "sken.pdf", "PDF")
    iz = citaj(tmp_path)
    assert len(iz.za_citanje) == 1
    txt, slika = iz.za_citanje[0]
    assert slika.exists() and slika.with_suffix(".png").exists()  # preview .jpg + full 150-dpi render .png
    assert slika.with_name(slika.stem + "_a.jpg").exists() and slika.with_name(slika.stem + "_b.jpg").exists()
    assert "=== p1" in txt.read_text(encoding="utf-8")
    assert "[ZA ČITANJE: " in txt.read_text(encoding="utf-8")


def _zip(put, delovi):
    with zipfile.ZipFile(put, "w") as z:
        for ime, sadrzaj in delovi.items():
            z.writestr(ime, sadrzaj)


W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
A = 'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'


def slajd(tekst):
    return (f'<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" {A}><p:cSld><p:spTree>'
            f'<p:sp><p:txBody><a:p><a:r><a:t>{tekst}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>')


def test_docx(tmp_path):
    _zip(tmp_path / "d.docx", {"word/document.xml": f'<w:document {W}><w:body><w:p><w:r><w:t>Zdravo </w:t></w:r>'
                                                    '<w:r><w:t>svete</w:t></w:r></w:p></w:body></w:document>'})
    citaj(tmp_path)
    assert "Zdravo svete" in tekst(tmp_path, "d.docx.txt")


def test_pptx(tmp_path):
    _zip(tmp_path / "p.pptx", {"ppt/slides/slide2.xml": slajd("Drugi slajd " + "x" * 50),
                               "ppt/slides/slide10.xml": slajd("Deseti slajd " + "y" * 50),
                               "ppt/slides/slide1.xml": slajd("Prvi slajd " + "z" * 50)})
    iz = citaj(tmp_path)
    t = tekst(tmp_path, "p.pptx.txt")
    assert t.index("=== s1") < t.index("Prvi slajd") < t.index("=== s2") < t.index("Drugi slajd") < t.index("=== s10")
    assert iz.za_citanje == []


def test_pptx_picture_slide(tmp_path):
    from io import BytesIO
    b = BytesIO()
    Image.new("RGB", (50, 50), "blue").save(b, "PNG")
    rels = ('<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
            'Target="../media/image1.png"/></Relationships>')
    _zip(tmp_path / "p.pptx", {"ppt/slides/slide1.xml": slajd(""), "ppt/slides/_rels/slide1.xml.rels": rels,
                               "ppt/media/image1.png": b.getvalue()})
    iz = citaj(tmp_path)
    assert len(iz.za_citanje) == 1 and iz.za_citanje[0][1].exists()
    assert "[ZA ČITANJE: " in tekst(tmp_path, "p.pptx.txt")


def test_jpg(tmp_path):
    jpg(tmp_path / "strana.jpg", 2000, 1500, orijentacija=6)
    iz = citaj(tmp_path)
    t = tekst(tmp_path, "strana.jpg.txt")
    assert "[ZA ČITANJE: _slike/strana.jpg" in t and "strana_a.jpg" in t and "strana_b.jpg" in t
    sl = tmp_path / "_tekst" / "_slike"
    pregled = Image.open(sl / "strana.jpg")
    assert pregled.height > pregled.width and max(pregled.size) <= 1600
    for pola in ("strana_a.jpg", "strana_b.jpg"):
        assert Image.open(sl / pola).size == (1500, 1100)  # 55 % of the upright 2000 px height
    assert iz.za_citanje == [(tmp_path / "_tekst" / "strana.jpg.txt", sl / "strana.jpg")]


def test_predlozi_termine(tmp_path):
    t = tmp_path / "_tekst"
    t.mkdir()
    (t / "a.txt").write_text("=== x\n--- ГЛАВНИ ТЕКСТ\nДве **контрактилне вакуоле** раде. Једна **год** годишње.\n"
                             "--- НАПОМЕНЕ\nОвде **не узимај** ово.\n", encoding="utf-8")
    assert predlozi_termine(t) == {"контрактилне вакуоле": r"контрактил\w*\s+вакуо", "год": r"год"}


def test_heic_failure_reported(tmp_path):
    (tmp_path / "slika.heic").write_bytes(os.urandom(2000))
    iz = citaj(tmp_path)
    assert len(iz.greske) == 1 and "slika.heic" in iz.greske[0]
    assert "[HEIC NIJE KONVERTOVAN" in tekst(tmp_path, "slika.heic.txt")
    assert len(citaj(tmp_path).greske) == 1  # still reported on a rerun


def test_unsupported(tmp_path):
    (tmp_path / "fajl.xyz").write_text("x")
    iz = citaj(tmp_path)
    assert len(iz.greske) == 1 and "fajl.xyz" in iz.greske[0]
    assert not (tmp_path / "_tekst" / "fajl.xyz.txt").exists()


def test_rerun_keeps_transcriptions(tmp_path):
    jpg(tmp_path / "s.jpg")
    citaj(tmp_path)
    txt = tmp_path / "_tekst" / "s.jpg.txt"
    s = txt.read_text(encoding="utf-8")
    pocetak = s.index("[ZA ČITANJE:")
    txt.write_text(s[:pocetak] + "PREPISANO" + s[s.index("]", pocetak) + 1:], encoding="utf-8")
    iz = citaj(tmp_path)
    assert "PREPISANO" in txt.read_text(encoding="utf-8")
    assert iz.preskoceni == [tmp_path / "s.jpg"] and iz.za_citanje == []


def test_diacritic_and_space_names(tmp_path):
    jpg(tmp_path / "Zaštita (test)" / "slajd š.jpg")
    iz = citaj(tmp_path)
    assert (tmp_path / "_tekst" / "Zaštita (test)" / "slajd š.jpg.txt").exists()
    assert iz.za_citanje[0][1] == tmp_path / "_tekst" / "_slike" / "Zaštita (test)" / "slajd š.jpg"


def test_placeholder_format():
    assert PLACEHOLDER.format(slika="_slike/x.jpg") == "[ZA ČITANJE: _slike/x.jpg]"


def test_cli(tmp_path):
    jpg(tmp_path / "s.jpg")
    r = subprocess.run([sys.executable, CITAJ, str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0 and "ČITAJ" in r.stdout, r.stdout + r.stderr
    (tmp_path / "f.xyz").write_text("x")
    r = subprocess.run([sys.executable, CITAJ, str(tmp_path)], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "GREŠKA" in r.stdout


def test_touched_source_keeps_transcription(tmp_path):
    put = jpg(tmp_path / "s.jpg")
    citaj(tmp_path)
    txt = tmp_path / "_tekst" / "s.jpg.txt"
    txt.write_text("=== s | страна 5\nPREPISANO\n", encoding="utf-8")
    novo = txt.stat().st_mtime + 100
    os.utime(put, (novo, novo))  # e.g. the photo folder copied again from the phone
    iz = citaj(tmp_path)
    assert "PREPISANO" in txt.read_text(encoding="utf-8")
    assert len(iz.greske) == 1 and "s.jpg" in iz.greske[0]
    assert (tmp_path / "_tekst" / "s.jpg.txt.novo").exists()


def test_same_stem_sources_get_separate_previews(tmp_path):
    jpg(tmp_path / "IMG_1.jpg")
    Image.new("RGB", (300, 200), "blue").save(tmp_path / "IMG_1.png")
    iz = citaj(tmp_path)
    slike = [s for _, s in iz.za_citanje]
    assert len(slike) == 2 and len(set(slike)) == 2 and all(s.exists() for s in slike)
