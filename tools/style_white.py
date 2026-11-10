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

DCX, DCY, R = 0.56 * S, 0.44 * S, 0.40 * S    # disc, a little up-right: room for the shadow
HAS_NIGHT = True
# day: the reference; night: the same saucer in graphite with a light line
THEMES = {
    False: dict(base=240, gain=150, spec=25, ink=np.array([40, 40, 44]), shadow=np.array([60, 60, 66]),
                long=0.32, drop=0.30),
    True: dict(base=64, gain=95, spec=30, ink=np.array([228, 228, 232]), shadow=np.array([0, 0, 0]),
               long=0.50, drop=0.55),
}
LIGHT = (1.0, -1.0, 1.3)                          # from the top-right


def _disc(cx=DCX, cy=DCY, r=R):
    sd = sd_circle(r / S, cx, cy)
    return sd, cov(sd)


def _long_shadow(disc):
    """The disc swept down-left along the diagonal, fading with distance."""
    k2 = 2
    small = disc.reshape(S // k2, k2, S // k2, k2).mean(axis=(1, 3))
    # long like in the reference; a round vignette fades it out before the
    # square edge of the icon, so the edge never shows
    n = int(0.36 * S / k2)
    acc = np.zeros_like(small)
    for k in range(1, n):
        np.maximum(acc, shift(small, -k, k) * (1 - k / n) ** 1.1, out=acc)
    from PIL import Image
    big = np.asarray(Image.fromarray(acc.astype(np.float32), "F").resize((S, S), Image.BILINEAR))
    return blur(big, 0.01 * S)


def _vignette():
    """1 inside, 0 at the icon's edge: a rounded square (no hard straight cut)."""
    u, v = np.abs(XX / S - 0.5) / 0.5, np.abs(YY / S - 0.5) / 0.5
    d = (u ** 5 + v ** 5) ** 0.2                   # 1 on the edge, rounded corners
    t = np.clip((1 - d) / 0.16, 0, 1)
    return t * t * (3 - 2 * t)


def _base(c: Canvas, dark=False, cx=DCX, cy=DCY, r=R, long_shadow=True):
    th = THEMES[dark]
    sd, disc = _disc(cx, cy, r)
    if long_shadow:
        c.over(th["shadow"], _long_shadow(disc) * th["long"] * (1 - disc) * _vignette())
    c.over(th["shadow"], blur(shift(disc, -0.008 * S, 0.011 * S), 0.014 * S) * th["drop"] * (1 - disc))
    # height field: rounded outer edge, then a shallow parabolic saucer inside it
    rim = 0.03 * S * (r / R)
    h = dome(sd, 0.013 * S, 0.008 * S)
    rr = np.hypot(XX - cx, YY - cy) / (r - rim)
    h = h - 0.09 * S * (r / R) * np.clip(1 - rr ** 2, 0, 1) * cov(sd - rim * 0.3)
    h = blur(h, 1.5)
    shade, spec, _ = light(h, L=LIGHT, power=24)
    col = th["base"] + shade * th["gain"] + spec * th["spec"]
    c.over(np.repeat(np.clip(col, 0, 255)[..., None], 3, axis=2), disc)
    return disc


def white(svg, name, out=256, dark=False):
    c = Canvas()
    _base(c, dark)
    g = glyph(svg, 0.5, 0.6)
    g = shift(g, DCX - S / 2, DCY - S / 2)
    c.over(THEMES[dark]["ink"], g)
    return c.image(out)


def white_dark(svg, name, out=256):
    return white(svg, name, out, dark=True)


# iconback: also used by Theme Park as the folder background, so it is a big
# centred saucer without the long shadow (the folder's icon grid sits inside it)
BACK = dict(cx=S / 2, cy=S / 2, r=0.46 * S)


def back(out=256, dark=False):
    c = Canvas()
    _base(c, dark, long_shadow=False, **BACK)
    return c.image(out)


def upon(out=256):
    """iconupon: nothing on top (the app icon simply sits on the disc)."""
    c = Canvas()
    return c.image(out)


def mask(out=256):
    """iconmask: only cuts what lies outside the disc (launchers apply DST_OUT)."""
    from styles import finish
    _, disc = _disc(**BACK)
    img = np.zeros((S, S, 4))
    img[..., 3] = (1 - disc) * 255
    return finish(img, out)


ICON_SCALE = 0.64
NIGHT_STYLE = white_dark

STYLES = {"white": ("Белый", white)}
