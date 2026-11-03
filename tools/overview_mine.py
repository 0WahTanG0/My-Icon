"""Sheet with the icons drawn for the owner's apps (category "Мои приложения").

usage: python tools/overview_mine.py <out.png>   (after build_pack.py)
"""

import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
DRAW = ROOT / "android/app/src/generated/res/drawable-nodpi"
FONT = "/usr/share/fonts/opentype/inter/Inter-Medium.otf"


def main():
    out = Path(sys.argv[1])
    apps = []
    section = False
    for line in (ROOT / "pack/apps.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("["):
            section = line.strip() == "[Мои приложения]"
            continue
        m = re.match(r"map:[^=]+=([^|]+)\|(.+)", line.strip())
        if section and m:
            apps.append((m.group(2), m.group(1)))
    apps.sort(key=lambda a: a[0].lower())
    cols, cell, lab, pad = 6, 150, 34, 22
    rows = (len(apps) + cols - 1) // cols
    W = cols * cell + (cols + 1) * pad
    H = rows * (cell + lab) + (rows + 1) * pad
    sheet = Image.new("RGBA", (W, H), (52, 52, 52, 255))
    d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(FONT, 17)
    for i, (label, name) in enumerate(apps):
        r, c = divmod(i, cols)
        x, y = pad + c * (cell + pad), pad + r * (cell + lab + pad)
        im = Image.open(DRAW / f"{name}.png").convert("RGBA").resize((cell, cell), Image.LANCZOS)
        sheet.alpha_composite(im, (x, y))
        while d.textlength(label, font=f) > cell + pad - 4:
            label = label[:-2] + "…"
        w = d.textlength(label, font=f)
        d.text((x + (cell - w) / 2, y + cell + 6), label, font=f, fill=(210, 210, 210))
    sheet.convert("RGB").save(out, quality=92)
    print("saved", out, len(apps), "apps")


if __name__ == "__main__":
    main()
