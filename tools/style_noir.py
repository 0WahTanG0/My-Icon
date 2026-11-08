""""Noir" style: a thick black matte slab with the glyph cut through it.

Modelled on the owner's reference (black tile, see-through bubble, thin black
handset floating in it): every area the glyph's outlines enclose is a hole
through the slab, so the wallpaper shows through it; the outlines themselves,
nested ones included, stay as thin raised black lines, and an engraved groove
follows the glyph's silhouette.  The slab floats above the wallpaper, so its
shadow falls outside the tile and, through the holes, on the wallpaper inside.

Glyphs without real enclosed areas (open strokes, lettering with tiny counters)
get their strokes cut out as a stencil inside a raised rim.

style(svg_text, name, out_size) -> PIL RGBA, plus back()/upon()/mask() for
apps without an icon (their icon shows through a round window).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from styles import CX, CY, S, XX, YY, Canvas, blur, cov, dome, glyph, light, sd_roundrect, shift, tube_height

BLACK = 27.0
TILE = dict(half=0.43, r=0.15, cx=CX - 0.006 * S, cy=CY - 0.008 * S)


def sdf(mask_bool):
    d_in = ndimage.distance_transform_edt(mask_bool)
    d_out = ndimage.distance_transform_edt(~mask_bool)
    return blur(np.where(mask_bool, d_in - 0.5, -(d_out - 0.5)), 1.2)


STROKE = 0.7   # line weight relative to Lawnicons (thin, like the reference)


def _glyph_parts(svg):
    g = glyph(svg, 0.62, STROKE)
    gb = g > 0.5
    filled = ndimage.binary_fill_holes(gb)
    inner = ndimage.binary_dilation(filled & ~gb, iterations=3)
    hole = blur(inner.astype(float), 1.0) * (1 - g)
    if hole.sum() < 0.5 * g.sum():
        # open strokes or lettering (tiny counters): stencil, strokes cut out inside a raised rim
        rim = cov(sdf(gb) + 0.013 * S)
        return g, np.clip(rim - g, 0, 1), rim > 0.5
    return hole, g, filled


def _porthole():
    r = 0.25 * S
    d = np.hypot(XX - TILE["cx"], YY - TILE["cy"])
    hole = cov(r - d)
    ring = np.clip(cov(r + 0.035 * S - d) - hole, 0, 1)
    return hole, ring, (r + 0.035 * S - d) > 0


def compose(hole=None, raised=None, sil=None, outer_shadow=True):
    sd_t = sd_roundrect(TILE["half"], TILE["r"], TILE["cx"], TILE["cy"])
    tile = cov(sd_t)
    if hole is None:
        hole = np.zeros((S, S))
        raised = np.zeros((S, S))
    material = tile * (1 - hole)

    h = dome(sd_t, 0.035 * S, 0.022 * S)
    if sil is not None:
        groove = np.exp(-((sdf(sil) + 0.017 * S) / (0.003 * S)) ** 2)
        h -= 0.004 * S * groove
    h += tube_height(raised, 0.005 * S, 0.008 * S, 2.6)
    # the cut walls drop down into the hole
    h -= 0.03 * S * blur(hole, 2.0)
    shade, spec, _ = light(h, power=22)
    black = BLACK + shade * 115 + spec * 55
    black += (np.random.default_rng(3).random((S, S)) - 0.5) * 2.0
    black = np.clip(black, 0, 255)

    # shadow of the floating slab: outside the tile and, through the holes, inside
    far = blur(shift(material, 0.012 * S, 0.024 * S), 0.03 * S)
    near = blur(shift(material, 0.004 * S, 0.008 * S), 0.008 * S)
    inside = blur(tile, 2.0)
    # outside the tile: full drop shadow; inside the holes: lighter, so thin cuts stay readable
    far_k = 0.45 * (1 - inside) + 0.18 * inside
    near_k = 0.35 * (1 - inside) + 0.30 * inside
    sh = 1 - (1 - far * far_k) * (1 - near * near_k)
    if not outer_shadow:
        sh = sh * hole
    c = Canvas()
    c.over(np.zeros(3), sh * (1 - material))
    c.over(np.repeat(black[..., None], 3, axis=2), material)
    return c


def noir(svg, name, out=256):
    hole, raised, sil = _glyph_parts(svg)
    return compose(hole, raised, sil).image(out)


def back(out=256):
    """iconback: the plain slab behind an app icon."""
    return compose().image(out)


def upon(out=256):
    """iconupon: slab with a round window, laid over the app icon."""
    hole, ring, sil = _porthole()
    return compose(hole, ring, sil, outer_shadow=False).image(out)


def mask(out=256):
    """iconmask: only cuts what lies outside the tile (launchers apply DST_OUT)."""
    from styles import finish
    sd_t = sd_roundrect(TILE["half"], TILE["r"], TILE["cx"], TILE["cy"])
    img = np.zeros((S, S, 4))
    img[..., 3] = (1 - cov(sd_t)) * 255
    return finish(img, out)


ICON_SCALE = 0.56   # app icon size inside the round window

STYLES = {"noir": ("Noir", noir)}
