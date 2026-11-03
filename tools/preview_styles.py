"""Sample sheets for the alternative styles in tools/styles.py.

usage: python tools/preview_styles.py <svgs_dir> <out_prefix> [style ...]
Writes <out_prefix>_1.png (styles 1-5) and <out_prefix>_2.png (6-10),
or one sheet per given style list.
"""

import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
import styles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = [
    ("Телефон", "generic_dialer"),
    ("Сообщения", "samsung_messages"),
    ("Камера", "generic_camera"),
    ("Chrome", "google_chrome"),
    ("Telegram", "telegram"),
    ("Настройки", "generic_settings"),
]
FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
FONT_B = "/usr/share/fonts/opentype/inter/Inter-SemiBold.otf"


def find_svg(svgs: Path, name: str) -> str:
    for p in (ROOT / "pack/glyphs" / f"{name}.svg", svgs / f"{name}.svg"):
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError(name)


def sheet(keys, svgs, out):
    cell, pad, head, lab = 176, 20, 58, 30
    W = 6 * cell + 7 * pad
    rowh = head + cell + lab + pad
    img = Image.new("RGB", (W, len(keys) * rowh + pad), (40, 40, 42))
    d = ImageDraw.Draw(img)
    fh = ImageFont.truetype(FONT_B, 30)
    fl = ImageFont.truetype(FONT, 17)
    for r, key in enumerate(keys):
        title, fn = styles.STYLES[key]
        y0 = pad + r * rowh
        idx = list(styles.STYLES).index(key) + 1
        d.text((pad, y0 + 8), f"{idx}. {title}", font=fh, fill=(235, 235, 235))
        t0 = time.time()
        for i, (label, name) in enumerate(SAMPLES):
            icon = fn(find_svg(svgs, name), name, cell)
            x = pad + i * (cell + pad)
            img.paste(icon, (x, y0 + head), icon)
            w = d.textlength(label, font=fl)
            d.text((x + (cell - w) / 2, y0 + head + cell + 4), label, font=fl, fill=(200, 200, 200))
        print(f"{key}: {time.time() - t0:.1f}s", flush=True)
    img.save(out, quality=92)
    print("saved", out)


def main():
    svgs = Path(sys.argv[1])
    prefix = sys.argv[2]
    keys = sys.argv[3:] or list(styles.STYLES)
    if len(sys.argv) > 3:
        sheet(keys, svgs, f"{prefix}.png")
    else:
        sheet(keys[:5], svgs, f"{prefix}_1.png")
        sheet(keys[5:], svgs, f"{prefix}_2.png")


if __name__ == "__main__":
    main()
