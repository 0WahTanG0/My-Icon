"""Render the sample sheet with 6 trial icons.

usage: python tools/preview.py <lawnicons_svgs_dir> <out.png>
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import iconstyle  # noqa: E402

SAMPLES = [
    ("Телефон", "generic_dialer"),
    ("Сообщения", "samsung_messages"),
    ("Камера", "generic_camera"),
    ("Chrome", "google_chrome"),
    ("Telegram", "telegram"),
    ("Настройки", "generic_settings"),
]

FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"


def bg_gradient(w, h, top, bottom):
    t = np.linspace(0, 1, h)[:, None, None]
    c = np.array(top)[None, None] * (1 - t) + np.array(bottom)[None, None] * t
    return Image.fromarray(np.repeat(c, w, axis=1).astype(np.uint8), "RGB")


def main():
    svgs = Path(sys.argv[1])
    out = Path(sys.argv[2])
    big = 360
    small = 128
    icons_big, icons_small = [], []
    r = iconstyle.Renderer()
    for label, name in SAMPLES:
        svg = (svgs / f"{name}.svg").read_text()
        work = r.compose(iconstyle.glyph_from_svg(svg))
        icons_big.append(iconstyle.finish(work, big))
        icons_small.append(iconstyle.finish(work, small))

    cols, rows = 3, 2
    pad = 56
    lab = 54
    W = cols * big + (cols + 1) * pad
    H1 = rows * (big + lab) + (rows + 1) * pad
    strip_h = small + 120
    H = H1 + strip_h
    sheet = bg_gradient(W, H1, (66, 66, 66), (44, 44, 44)).convert("RGBA")
    full = Image.new("RGBA", (W, H))
    full.paste(sheet, (0, 0))
    # lighter "wallpaper" strip to see the icons at home-screen size
    strip = bg_gradient(W, strip_h, (128, 132, 138), (84, 88, 94)).convert("RGBA")
    full.paste(strip, (0, H1))

    d = ImageDraw.Draw(full)
    f = ImageFont.truetype(FONT, 30)
    fs = ImageFont.truetype(FONT, 22)
    for i, (label, _) in enumerate(SAMPLES):
        r, c = divmod(i, cols)
        x = pad + c * (big + pad)
        y = pad + r * (big + lab + pad)
        full.alpha_composite(icons_big[i], (x, y))
        tw = d.textlength(label, font=f)
        d.text((x + (big - tw) / 2, y + big + 10), label, font=f, fill=(205, 205, 205))

    gap = (W - 6 * small) / 7
    for i, (label, _) in enumerate(SAMPLES):
        x = int(gap + i * (small + gap))
        y = H1 + 24
        full.alpha_composite(icons_small[i], (x, y))
        tw = d.textlength(label, font=fs)
        d.text((x + (small - tw) / 2, y + small + 8), label, font=fs, fill=(245, 245, 245))

    full.convert("RGB").save(out, quality=92)
    print("saved", out)


if __name__ == "__main__":
    main()
