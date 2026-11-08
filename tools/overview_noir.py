"""Noir preview: icons on three wallpapers (the cut-outs are see-through) and
how an app without an icon looks through the round window.

usage: python tools/overview_noir.py <out.png>   (after build_pack.py --pack noir)
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from overview import fake_app_icon  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DRAW = ROOT / "android/app/src/generated-noir/res/drawable-nodpi"
FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"
ITEMS = [("WhatsApp", "whatsapp"), ("Телефон", "generic_dialer"), ("Сообщения", "samsung_messages"),
         ("Камера", "generic_camera"), ("Chrome", "google_chrome"), ("Telegram", "telegram"),
         ("Настройки", "generic_settings"), ("YouTube", "youtube"), ("СберБанк", "sberbank"),
         ("Госуслуги", "gosuslugi"), ("Делимобиль", "delimobil"), ("Мой Налог", "moy_nalog")]


def wall(kind, w, h):
    y, x = np.mgrid[0:h, 0:w] / max(w, h)
    if kind == "cream":
        a = np.zeros((h, w, 3)) + np.array([239, 233, 223])
    elif kind == "photo":
        a = np.stack([120 + 110 * np.sin(x * 5 + 1) * np.cos(y * 3), 90 + 90 * np.sin(y * 6 + 2),
                      170 + 70 * np.cos(x * 4 + y * 3)], -1)
    else:
        a = np.zeros((h, w, 3)) + np.array([52, 58, 70]) + (y[..., None] * 40)
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGB").convert("RGBA")


def fallback(icon, scale=0.56):
    back = Image.open(DRAW / "iconback.png").convert("RGBA")
    upon = Image.open(DRAW / "iconupon.png").convert("RGBA")
    mask = Image.open(DRAW / "iconmask.png").convert("RGBA")
    S = back.width
    n = int(S * scale)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    layer.alpha_composite(icon.resize((n, n), Image.LANCZOS), ((S - n) // 2, (S - n) // 2))
    layer.putalpha(ImageChops.multiply(layer.split()[-1], ImageChops.invert(mask.split()[-1])))
    out = back.copy()
    out.alpha_composite(layer)
    out.alpha_composite(upon)
    return out


def main():
    cols, cell, pad, lab = 6, 150, 22, 30
    band_h = 2 * (cell + lab) + 3 * pad
    W = cols * cell + (cols + 1) * pad
    f = ImageFont.truetype(FONT, 17)
    fh = ImageFont.truetype(FONT, 20)
    icons = [(l, Image.open(DRAW / f"{n}.png").convert("RGBA").resize((cell, cell), Image.LANCZOS))
             for l, n in ITEMS]
    fb_h = cell + lab + 2 * pad + 36
    sheet = Image.new("RGB", (W, band_h * 3 + fb_h))
    for bi, kind in enumerate(["cream", "photo", "dark"]):
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
    d.text((pad, 12), "Приложения без иконки в паке — их иконка видна в круглом окне:", font=fh, fill=(70, 64, 56))
    fakes = [((255, 94, 58), (255, 42, 104), "A"), ((40, 160, 255), (20, 80, 220), "B"),
             ((60, 200, 120), (20, 130, 90), "C")]
    for i, (a, b, l) in enumerate(fakes):
        im = fallback(fake_app_icon(512, a, b, l)).resize((cell, cell), Image.LANCZOS)
        band.alpha_composite(im, (pad + i * (cell + pad), 48))
    sheet.paste(band.convert("RGB"), (0, 3 * band_h))
    sheet.save(sys.argv[1], quality=92)
    print("saved", sys.argv[1])


if __name__ == "__main__":
    main()
