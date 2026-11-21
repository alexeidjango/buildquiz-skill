"""Draw the demo quiz's source page: the Sun and the four inner planets, with printed name labels.

Run once: python draw.py   (writes inner-planets.png next to this file and prints each label's box,
which the demo's pictures.py call covers with numbers).
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
W, H = 1200, 520
FONT = r"C:\Windows\Fonts\arial.ttf"

try:
    font = ImageFont.truetype(FONT, 30)
except OSError:
    font = ImageFont.load_default(30)

im = Image.new("RGB", (W, H), "#0f1b33")
d = ImageDraw.Draw(im)
for x, y in ((80, 60), (300, 450), (640, 70), (900, 470), (1130, 120), (470, 30), (1040, 300)):
    d.ellipse((x - 2, y - 2, x + 2, y + 2), fill="#c9d4ea")
d.ellipse((-260, 60, 140, 460), fill="#f6b73c")  # the Sun, cut off by the left edge
d.text((40, 260), "Sun", fill="#3a2600", font=font, anchor="lm")
planets = (("Mercury", 330, 16, "#9a9a9a"), ("Venus", 530, 30, "#e3c27a"),
           ("Earth", 760, 32, "#3d7fd6"), ("Mars", 990, 22, "#c8553d"))
for name, x, r, color in planets:
    d.arc((140 - (x - 140), 260 - (x - 140), x, 260 + (x - 140)), -20, 20, fill="#3b4c70", width=2)
    d.ellipse((x - r, 260 - r, x + r, 260 + r), fill=color)
    d.text((x, 360), name, fill="white", font=font, anchor="mm")
    x0, y0, x1, y1 = d.textbbox((x, 360), name, font=font, anchor="mm")
    print(f"{name}: --mask {x0 - 8},{y0 - 6},{x1 + 8},{y1 + 6},N")
im.save(HERE / "inner-planets.png")
print(HERE / "inner-planets.png", im.size)
