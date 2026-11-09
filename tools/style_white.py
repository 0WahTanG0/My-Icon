""""White" style: white round tiles with thin line glyphs and a long shadow.

Taken apart from the owner's reference picture:
 - a white disc, slightly domed: white towards the light (top-right), a soft
   light grey towards the bottom-left edge;
 - light from the top-right, so a long soft shadow runs diagonally down-left,
   the disc swept along that diagonal and fading out;
 - a thin dark line glyph (about 2.4 % of the disc's diameter), flat on the disc.

style(svg_text, name, out_size) -> PIL RGBA, plus back()/upon()/mask().
"""

from __future__ import annotations

import numpy as np

from styles import S, XX, YY, Canvas, blur, cov, dome, glyph, light, sd_circle, shift

DCX, DCY, R = 0.54 * S, 0.46 * S, 0.36 * S      # disc, a little up-right: room for the shadow
INK = np.array([46, 46, 50])
SHADOW = np.array([70, 70, 70])
LIGHT = (1.0, -1.0, 1.3)                          # from the top-right


def _disc():
    sd = sd_circle(R / S, DCX, DCY)
    return sd, cov(sd)


def _long_shadow(disc):
    """The disc swept down-left along the diagonal, fading with distance."""
    k2 = 2
    small = disc.reshape(S // k2, k2, S // k2, k2).mean(axis=(1, 3))
    n = int(0.5 * S / k2)
    acc = np.zeros_like(small)
    for k in range(1, n):
        np.maximum(acc, shift(small, -k, k) * (1 - k / n) ** 0.9, out=acc)
    from PIL import Image
    big = np.asarray(Image.fromarray(acc.astype(np.float32), "F").resize((S, S), Image.BILINEAR))
    return blur(big, 0.01 * S)


def _base(c: Canvas):
    sd, disc = _disc()
    # fade the long shadow out before the edges of the icon, so it never ends in a hard line
    border = np.minimum(np.minimum(XX, S - 1 - XX), np.minimum(YY, S - 1 - YY))
    fade = np.clip(border / (0.16 * S), 0, 1) ** 1.5
    c.over(SHADOW, _long_shadow(disc) * 0.17 * fade * (1 - disc))
    c.over(SHADOW, blur(shift(disc, -0.006 * S, 0.008 * S), 0.012 * S) * 0.22 * (1 - disc))
    h = dome(sd, 0.05 * S, 0.012 * S)
    shade, spec, _ = light(h, L=LIGHT, power=20)
    u = ((XX - DCX) - (YY - DCY)) / (2 * R)          # +1 towards the light, -1 away
    col = 247 + 7 * np.clip(u, -1, 1) + shade * 45 + spec * 10
    col = col - 10 * np.clip(-u, 0, 1) ** 2
    edge = np.clip(1 - np.abs(sd - 0.002 * S) / (0.003 * S), 0, 1) * np.clip(-u + 0.2, 0, 1)
    col = col * (1 - 0.12 * edge)
    c.over(np.repeat(np.clip(col, 0, 255)[..., None], 3, axis=2), disc)
    return disc


def white(svg, name, out=256):
    c = Canvas()
    _base(c)
    g = glyph(svg, 0.45, 0.6)
    g = shift(g, DCX - S / 2, DCY - S / 2)
    c.over(INK, g)
    return c.image(out)


def back(out=256):
    c = Canvas()
    _base(c)
    return c.image(out)


def upon(out=256):
    """iconupon: nothing on top (the app icon simply sits on the disc)."""
    c = Canvas()
    return c.image(out)


def mask(out=256):
    """iconmask: only cuts what lies outside the disc (launchers apply DST_OUT)."""
    from styles import finish
    _, disc = _disc()
    img = np.zeros((S, S, 4))
    img[..., 3] = (1 - disc) * 255
    return finish(img, out)


ICON_SCALE = 0.5

STYLES = {"white": ("Белый", white)}
