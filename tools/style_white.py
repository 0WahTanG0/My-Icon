""""White" style: a raised white disc with a concave, saucer-like top.

Taken apart from the owner's reference picture (measured, not guessed):
 - the disc is darker at the top and right and brighter at the bottom and left;
   with the light coming from the top-right that is a dished (concave) top, a
   shallow saucer, while the rounded outer edge catches a thin highlight at the
   top-right - the round, white sibling of the graphite style;
 - the disc stands on the wallpaper, so a long soft shadow runs diagonally
   down-left, the disc swept along that diagonal and fading out;
 - a thin dark line glyph (about 2.4 % of the disc's diameter) lies in the saucer.

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
    n = int(0.6 * S / k2)
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
    c.over(SHADOW, _long_shadow(disc) * 0.22 * fade * (1 - disc))
    c.over(SHADOW, blur(shift(disc, -0.006 * S, 0.008 * S), 0.012 * S) * 0.22 * (1 - disc))
    # height field: rounded outer edge, then a shallow parabolic saucer inside it
    rim = 0.03 * S
    h = dome(sd, 0.013 * S, 0.008 * S)
    r = np.hypot(XX - DCX, YY - DCY) / (R - rim)
    h = h - 0.075 * S * np.clip(1 - r ** 2, 0, 1) * cov(sd - rim * 0.3)
    h = blur(h, 1.5)
    shade, spec, _ = light(h, L=LIGHT, power=24)
    col = 240 + shade * 115 + spec * 25
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
