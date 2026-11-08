""""Glass" style: a thick, clear acrylic slab with a dark printed glyph.

Modelled on the owner's reference (clear glass buttons and search field):
 - the slab is almost perfectly clear: the wallpaper shows through unchanged,
   only a whisper of frost;
 - it has thickness: seen slightly from above, the front face of the slab shows
   as a band along the bottom (milky, with a bright line where light leaves the
   glass and the shadow refracted into it);
 - the polished edge reads as a thin double outline (outer silhouette and the
   inner edge of the top face), with crisp specular lines and a glint in the
   top-left corner;
 - a soft shadow and a darker contact line on the wallpaper below.

style(svg_text, name, out_size) -> PIL RGBA, plus back()/upon()/mask() for
apps without an icon (their own icon sits under the glass).
"""

from __future__ import annotations

import numpy as np

from styles import CX, CY, S, XX, YY, Canvas, blur, cov, dome, glyph, light, sd_roundrect, shift

HALF, RADIUS = 0.40, 0.15
LIFT = 0.036 * S            # visible thickness of the slab (front face height)
TOP_CY = CY - 0.026 * S     # top face centre
INK = np.array([30, 30, 30])
WHITE = np.array([255, 255, 255])
GREY = np.array([110, 110, 110])


def _geometry():
    sd_top = sd_roundrect(HALF, RADIUS, CX, TOP_CY)
    sd_bot = sd_roundrect(HALF, RADIUS, CX, TOP_CY + LIFT)
    sd_sil = np.maximum(sd_top, sd_bot)            # union: whole slab outline
    return sd_top, sd_bot, sd_sil


def _line(sd, at, width):
    return np.clip(1 - np.abs(sd - at) / width, 0, 1)


def drop_shadow(c: Canvas, sil):
    keep = 1 - 0.85 * sil                           # barely any under the clear slab
    c.over(np.array([60, 60, 60]), blur(shift(sil, 0, 0.035 * S), 0.04 * S) * 0.28 * keep)
    c.over(np.array([60, 60, 60]), blur(shift(sil, 0, 0.01 * S), 0.01 * S) * 0.28 * keep)


def _slab(c: Canvas, frost=True, front=True):
    """Draw the glass slab; returns (top face coverage, silhouette coverage)."""
    sd_top, sd_bot, sd_sil = _geometry()
    top, sil = cov(sd_top), cov(sd_sil)
    # one smooth rounded edge; wider at the bottom, where the slab's thickness shows
    lower = np.clip((YY - (TOP_CY - 0.1 * S)) / (HALF * S + LIFT), 0, 1) ** 1.6
    W = 0.05 * S * (1 + 1.1 * lower)
    e = np.clip(1 - sd_sil / W, 0, 1)               # 1 at the outline, 0 on the flat top
    h = 0.05 * S * np.sqrt(np.clip(1 - e ** 2, 0, 1))

    if frost:
        # nearly clear middle, milky towards the rim (internal reflection / fresnel)
        t = np.clip((YY - (TOP_CY - HALF * S)) / (2 * HALF * S), 0, 1)
        c.over(WHITE, sil * ((0.09 - 0.04 * t) + 0.34 * e ** 1.6))
    if front:
        # shadow refracted into the lower rim, then the bright exit line at the very bottom
        c.over(GREY, sil * lower * 0.2 * np.exp(-((e - 0.55) / 0.2) ** 2))
        c.over(WHITE, sil * lower * 0.8 * np.exp(-((e - 0.9) / 0.07) ** 2))

    # polished edge: crisp outer outline and a faint inner line where the flat top begins
    c.over(np.array([120, 120, 120]), _line(sd_sil, 0.003 * S, 0.003 * S) * 0.5)
    c.over(WHITE, np.clip(1 - np.abs(e - 0.02) / 0.03, 0, 1) * (sd_sil > 0) * 0.35)
    _, spec_t, _ = light(h, L=(-0.3, -1.0, 1.0), power=110)
    _, spec_b, _ = light(h, L=(0.15, 1.0, 1.5), power=70)
    c.over(WHITE, np.clip(spec_t * 3.4 + spec_b * 1.2, 0, 1) * sil)
    # glint in the top-left corner
    gx, gy = CX - HALF * S + 0.075 * S, TOP_CY - HALF * S + 0.075 * S
    glint = np.exp(-(((XX - gx) + (YY - gy)) / (0.09 * S)) ** 2 - (((XX - gx) - (YY - gy)) / (0.028 * S)) ** 2)
    c.over(WHITE, glint * np.clip(1 - np.abs(e - 0.75) / 0.25, 0, 1) * sil * 0.85)
    return top, sil


def glass(svg, name, out=256):
    _, _, sd_sil = _geometry()
    sil = cov(sd_sil)
    g = shift(glyph(svg, 0.5, 0.95), 0, -0.026 * S)
    c = Canvas()
    drop_shadow(c, sil)
    c.shadow(g, 0, 0.03 * S, 0.012 * S, 0.10, (40, 40, 40))     # print shadow on the wallpaper
    top, _ = _slab(c)
    c.over(WHITE, np.clip(blur(g, 0.009 * S) * 0.55, 0, 1) * top)   # keeps ink readable on dark walls
    c.over(INK, g * 0.95)
    return c.image(out)


def back(out=256):
    """iconback: the empty slab with its shadow."""
    _, _, sd_sil = _geometry()
    c = Canvas()
    drop_shadow(c, cov(sd_sil))
    _slab(c)
    return c.image(out)


def upon(out=256):
    """iconupon: edges and highlights laid over the app icon (icon under the glass)."""
    c = Canvas()
    _slab(c, frost=False, front=False)
    return c.image(out)


def mask(out=256):
    """iconmask: only cuts what lies outside the slab (launchers apply DST_OUT)."""
    from styles import finish
    _, _, sd_sil = _geometry()
    img = np.zeros((S, S, 4))
    img[..., 3] = (1 - cov(sd_sil)) * 255
    return finish(img, out)


ICON_SCALE = 0.6

STYLES = {"glass": ("Glass", glass)}
