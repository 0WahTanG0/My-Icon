""""White" style: a raised round saucer - a rim lip around a sunken well.

v3.2 (owner: "icons a bit bigger, more shadow, it must look like a saucer, and
switch with the light / dark theme if possible"):
 - the disc fills more of the icon (R 0.36 -> 0.43 of the canvas);
 - real saucer profile: rounded outer edge, a flat lip, a wall sloping down
   into a flat floor where the glyph lies; the lip throws a shadow into the
   well on the side of the light (top-right), the far wall catches light;
 - a stronger drop shadow down-left plus a short long-shadow, both faded out
   by a round vignette so nothing is cut by the square edge of the icon;
 - dark=True gives the night twin (graphite saucer, light glyph); the pack
   ships it in drawable-night-nodpi, launchers that follow the system theme
   switch to it on their own.

style(svg_text, name, out_size) -> PIL RGBA, plus back()/upon()/mask().
"""

from __future__ import annotations

import numpy as np

from styles import S, XX, YY, Canvas, blur, cov, glyph, light, sd_circle, shift

DCX, DCY, R = 0.525 * S, 0.475 * S, 0.43 * S    # disc, a little up-right: room for the shadow
LIGHT = (1.0, -1.0, 1.25)                        # from the top-right
HAS_NIGHT = True

THEMES = {
    # base: lit flat surface; gain: how much the slope shading changes it
    False: dict(base=240, gain=105, spec=22, ink=np.array([44, 44, 48]), shadow=np.array([40, 40, 46]),
                drop=0.42, long=0.22, inner=0.22),
    True: dict(base=70, gain=75, spec=30, ink=np.array([226, 226, 230]), shadow=np.array([0, 0, 0]),
               drop=0.70, long=0.38, inner=0.35),
}


def _disc(cx=DCX, cy=DCY, r=R):
    sd = sd_circle(r / S, cx, cy)
    return sd, cov(sd)


def _vignette():
    """1 inside, fading to 0 before the square edge, along a circle (no straight cut)."""
    d = np.hypot(XX - S / 2, YY - S / 2)
    return np.clip((0.495 * S - d) / (0.05 * S), 0, 1)


def _long_shadow(disc, n_frac=0.10):
    """The disc swept down-left along the diagonal, fading with distance."""
    k2 = 2
    small = disc.reshape(S // k2, k2, S // k2, k2).mean(axis=(1, 3))
    n = int(n_frac * S / k2)
    acc = np.zeros_like(small)
    for k in range(1, n):
        np.maximum(acc, shift(small, -k, k) * (1 - k / n) ** 1.4, out=acc)
    from PIL import Image
    big = np.asarray(Image.fromarray(acc.astype(np.float32), "F").resize((S, S), Image.BILINEAR))
    return blur(big, 0.012 * S)


def _height(cx, cy, r):
    """Saucer height field (px): outer roll, flat lip, sloped wall, flat floor."""
    rho = np.hypot(XX - cx, YY - cy) / r
    t = r / R                                      # depths scale with the disc
    edge = np.clip((1 - rho) / 0.07, 0, 1)         # rounded outer edge
    h = 0.03 * S * t * np.sqrt(1 - (1 - edge) ** 2)
    lip, floor_ = 0.80, 0.58                       # wall runs from rho=lip down to rho=floor
    w = np.clip((lip - rho) / (lip - floor_), 0, 1)
    w = w * w * (3 - 2 * w)                        # smooth S-curve wall
    h = h - 0.07 * S * t * w
    # the floor is not quite flat: a very shallow dish, so it shades softly too
    h = h - 0.012 * S * t * np.clip(1 - (rho / floor_) ** 2, 0, 1)
    return blur(h, 1.5), rho


def _base(c: Canvas, dark=False, cx=DCX, cy=DCY, r=R, long_shadow=True):
    th = THEMES[dark]
    sd, disc = _disc(cx, cy, r)
    vig = _vignette()
    outside = 1 - disc
    if long_shadow:
        c.over(th["shadow"], _long_shadow(disc) * th["long"] * outside * vig)
    # soft drop shadow down-left + tight contact shadow
    o = 0.022 * S * (r / R)
    c.over(th["shadow"], blur(shift(disc, -o, o * 1.2), 0.028 * S) * th["drop"] * outside * vig)
    c.over(th["shadow"], blur(shift(disc, -0.004 * S, 0.006 * S), 0.006 * S) * th["drop"] * 0.6 * outside)

    h, rho = _height(cx, cy, r)
    shade, spec, _ = light(h, L=LIGHT, power=22)
    col = th["base"] + shade * th["gain"] + spec * 255 * th["spec"] / 100
    # the lip shades the top-right part of the well (light comes from there)
    well = np.clip((0.80 - rho) / 0.04, 0, 1)
    ish = blur(shift(1 - well, -0.035 * S * (r / R), 0.035 * S * (r / R)), 0.02 * S) * well
    col = col * (1 - th["inner"] * ish)
    # a little ambient occlusion where the wall meets the floor
    ao = np.exp(-((rho - 0.6) / 0.05) ** 2)
    col = col * (1 - 0.08 * ao)
    c.over(np.repeat(np.clip(col, 0, 255)[..., None], 3, axis=2), disc)
    return disc


def white(svg, name, out=256, dark=False):
    th = THEMES[dark]
    c = Canvas()
    _base(c, dark)
    g = glyph(svg, 0.47, 0.62)
    g = shift(g, DCX - S / 2, DCY - S / 2)
    if dark:
        # a faint glow under the light line so it reads on the dark floor
        c.over(np.array([0, 0, 0]), blur(shift(g, -2, 3), 2.5) * 0.35)
    c.over(th["ink"], g)
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


def upon(out=256, dark=False):
    """iconupon: nothing on top (the app icon simply sits on the disc)."""
    return Canvas().image(out)


def mask(out=256, dark=False):
    """iconmask: only cuts what lies outside the disc (launchers apply DST_OUT)."""
    from styles import finish
    _, disc = _disc(**BACK)
    img = np.zeros((S, S, 4))
    img[..., 3] = (1 - disc) * 255
    return finish(img, out)


ICON_SCALE = 0.52

STYLES = {"white": ("Белый", white)}
NIGHT_STYLE = white_dark
