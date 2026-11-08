""""Glass" style: a thick, clear glass tile with a dark printed glyph.

Modelled on the owner's reference (clear glass buttons and cards): the tile is
mostly transparent, so the wallpaper shows through; a light frost keeps the
glyph readable on dark wallpapers.  The rounded glass edge catches two bright
rim highlights (top and bottom), has a thin grey refraction line at the outer
edge and a faint one where the bevel meets the flat top; light focused by the
glass brightens the inner bottom edge.  A soft grey shadow sits under it.

style(svg_text, name, out_size) -> PIL RGBA, plus back()/upon()/mask() for
apps without an icon (their own icon appears under the glass).
"""

from __future__ import annotations

import numpy as np

from styles import CX, CY, S, YY, Canvas, blur, cov, dome, glyph, light, sd_roundrect, shift

TILE = dict(half=0.42, r=0.14, cx=CX, cy=CY - 0.012 * S)
BEVEL = 0.056 * S
INK = np.array([33, 33, 33])
WHITE = np.array([255, 255, 255])


def _tile():
    sd = sd_roundrect(TILE["half"], TILE["r"], TILE["cx"], TILE["cy"])
    return sd, cov(sd)


def _glass(c: Canvas, sd, tile, shadow=True, body=True):
    if shadow:
        drop_shadow(c, tile)
    h = dome(sd, BEVEL, 0.04 * S)
    _, spec_top, _ = light(h, L=(-0.25, -1.0, 1.1), power=110)
    _, spec_bot, _ = light(h, L=(0.2, 1.0, 1.6), power=60)
    edge = np.clip(1 - sd / BEVEL, 0, 1)                      # 1 at the rim, 0 on the flat top
    if body:
        t = np.clip((YY - (TILE["cy"] - TILE["half"] * S)) / (2 * TILE["half"] * S), 0, 1)
        frost = (0.26 - 0.08 * t) + 0.12 * edge ** 2         # fresnel: edges look denser
        c.over(WHITE, frost * tile)
    # light focused by the glass along the inner bottom edge
    lower = np.clip((YY - (TILE["cy"] - 0.15 * S)) / (0.55 * S), 0, 1) ** 2   # smooth, no seam
    caustic = np.exp(-((sd - 0.022 * S) / (0.012 * S)) ** 2) * lower
    c.over(WHITE, np.clip(caustic * 0.35, 0, 1) * tile)
    # the shadow below, refracted up into the bottom edge of the glass
    refr = np.exp(-((sd - 0.034 * S) / (0.014 * S)) ** 2) * lower ** 1.5
    c.over(np.array([102, 102, 102]), np.clip(refr * 0.16, 0, 1) * tile)
    # thin grey refraction line at the outer edge, faint one where the bevel ends
    line_out = np.clip(1 - np.abs(sd - 0.0045 * S) / (0.0035 * S), 0, 1)
    line_in = np.clip(1 - np.abs(sd - BEVEL) / (0.003 * S), 0, 1)
    c.over(np.array([125, 125, 125]), np.clip(line_out * 0.32 + line_in * 0.12, 0, 1))
    # bright rim highlights
    c.over(WHITE, np.clip(spec_top * 3.0 + spec_bot * 1.6, 0, 1) * tile)


def drop_shadow(c: Canvas, tile):
    """Soft shadow on the wallpaper; almost none under the clear body itself."""
    keep = 1 - 0.8 * tile
    c.over(np.array([60, 60, 60]), blur(shift(tile, 0, 0.03 * S), 0.035 * S) * 0.26 * keep)
    c.over(np.array([60, 60, 60]), blur(shift(tile, 0, 0.008 * S), 0.008 * S) * 0.2 * keep)


def glass(svg, name, out=256):
    sd, tile = _tile()
    g = glyph(svg, 0.5, 0.95)
    g = shift(g, 0, -0.012 * S)
    c = Canvas()
    drop_shadow(c, tile)
    c.shadow(g, 0, 0.022 * S, 0.012 * S, 0.12, (42, 42, 42))   # glyph shadow on the wallpaper
    _glass(c, sd, tile, shadow=False)
    c.over(WHITE, np.clip(blur(g, 0.02 * S) * 0.5, 0, 1) * tile)  # frost halo behind the ink
    c.over(INK, g * 0.94)
    return c.image(out)


def back(out=256):
    """iconback: the empty glass tile with its shadow."""
    sd, tile = _tile()
    c = Canvas()
    _glass(c, sd, tile, shadow=True, body=True)
    return c.image(out)


def upon(out=256):
    """iconupon: rim highlights and edge lines laid over the app icon (icon under glass)."""
    sd, tile = _tile()
    c = Canvas()
    _glass(c, sd, tile, shadow=False, body=False)
    sheen = np.exp(-((YY - (TILE["cy"] - 0.2 * S)) / (0.12 * S)) ** 2) * cov(sd - BEVEL)
    c.over(WHITE, sheen * 0.12)
    return c.image(out)


def mask(out=256):
    """iconmask: only cuts what lies outside the tile (launchers apply DST_OUT)."""
    from styles import finish
    sd, tile = _tile()
    img = np.zeros((S, S, 4))
    img[..., 3] = (1 - tile) * 255
    return finish(img, out)


ICON_SCALE = 0.62

STYLES = {"glass": ("Glass", glass)}
