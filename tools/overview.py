"""Overview sheet of the generated pack (run after build_pack.py).

usage: python tools/overview.py <out.png>
Shows a selection of icons and how an app without an icon looks
(iconback + scaled original icon + iconmask + iconupon, as launchers do it).
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DRAW = ROOT / "android/app/src/generated/res/drawable-nodpi"
FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"

SHOW = [
    ("Телефон", "generic_dialer"), ("Сообщения", "samsung_messages"), ("Камера", "generic_camera"),
    ("Галерея", "generic_gallery"), ("Настройки", "generic_settings"), ("Часы", "generic_clock"),
    ("Календарь", "themed_icon_calendar_3"), ("Заметки", "samsung_notes"), ("Интернет", "samsung_internet"),
    ("Galaxy Store", "samsung_galaxy_store"), ("Theme Park", "samsung_theme_park"), ("Wearable", "wear"),
    ("Chrome", "google_chrome"), ("Play Маркет", "google_play_store"), ("YouTube", "youtube"),
    ("Gmail", "gmail"), ("Карты", "google_maps"), ("Фото", "google_photos"),
    ("Telegram", "telegram"), ("WhatsApp", "whatsapp"), ("MAX", "max_messenger"),
    ("ВКонтакте", "vk"), ("Instagram", "instagram"), ("TikTok", "tiktok"),
    ("СберБанк", "sberbank"), ("Т-Банк", "t_bank"), ("ВТБ", "vtb"),
    ("Альфа", "alfa_bank"), ("Госуслуги", "gosuslugi"), ("Ozon", "ozon"),
    ("Wildberries", "wildberries"), ("Авито", "avito"), ("Яндекс Go", "yandex_go"),
    ("Spotify", "spotify"), ("ChatGPT", "chatgpt"), ("Claude", "claude_by_anthropic"),
]


def fake_app_icon(size, hue_a, hue_b, letter):
    """Colourful stand-in for an app the pack has no icon for."""
    y, x = np.mgrid[0:size, 0:size] / size
    t = (x + y) / 2
    a, b = np.array(hue_a), np.array(hue_b)
    rgb = (a[None, None] * (1 - t[..., None]) + b[None, None] * t[..., None]).astype(np.uint8)
    im = Image.fromarray(rgb, "RGB").convert("RGBA")
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).ellipse((0, 0, size - 1, size - 1), fill=255)
    im.putalpha(m)
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, int(size * 0.55))
    w = d.textlength(letter, font=f)
    d.text(((size - w) / 2, size * 0.16), letter, font=f, fill=(255, 255, 255, 255))
    return im


def themed_fallback(app_icon, scale=0.58):
    back = Image.open(DRAW / "iconback.png").convert("RGBA")
    upon = Image.open(DRAW / "iconupon.png").convert("RGBA")
    mask = Image.open(DRAW / "iconmask.png").convert("RGBA")
    S = back.width
    n = int(S * scale)
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    layer.alpha_composite(app_icon.resize((n, n), Image.LANCZOS), ((S - n) // 2, (S - n) // 2))
    # DST_OUT: opaque mask pixels erase the icon
    a = ImageChops.multiply(layer.split()[-1], ImageChops.invert(mask.split()[-1]))
    layer.putalpha(a)
    out = back.copy()
    out.alpha_composite(layer)
    out.alpha_composite(upon)
    return out


def main():
    out = Path(sys.argv[1])
    cols, cell, lab, pad = 6, 150, 34, 22
    rows = (len(SHOW) + cols - 1) // cols
    W = cols * cell + (cols + 1) * pad
    H = rows * (cell + lab) + (rows + 1) * pad + cell + lab + 80
    sheet = Image.new("RGBA", (W, H), (52, 52, 52, 255))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 18)
    fh = ImageFont.truetype(FONT, 22)

    def put(im, label, x, y):
        sheet.alpha_composite(im.resize((cell, cell), Image.LANCZOS), (x, y))
        w = d.textlength(label, font=f)
        d.text((x + (cell - w) / 2, y + cell + 6), label, font=f, fill=(210, 210, 210))

    for i, (label, name) in enumerate(SHOW):
        r, c = divmod(i, cols)
        p = DRAW / f"{name}.png"
        if not p.exists():
            print("missing", name)
            continue
        put(Image.open(p).convert("RGBA"), label, pad + c * (cell + pad), pad + r * (cell + lab + pad))

    y0 = pad + rows * (cell + lab + pad) + 10
    d.text((pad, y0), "Приложения без иконки в паке (iconback + iconmask + iconupon):",
           font=fh, fill=(230, 230, 230))
    y0 += 44
    fakes = [((255, 94, 58), (255, 42, 104), "A"), ((40, 160, 255), (20, 80, 220), "B"),
             ((60, 200, 120), (20, 130, 90), "C")]
    for i, (a, b, l) in enumerate(fakes):
        icon = fake_app_icon(512, a, b, l)
        x = pad + i * 2 * (cell + pad)
        put(icon, "оригинал", x, y0)
        put(themed_fallback(icon), "в паке", x + cell + pad, y0)
    sheet.convert("RGB").save(out, quality=92)
    print("saved", out)


if __name__ == "__main__":
    main()
