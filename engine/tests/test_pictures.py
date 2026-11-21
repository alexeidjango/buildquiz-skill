import json
import subprocess
import sys

import pytest
from PIL import Image, ImageDraw

from conftest import ENGINE
from pictures import make

PICTURES = ENGINE / "pictures.py"
# Upright page 3000x4000 -> preview 1200x1600 (k = 2.5). Red rectangle at full-res (750, 1000)-(1500, 1500),
# i.e. preview (300, 400)-(600, 600).
RECT = (750, 1000, 1500, 1500)


@pytest.fixture
def photo(tmp_path):
    upright = Image.new("RGB", (3000, 4000), "white")
    ImageDraw.Draw(upright).rectangle(RECT, fill=(220, 30, 30))
    stored = upright.transpose(Image.Transpose.ROTATE_90)  # stored sideways; EXIF 6 turns it upright
    exif = Image.Exif()
    exif[0x0112] = 6
    path = tmp_path / "š folder" / "strana.jpg"
    path.parent.mkdir()
    stored.save(path, "JPEG", quality=95, exif=exif.tobytes())
    quiz = tmp_path / "predmet" / "kviz"
    quiz.mkdir(parents=True)
    return path, quiz


def is_red(px):
    r, g, b = px[:3]
    return r > 180 and g < 90 and b < 90


def test_crop_scale(photo):
    path, quiz = photo
    out = make(quiz, "A_test", path, (200, 300, 600, 500))  # 400x200 preview px = 1000x500 full px
    im = Image.open(out)
    assert out == quiz / "images" / "A_test.jpg"
    assert im.size == (900, 450)
    s = 900 / 1000
    # rectangle in output coords: full-res rect minus crop origin (500, 750), times s
    x0, y0 = (750 - 500) * s, (1000 - 750) * s
    assert is_red(im.getpixel((round(x0 + 20), round(y0 + 20))))
    assert not is_red(im.getpixel((round(x0 - 20), round(y0 + 20))))
    assert not is_red(im.getpixel((round(x0 + 20), round(y0 - 20))))


def test_mask_is_white_with_number(photo):
    path, quiz = photo
    im = Image.open(make(quiz, "A_mask", path, (200, 300, 600, 500), masks=[(320, 420, 400, 480, "3")]))
    s = 0.9 * 2.5  # preview px -> output px
    a, b, c, d = ((320 - 200) * s, (420 - 300) * s, (400 - 200) * s, (480 - 300) * s)
    for x, y in ((a + 6, b + 6), (c - 6, b + 6), (a + 6, d - 6), (c - 6, d - 6)):
        r, g, bb = im.getpixel((round(x), round(y)))
        assert min(r, g, bb) > 235, (x, y, (r, g, bb))
    cx, cy = (a + c) / 2, (b + d) / 2
    dark_red = [im.getpixel((round(cx + dx), round(cy + dy))) for dx in range(-15, 16, 3) for dy in range(-15, 16, 3)]
    assert any(p[0] > 120 and p[1] < 60 and p[2] < 100 for p in dark_red)


def test_record_and_rebuild_identical(photo):
    path, quiz = photo
    r = subprocess.run([sys.executable, PICTURES, str(quiz), "A_ponovo", str(path), "200", "300", "600", "500",
                        "--mask", "320,420,400,480,3", "--number", "250,350,1"], capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    first = (quiz / "images" / "A_ponovo.jpg").read_bytes()
    record = json.loads((quiz / "images_A.json").read_text(encoding="utf-8"))["A_ponovo"]
    assert record["source"] == "../š folder/strana.jpg"
    assert record["box"] == [200, 300, 600, 500] and record["masks"] == [[320, 420, 400, 480, "3"]]
    assert record["numbers"] == [[250, 350, "1"]] and record["width"] == 900
    (quiz / "images" / "A_ponovo.jpg").unlink()
    r = subprocess.run([sys.executable, PICTURES, str(quiz), "--rebuild"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stdout + r.stderr
    assert (quiz / "images" / "A_ponovo.jpg").read_bytes() == first


def test_bad_id(photo):
    path, quiz = photo
    r = subprocess.run([sys.executable, PICTURES, str(quiz), "slika1", str(path), "0", "0", "10", "10"],
                       capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 1 and "id" in (r.stdout + r.stderr)
    assert not (quiz / "images_s.json").exists()


def test_diacritic_paths(photo):
    path, quiz = photo
    assert "š folder" in str(path)
    assert make(quiz, "B_dijakritika", path, (0, 0, 100, 100)).exists()
