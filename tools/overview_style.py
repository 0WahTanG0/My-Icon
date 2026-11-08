"""Preview of a pack style straight from its module: icons on three wallpapers
(light, colourful, dark) and an app without an icon (iconback/iconupon/mask).

usage: python tools/overview_style.py <module> <out.png>     e.g. style_glass
"""

import importlib
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from overview import fake_app_icon  # noqa: E402
from overview_noir import ITEMS, wall  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"


def svg(name):
    for p in (ROOT / "pack/glyphs" / f"{name}.svg", ROOT / "third_party/lawnicons/svgs" / f"{name}.svg"):
        if p.exists():
            return p.read_text(encoding="utf-8")
    raise FileNotFoundError(name)


def fallback(mod, icon, size):
    back, upon, mask = mod.back(size), mod.upon(size), mod.mask(size)
    n = int(size * mod.ICON_SCALE)
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    layer.alpha_composite(icon.resize((n, n), Image.LANCZOS), ((size - n) // 2, (size - n) // 2))
    layer.putalpha(ImageChops.multiply(layer.split()[-1], ImageChops.invert(mask.split()[-1])))
    out = back.copy()
    out.alpha_composite(layer)
    out.alpha_composite(upon)
    return out


def main():
    mod = importlib.import_module(sys.argv[1])
    fn = next(iter(mod.STYLES.values()))[1]
    cols, cell, pad, lab = 6, 150, 22, 30
    band_h = 2 * (cell + lab) + 3 * pad
    W = cols * cell + (cols + 1) * pad
    f = ImageFont.truetype(FONT, 17)
    fh = ImageFont.truetype(FONT, 20)
    icons = [(l, fn(svg(n), n, cell)) for l, n in ITEMS]
    fb_h = cell + 2 * pad + 40
    kinds = ["cream", "photo", "dark"]
    sheet = Image.new("RGB", (W, band_h * len(kinds) + fb_h))
    for bi, kind in enumerate(kinds):
        band = wall(kind, W, band_h)
        d = ImageDraw.Draw(band)
        tc = (70, 64, 56) if kind == "cream" else (245, 245, 245)
        for i, (l, ic) in enumerate(icons):
            r, c = divmod(i, cols)
            x, y = pad + c * (cell + pad), pad + r * (cell + lab + pad)
            band.alpha_composite(ic, (x, y))
            w = d.textlength(l, font=f)
            d.text((x + (cell - w) / 2, y + cell + 3), l, font=f, fill=tc)
        sheet.paste(band.convert("RGB"), (0, bi * band_h))
    band = wall("cream", W, fb_h)
    d = ImageDraw.Draw(band)
    d.text((pad, 12), "Приложения без иконки в паке:", font=fh, fill=(70, 64, 56))
    fakes = [((255, 94, 58), (255, 42, 104), "A"), ((40, 160, 255), (20, 80, 220), "B"),
             ((60, 200, 120), (20, 130, 90), "C")]
    for i, (a, b, l) in enumerate(fakes):
        band.alpha_composite(fallback(mod, fake_app_icon(512, a, b, l), cell), (pad + i * (cell + pad), 48))
    sheet.paste(band.convert("RGB"), (0, len(kinds) * band_h))
    sheet.save(sys.argv[2], quality=92)
    print("saved", sys.argv[2])


if __name__ == "__main__":
    main()
