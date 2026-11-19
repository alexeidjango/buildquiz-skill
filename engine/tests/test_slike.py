import json
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw

from conftest import ENGINE
from slike import napravi

SLIKE = ENGINE / "slike.py"
# Upright page 3000x4000 -> preview 1200x1600 (k = 2.5). Red rectangle at full-res (750, 1000)-(1500, 1500),
# i.e. preview (300, 400)-(600, 600).
RECT = (750, 1000, 1500, 1500)


@pytest.fixture
def foto(tmp_path):
    uspravna = Image.new("RGB", (3000, 4000), "white")
    ImageDraw.Draw(uspravna).rectangle(RECT, fill=(220, 30, 30))
    sacuvana = uspravna.transpose(Image.Transpose.ROTATE_90)  # stored sideways; EXIF 6 turns it upright
    exif = Image.Exif()
    exif[0x0112] = 6
    put = tmp_path / "š folder" / "strana.jpg"
    put.parent.mkdir()
    sacuvana.save(put, "JPEG", quality=95, exif=exif.tobytes())
    kviz = tmp_path / "predmet" / "kviz"
    kviz.mkdir(parents=True)
    return put, kviz


def crveno(px):
    r, g, b = px[:3]
    return r > 180 and g < 90 and b < 90


def test_crop_scale(foto):
    put, kviz = foto
    out = napravi(kviz, "A_test", put, (200, 300, 600, 500))  # 400x200 preview px = 1000x500 full px
    im = Image.open(out)
    assert out == kviz / "slike" / "A_test.jpg"
    assert im.size == (900, 450)
    s = 900 / 1000
    # rectangle in output coords: full-res rect minus crop origin (500, 750), times s
    x0, y0 = (750 - 500) * s, (1000 - 750) * s
    assert crveno(im.getpixel((round(x0 + 20), round(y0 + 20))))
    assert not crveno(im.getpixel((round(x0 - 20), round(y0 + 20))))
    assert not crveno(im.getpixel((round(x0 + 20), round(y0 - 20))))


def test_mask_is_white_with_number(foto):
    put, kviz = foto
    im = Image.open(napravi(kviz, "A_maska", put, (200, 300, 600, 500), maske=[(320, 420, 400, 480, "3")]))
    s = 0.9 * 2.5  # preview px -> output px
    a, b, c, d = ((320 - 200) * s, (420 - 300) * s, (400 - 200) * s, (480 - 300) * s)
    for x, y in ((a + 6, b + 6), (c - 6, b + 6), (a + 6, d - 6), (c - 6, d - 6)):
        r, g, bb = im.getpixel((round(x), round(y)))
        assert min(r, g, bb) > 235, (x, y, (r, g, bb))
    cx, cy = (a + c) / 2, (b + d) / 2
    tamnocrveni = [im.getpixel((round(cx + dx), round(cy + dy))) for dx in range(-15, 16, 3) for dy in range(-15, 16, 3)]
    assert any(p[0] > 120 and p[1] < 60 and p[2] < 100 for p in tamnocrveni)


def test_record_and_rebuild_identical(foto):
    put, kviz = foto
    r = subprocess.run([sys.executable, SLIKE, str(kviz), "A_ponovo", str(put), "200", "300", "600", "500",
                        "--maska", "320,420,400,480,3", "--broj", "250,350,1"], capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    prvi = (kviz / "slike" / "A_ponovo.jpg").read_bytes()
    zapis = json.loads((kviz / "slike_A.json").read_text(encoding="utf-8"))["A_ponovo"]
    assert zapis["izvor"] == "../š folder/strana.jpg"
    assert zapis["box"] == [200, 300, 600, 500] and zapis["maske"] == [[320, 420, 400, 480, "3"]]
    assert zapis["brojevi"] == [[250, 350, "1"]] and zapis["sirina"] == 900
    (kviz / "slike" / "A_ponovo.jpg").unlink()
    r = subprocess.run([sys.executable, SLIKE, str(kviz), "--obnovi"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (kviz / "slike" / "A_ponovo.jpg").read_bytes() == prvi


def test_bad_id(foto):
    put, kviz = foto
    r = subprocess.run([sys.executable, SLIKE, str(kviz), "slika1", str(put), "0", "0", "10", "10"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "id" in (r.stdout + r.stderr)
    assert not (kviz / "slike_s.json").exists()


def test_diacritic_paths(foto):
    put, kviz = foto
    assert "š folder" in str(put)
    assert napravi(kviz, "B_dijakritika", put, (0, 0, 100, 100)).exists()
