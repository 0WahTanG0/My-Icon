""""Noir" style: a thick black matte slab with the glyph cut through it.

Modelled on the owner's reference (black tile, see-through bubble, black
handset floating in it): the glyph's enclosed areas are holes through the slab,
so the wallpaper shows through them; the outline around a hole is raised black,
shapes nested inside a hole are raised black again, and a thin engraved groove
follows the glyph's silhouette.  The slab floats above the wallpaper, so its
shadow falls outside the tile and, through the holes, on the wallpaper inside.

Lawnicons glyphs are outlines, so holes come from nesting depth: regions
enclosed by one outline are holes, regions enclosed again inside a hole are
slab, and so on.  Glyphs without enclosed areas (open strokes, letters) get
their strokes cut out as a stencil inside a raised rim.

style(svg_text, name, out_size) -> PIL RGBA, plus back()/upon()/mask() for
apps without an icon (their icon shows through a round window).
"""

from __future__ import annotations

from collections import deque

import numpy as np
from scipy import ndimage

from styles import CX, CY, S, XX, YY, Canvas, blur, cov, dome, glyph, light, sd_roundrect, shift, tube_height

BLACK = 27.0
TILE = dict(half=0.43, r=0.15, cx=CX - 0.006 * S, cy=CY - 0.008 * S)


def nesting(g, k=2, thr=0.5):
    """Background regions of the glyph at odd and at even (>=2) nesting depth."""
    small = g.reshape(S // k, k, S // k, k).mean(axis=(1, 3)) > thr
    strokes, ns = ndimage.label(small)
    bg, nb = ndimage.label(~small)
    border = np.concatenate([bg[0], bg[-1], bg[:, 0], bg[:, -1]])
    border = border[border > 0]
    empty = np.zeros((S, S), bool)
    if not border.size:
        return empty, empty
    outside = np.bincount(border).argmax()
    adj_b = {b: set() for b in range(1, nb + 1)}
    adj_s = {s: set() for s in range(1, ns + 1)}
    H, W = small.shape
    for b, sl in enumerate(ndimage.find_objects(bg), 1):
        if sl is None:
            continue
        y0, y1 = max(sl[0].start - 3, 0), min(sl[0].stop + 3, H)
        x0, x1 = max(sl[1].start - 3, 0), min(sl[1].stop + 3, W)
        sub = bg[y0:y1, x0:x1] == b
        ring = ndimage.binary_dilation(sub, iterations=2) & ~sub
        for s in np.unique(strokes[y0:y1, x0:x1][ring]):
            if s:
                adj_b[b].add(s)
                adj_s[s].add(b)
    depth = {outside: 0}
    seen = set()
    q = deque([outside])
    while q:
        b = q.popleft()
        for s in adj_b[b]:
            if s not in seen:
                seen.add(s)
                for b2 in adj_s[s]:
                    if b2 not in depth:
                        depth[b2] = depth[b] + 1
                        q.append(b2)
    odd = np.isin(bg, [b for b, d in depth.items() if d % 2 == 1])
    even = np.isin(bg, [b for b, d in depth.items() if d >= 2 and d % 2 == 0])
    up = lambda m: ndimage.zoom(m.astype(np.uint8), k, order=0)[:S, :S].astype(bool)  # noqa: E731
    return up(odd), up(even)


def sdf(mask_bool):
    d_in = ndimage.distance_transform_edt(mask_bool)
    d_out = ndimage.distance_transform_edt(~mask_bool)
    return blur(np.where(mask_bool, d_in - 0.5, -(d_out - 0.5)), 1.2)


def _glyph_parts(svg):
    g = glyph(svg, 0.62, 0.85)
    gb = g > 0.5
    odd, even = nesting(g)
    odd = ndimage.binary_dilation(odd, iterations=3)
    even = ndimage.binary_dilation(even, iterations=3)
    sil = ndimage.binary_fill_holes(gb | odd | even)
    hole = blur(odd.astype(float), 1.0) * (1 - g)
    island = blur(even.astype(float), 1.0) * (1 - g)
    if hole.sum() < 0.45 * g.sum():
        # open strokes or lettering (tiny counters): stencil, strokes cut out inside a raised rim
        rim = cov(sdf(gb) + 0.013 * S)
        return g, np.clip(rim - g, 0, 1), rim > 0.5
    return hole, np.clip(g + island, 0, 1), sil


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
