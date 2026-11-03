"""Round 2: ten icon concepts that break the "tile + centred line glyph" template.

Each one changes the shape, scale, medium or composition, not just the material:
die-cut stickers, a gothic stained-glass window, an embroidered patch, toy
bricks, a page from a notebook, risograph print, Bauhaus composition, glitch,
neubrutalism and graffiti.  All procedural (Python + Pillow + NumPy + SciPy).

style(svg_text, name, out_size) -> PIL RGBA
"""

from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

from styles import (CX, CY, S, XX, YY, Canvas, blur, cov, glyph, glyph_sd, hsl, hsv, light, noise,
                    sd_circle, sd_roundrect, seed_of, shift, tonemap, tube_height)

MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"


def rng_of(name, salt=0):
    return np.random.default_rng(seed_of(name) + salt)


def pick(name, items, salt=0):
    return items[(seed_of(name) // 7 + salt) % len(items)]


def rgb(hexstr):
    hexstr = hexstr.lstrip("#")
    return np.array([int(hexstr[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


def rotate(img: Image.Image, deg: float) -> Image.Image:
    return img.rotate(deg, resample=Image.BICUBIC, center=(img.width / 2, img.height / 2))


def silhouette(g, grow):
    """Filled outline of the glyph grown by `grow` px (holes filled)."""
    sd = glyph_sd(g)
    solid = ndimage.binary_fill_holes(sd + grow > 0)
    return blur(solid.astype(float), 1.5)


def voronoi(pts, k2=4):
    """F1, F2 distances and nearest-cell index (computed at 1/k2 resolution)."""
    ys, xs = np.mgrid[0:S // k2, 0:S // k2] * k2
    d = np.stack([np.hypot(xs - px, ys - py) for px, py in pts])
    order = np.argsort(d, axis=0)
    ds = np.take_along_axis(d, order[:2], axis=0)
    z = lambda a: ndimage.zoom(a, k2, order=1)[:S, :S]  # noqa: E731
    cell = ndimage.zoom(order[0], k2, order=0)[:S, :S]
    return z(ds[0]), z(ds[1]), cell


def finish_canvas(c: Canvas, out, rot=0.0):
    im = c.image(out)
    return rotate(im, rot) if rot else im


# --------------------------------------------------------- 1. neubrutalism

NB = ["#FFD23F", "#FF6B9D", "#3BCEAC", "#A78BFA", "#FF8C42", "#C5F82A", "#4D96FF", "#FF5D5D"]


def neubrutal(svg, name, out=256):
    bg = rgb(pick(name, NB))
    acc = rgb(pick(name, NB, 3))
    off = 0.045 * S
    sd = sd_roundrect(0.39, 0.07, CX - off / 2, CY - off / 2)
    c = Canvas()
    c.over(np.zeros(3), cov(sd_roundrect(0.39, 0.07, CX + off / 2, CY + off / 2)))   # hard shadow
    c.over(np.zeros(3), cov(sd))                       # black outline
    inner = cov(sd - 0.022 * S)
    # dotted grid in the corner
    dots = ((np.hypot((XX % 40) - 20, (YY % 40) - 20) < 5) & (XX + YY < 0.55 * S)).astype(float)
    c.over(bg, inner)
    c.over(np.zeros(3), dots * inner * 0.85)
    # four-point star sticker
    sx, sy = CX + 0.24 * S, CY - 0.25 * S
    ang = np.arctan2(YY - sy, XX - sx)
    rr = np.hypot(XX - sx, YY - sy)
    star_r = 0.075 * S * (0.42 + 0.58 * np.abs(np.cos(2 * ang)) ** 3)
    star = cov(star_r - rr)
    c.over(np.zeros(3), cov(star_r + 0.012 * S - rr) * inner)
    c.over(acc, star * inner)

    g = glyph(svg, 0.5, 1.6)
    gsd = glyph_sd(g)
    c.over(np.zeros(3), shift(cov(gsd + 0.016 * S), 0.022 * S, 0.022 * S) * inner)
    c.over(np.zeros(3), cov(gsd + 0.016 * S))
    c.over(np.array([255, 255, 255]), cov(gsd))
    rot = (seed_of(name) % 11) - 5
    return finish_canvas(c, out, rot)


# ---------------------------------------------------------------- 2. sticker

def sticker(svg, name, out=256):
    hue = (seed_of(name) % 360) / 360
    g = glyph(svg, 0.6, 1.7)
    sil = silhouette(g, 0.055 * S)
    body = blur(sil, 2.0)
    filled = silhouette(g, 0.0)
    c = Canvas()
    c.shadow(body, 0.008 * S, 0.02 * S, 0.018 * S, 0.45)
    # white vinyl with a curved gloss
    h = blur(body, 0.03 * S) * 0.04 * S
    shade, spec, _ = light(h, power=30)
    vinyl = 247 + shade[..., None] * 40 + spec[..., None] * 60
    c.over(vinyl, body)
    c.over(hsl(hue, 0.85, 0.86), np.clip(filled - g, 0, 1))   # pastel inside the shapes
    ink = hsv(hue, 0.85, 0.92)
    c.over(ink * 0.55, shift(g, 0.006 * S, 0.006 * S) * 0.6)   # print shadow
    c.over(ink, g)
    gloss = np.clip(1 - np.abs((XX - YY) / S + 0.25) / 0.12, 0, 1) ** 2 * body
    c.over(np.array([255, 255, 255]), gloss * 0.35)
    rot = ((seed_of(name) // 3) % 21) - 10
    return finish_canvas(c, out, rot)


# ----------------------------------------------------------------- 3. glitch

def glitch(svg, name, out=256):
    rng = rng_of(name)
    cyan, mag, yel = rgb("#00F0FF"), rgb("#FF2A6D"), rgb("#F5F500")
    # chamfered square
    h = 0.44 * S
    sd = np.minimum(h - np.abs(XX - CX), h - np.abs(YY - CY))
    cut = 0.12 * S
    sd = np.minimum(sd, ((CX + h - XX) + (YY - (CY - h)) - cut) / math.sqrt(2))   # top-right
    sd = np.minimum(sd, ((XX - (CX - h)) + ((CY + h) - YY) - cut) / math.sqrt(2))  # bottom-left
    tile = cov(sd)

    base = np.zeros((S, S, 3)) + rgb("#0A0A14")
    grid = ((XX % 64 < 2) | (YY % 64 < 2)).astype(float) * 0.08
    base += grid[..., None] * cyan
    g = glyph(svg, 0.55, 1.25)
    img = base.copy()
    img = img + shift(g, -0.014 * S, 0)[..., None] * mag * 0.9
    img = img + shift(g, 0.014 * S, 0.004 * S)[..., None] * cyan * 0.9
    img = np.where(g[..., None] > 0, img * (1 - g[..., None]) + 255 * g[..., None], img)
    # displaced slices
    for _ in range(7):
        y0 = int(rng.random() * S * 0.9)
        hh = int((0.015 + rng.random() * 0.05) * S)
        dx = int((rng.random() - 0.5) * 0.14 * S)
        img[y0:y0 + hh] = np.roll(img[y0:y0 + hh], dx, axis=1)
        if rng.random() < 0.35:
            tint = mag if rng.random() < 0.5 else cyan
            img[y0:y0 + hh] = img[y0:y0 + hh] * 0.5 + tint * 0.35
    # data blocks
    for _ in range(9):
        x0, y0 = (rng.random(2) * 0.8 + 0.1) * S
        w, hh = (rng.random() * 0.08 + 0.01) * S, (rng.random() * 0.025 + 0.006) * S
        col = [cyan, mag, yel, np.array([255.0, 255, 255])][int(rng.random() * 4)]
        img[int(y0):int(y0 + hh), int(x0):int(x0 + w)] = col
    scan = (YY % 6 < 2).astype(float)
    img = img * (1 - 0.35 * scan[..., None])
    img = img + (noise(seed_of(name) + 1, 2, 1)[..., None] - 0.5) * 30

    lay = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(lay)
    d.text((0.12 * S, 0.81 * S), f"ERR_0x{seed_of(name) % 4096:03X}", font=ImageFont.truetype(MONO, 46), fill=255)
    txt = np.asarray(lay, dtype=float) / 255
    img = img * (1 - txt[..., None]) + cyan * txt[..., None]
    edge = np.clip(1 - np.abs(sd - 0.006 * S) / 3.0, 0, 1)
    img = img * (1 - edge[..., None]) + cyan * edge[..., None]

    c = Canvas()
    c.over(cyan * 0.4, blur(tile, 0.02 * S) * 0.35)
    c.over(np.clip(img, 0, 255), tile)
    return c.image(out)


# ----------------------------------------------------------- 4. stained glass

JEWELS = ["#B3001B", "#0F4C9A", "#0B7A47", "#E89F0C", "#6A2C91", "#0E7C86", "#C0392B", "#1F3A93"]


def stained_glass(svg, name, out=256):
    rng = rng_of(name)
    # gothic pointed arch
    l, r_, top, bot, spring = 0.17 * S, 0.83 * S, 0.06 * S, 0.94 * S, 0.44 * S
    w = r_ - l
    walls = np.minimum(np.minimum(XX - l, r_ - XX), bot - YY)
    R = 0.384 * S   # lancet arch whose apex sits at `top`
    arch = np.minimum(R - np.hypot(XX - (l + R), YY - spring), R - np.hypot(XX - (r_ - R), YY - spring))
    sd = np.where(YY > spring, walls, arch)
    window = cov(sd)
    stone = cov(sd + 0.045 * S)

    pts = rng.random((30, 2)) * np.array([w, bot - top]) + np.array([l, top])
    f1, f2, cell = voronoi(pts)
    pal = np.array([rgb(JEWELS[(i + seed_of(name)) % len(JEWELS)]) for i in range(len(pts))])
    pal *= (0.75 + 0.5 * rng.random((len(pts), 1)))
    glass = pal[cell]
    mottle = noise(seed_of(name) + 2, 30, 3)
    glass = glass * (0.7 + 0.6 * mottle[..., None])
    sun = np.clip(1.25 - np.hypot(XX - 0.35 * S, YY - 0.2 * S) / S, 0.55, 1.3)
    glass = glass * sun[..., None]

    g = glyph(svg, 0.48, 1.6)
    gsd = glyph_sd(g)
    lead_cells = np.exp(-((f2 - f1) / (0.007 * S)) ** 2)
    lead_glyph = cov(gsd + 0.016 * S) - cov(gsd)
    lead = np.clip(np.maximum(lead_cells * (1 - cov(gsd + 0.016 * S)), lead_glyph), 0, 1)
    halo = blur(g, 0.03 * S)
    glass = glass + halo[..., None] * np.array([255, 220, 140]) * 0.5
    bright = np.array([255, 241, 190]) * (0.92 + 0.16 * mottle[..., None])
    glass = glass * (1 - g[..., None]) + bright * g[..., None]
    glass = glass * (1 - lead[..., None]) + np.array([24, 22, 26]) * lead[..., None]
    glass = 255 * tonemap(glass / 255 * 1.1)

    hs = blur(stone, 0.01 * S) * 0.02 * S
    shade, spec, _ = light(hs, power=12)
    stone_col = np.array([128, 122, 112]) * (0.85 + 0.3 * noise(seed_of(name) + 5, 8, 3))[..., None] \
        + shade[..., None] * 140 + spec[..., None] * 40

    c = Canvas()
    c.shadow(stone, 0.008 * S, 0.018 * S, 0.02 * S, 0.5)
    c.over(np.clip(stone_col, 0, 255), stone)
    c.over(np.zeros(3), window * 0.9)
    c.over(np.clip(glass, 0, 255), cov(sd - 0.008 * S))
    return c.image(out)


# ------------------------------------------------------------- 5. toy bricks

BRICK = ["#D01012", "#0055BF", "#F2CD37", "#237841", "#FE8A18", "#A5499B", "#05131D", "#E4ADC8"]


def bricks(svg, name, out=256):
    N = 16
    cell = S / N
    plate_col = rgb(pick(name, BRICK))
    top_col = rgb("#F4F4F4") if pick(name, BRICK) not in ("#F2CD37", "#E4ADC8") else rgb("#05131D")
    g = glyph(svg, 0.66, 1.6)
    small = ndimage.zoom(g, N / S, order=1)
    up = small > 0.3
    margin = 1
    up[:margin], up[-margin:], up[:, :margin], up[:, -margin:] = False, False, False, False

    gx = np.floor(XX / cell).astype(int).clip(0, N - 1)
    gy = np.floor(YY / cell).astype(int).clip(0, N - 1)
    raised = up[gy, gx].astype(float)
    raised = blur(raised, 1.0)
    lx, ly = XX - (gx + 0.5) * cell, YY - (gy + 0.5) * cell
    rr = np.hypot(lx, ly)
    stud = cov(0.3 * cell - rr)
    stud_h = np.clip((0.3 * cell - rr) / 3, 0, 1) * 0.16 * cell

    # brick edges: small bevel on every raised cell
    edge = np.minimum(0.5 * cell - np.abs(lx), 0.5 * cell - np.abs(ly))
    bevel = np.clip(edge / (0.08 * cell), 0, 1)
    h = raised * (0.55 * cell * bevel) + stud_h + 0.02 * cell * np.clip(edge / 3, 0, 1)
    shade, spec, _ = light(h, power=18)
    col = plate_col * (1 - raised[..., None]) + top_col * raised[..., None]
    sh = blur(shift(raised, 0.18 * cell, 0.26 * cell), 0.12 * cell) * (1 - raised) * 0.55
    img = col * (1 - sh[..., None]) + shade[..., None] * 160 + spec[..., None] * 90

    sd = sd_roundrect(0.46, 0.03)
    c = Canvas()
    c.shadow(cov(sd), 0.006 * S, 0.016 * S, 0.016 * S, 0.5)
    c.over(np.clip(img, 0, 255), cov(sd))
    return c.image(out)


# ------------------------------------------------------- 6. embroidered patch

PATCH = [("#1F2A44", "#F2C14E"), ("#4B5D2A", "#F4E9CD"), ("#7A1F2B", "#F7D08A"),
         ("#0F5257", "#FFD6A5"), ("#2D2A32", "#FF7A59"), ("#3E2C5E", "#9FE2BF")]


def patch(svg, name, out=256):
    fabric_hex, thread_hex = pick(name, PATCH)
    fabric, thread = rgb(fabric_hex), rgb(thread_hex)
    sd = sd_circle(0.45)
    disc = cov(sd)
    twill = 0.5 + 0.5 * np.sin(2 * math.pi * (XX * 0.8 + YY) / 9)
    cloth = fabric * (0.85 + 0.18 * twill[..., None]) * (0.92 + 0.16 * noise(seed_of(name), 6, 2))[..., None]

    # merrowed border: rope of diagonal stitches
    ang = np.arctan2(YY - CY, XX - CX)
    border = np.clip((0.06 * S - sd) / 2 + 0.5, 0, 1) * disc
    rope = 0.5 + 0.5 * np.sin(ang * 0.45 * S / 6 + sd * 0.35)
    hb = blur(border, 6) * 0.03 * S
    shade_b, _, _ = light(hb + rope * 4 * border, power=10)
    border_col = thread * (0.7 + 0.45 * rope[..., None]) + shade_b[..., None] * 120

    g = glyph(svg, 0.5, 1.55)
    hg = tube_height(g, 0.01 * S, 0.03 * S, 1.8)
    stitch = 0.5 + 0.5 * np.sin(2 * math.pi * (XX - YY) / 7.0)
    shade_g, spec_g, _ = light(hg + stitch * 3 * g, power=12)
    gcol = thread * (0.78 + 0.32 * stitch[..., None]) + shade_g[..., None] * 140 + spec_g[..., None] * 50

    img = cloth * (1 - border[..., None]) + border_col * border[..., None]
    gsh = blur(shift(g, 0.006 * S, 0.012 * S), 0.008 * S) * 0.5
    img = img * (1 - gsh[..., None])
    img = img * (1 - g[..., None]) + gcol * g[..., None]
    c = Canvas()
    c.shadow(disc, 0.006 * S, 0.016 * S, 0.016 * S, 0.5)
    c.over(np.clip(img, 0, 255), disc)
    return c.image(out)


# ---------------------------------------------------------- 7. notebook sketch

MARKERS = ["#FFF04D", "#FF8FD1", "#7CFF9B", "#FFB347", "#8FD3FF"]


def sketch(svg, name, out=256):
    rng = rng_of(name)
    tear = (noise(seed_of(name) + 9, 14, 3) - 0.5) * 0.03 * S
    sd = sd_roundrect(0.43, 0.012) + tear
    paper = cov(sd)
    base = np.array([252, 250, 243]) * (0.97 + 0.04 * noise(seed_of(name) + 1, 3, 2))[..., None]
    lines = (np.abs(((YY - 0.1 * S) % (0.075 * S))) < 2.2).astype(float) * 0.55
    base = base * (1 - lines[..., None]) + np.array([150, 190, 235]) * lines[..., None]
    margin = (np.abs(XX - 0.2 * S) < 2.2).astype(float) * 0.6
    base = base * (1 - margin[..., None]) + np.array([235, 120, 120]) * margin[..., None]

    # highlighter blob behind the drawing
    mk = rgb(pick(name, MARKERS))
    blob_sd = 0.27 * S - np.hypot((XX - CX - 0.03 * S) * 1.0, (YY - CY - 0.02 * S) * 1.25) \
        + (noise(seed_of(name) + 3, 60, 2) - 0.5) * 0.08 * S
    blob = cov(blob_sd) * 0.75
    base = base * (1 - blob[..., None]) + base * (mk / 255) * blob[..., None]

    g0 = glyph(svg, 0.52, 0.55)
    ink = np.zeros((S, S))
    for k in range(3):
        nx = (noise(seed_of(name) + 20 + k, 90, 2) - 0.5) * 0.022 * S
        ny = (noise(seed_of(name) + 30 + k, 90, 2) - 0.5) * 0.022 * S
        warped = ndimage.map_coordinates(g0, [YY + ny + rng.normal() * 3, XX + nx + rng.normal() * 3], order=1)
        ink = np.maximum(ink, warped * (0.9 - 0.2 * k))
    holes = np.clip(silhouette(g0, 0) - blur(g0, 1), 0, 1)
    hatch = (np.abs(((XX + YY) % 22) - 11) < 1.6).astype(float) * holes * 0.55
    ink = np.maximum(ink, hatch)
    grain = noise(seed_of(name) + 4, 1.5, 1)
    ink = ink * (0.75 + 0.35 * grain)
    img = base * (1 - ink[..., None] * 0.85) + np.array([40, 40, 48]) * ink[..., None] * 0.85

    # tape on top
    tape = cov(np.minimum(0.07 * S - np.abs(YY - 0.075 * S - (XX - CX) * 0.12), 0.13 * S - np.abs(XX - CX)))
    c = Canvas()
    c.shadow(paper, 0.006 * S, 0.014 * S, 0.012 * S, 0.35)
    c.over(np.clip(img, 0, 255), paper)
    c.over(np.array([236, 226, 196]), tape * 0.65)
    rot = ((seed_of(name) // 5) % 9) - 4
    return finish_canvas(c, out, rot)


# ------------------------------------------------------------ 8. risograph

RISO = [("#FF48B0", "#0078BF"), ("#FF6C2F", "#3255A4"), ("#00A95C", "#FF48B0"),
        ("#FFE800", "#FF48B0"), ("#765BA7", "#FF6C2F"), ("#0078BF", "#FFE800")]


def risograph(svg, name, out=256):
    a_hex, b_hex = pick(name, RISO)
    ink_a, ink_b = rgb(a_hex), rgb(b_hex)
    rng = rng_of(name)
    sd = sd_roundrect(0.45, 0.025)
    tile = cov(sd)
    paper = np.array([246, 241, 228])

    # halftone disc in ink A (dot size follows a gradient)
    ang = math.radians(15)
    u = (XX * math.cos(ang) + YY * math.sin(ang))
    v = (-XX * math.sin(ang) + YY * math.cos(ang))
    period = 0.028 * S
    du = (u % period) - period / 2
    dv = (v % period) - period / 2
    cx, cy = CX + (rng.random() - 0.5) * 0.3 * S, CY + (rng.random() - 0.5) * 0.3 * S
    val = np.clip(1.15 - np.hypot(XX - cx, YY - cy) / (0.45 * S), 0, 1)
    dots = cov(np.sqrt(val) * period * 0.62 - np.hypot(du, dv))
    grain = noise(seed_of(name) + 2, 1.5, 1)
    cov_a = dots * (0.75 + 0.3 * grain)

    # huge glyph in ink B, cropped by the tile, slightly mis-registered
    g = glyph(svg, 0.86, 1.6)
    g = shift(g, 0.08 * S, 0.06 * S)
    cov_b = g * (0.82 + 0.25 * noise(seed_of(name) + 3, 2, 1))
    cov_b = np.clip(cov_b, 0, 1)

    img = paper * (1 - cov_a[..., None]) + paper * (ink_a / 255) * cov_a[..., None]
    img = img * (1 - cov_b[..., None]) + img * (ink_b / 255) * cov_b[..., None]
    # second ink A pass: thin outline of the glyph, off-register
    gsd = glyph_sd(g)
    outline = np.clip(1 - np.abs(shift(gsd, -0.012 * S, 0.008 * S) + 0.012 * S) / 3, 0, 1)
    img = img * (1 - outline[..., None] * 0.8) + img * (ink_a / 255) * outline[..., None] * 0.8

    c = Canvas()
    c.shadow(tile, 0.004 * S, 0.01 * S, 0.01 * S, 0.3)
    c.over(np.clip(img, 0, 255), tile)
    return c.image(out)


# -------------------------------------------------------------- 9. bauhaus

BH = ["#E63946", "#F4C430", "#1D3557", "#111111", "#F1E9DA", "#2A9D8F"]


def bauhaus(svg, name, out=256):
    rng = rng_of(name)
    sd = sd_roundrect(0.45, 0.02)
    tile = cov(sd)
    cream = rgb("#F1E9DA")
    img = np.zeros((S, S, 3)) + cream
    x0, y0 = CX - 0.45 * S, CY - 0.45 * S
    q = 0.45 * S
    cols = [rgb(c) for c in BH if c != "#F1E9DA"]
    for qi in range(4):
        ox, oy = x0 + (qi % 2) * q, y0 + (qi // 2) * q
        col = cols[int(rng.random() * len(cols))]
        kind = int(rng.random() * 4)
        lx, ly = XX - ox, YY - oy
        inq = (lx >= 0) & (lx < q) & (ly >= 0) & (ly < q)
        if kind == 0:     # quarter circle from a corner
            cxq, cyq = [(0, 0), (q, 0), (0, q), (q, q)][int(rng.random() * 4)]
            m = cov(q - np.hypot(lx - cxq, ly - cyq))
        elif kind == 1:   # half circle
            m = cov(q / 2 - np.hypot(lx - q / 2, ly - q)) if rng.random() < 0.5 else \
                cov(q / 2 - np.hypot(lx, ly - q / 2))
        elif kind == 2:   # triangle
            m = cov((q - lx - ly) / math.sqrt(2)) if rng.random() < 0.5 else cov((lx - ly) / math.sqrt(2))
        else:             # full square
            m = np.ones((S, S))
        img = img * (1 - (m * inq)[..., None]) + col * (m * inq)[..., None]
    disc_col = cols[int(rng.random() * len(cols))]
    disc = cov(0.29 * S - np.hypot(XX - CX, YY - CY))
    img = img * (1 - disc[..., None]) + disc_col * disc[..., None]
    lum = disc_col @ np.array([0.3, 0.59, 0.11])
    gcol = rgb("#111111") if lum > 140 else cream
    g = glyph(svg, 0.36, 1.7)
    img = img * (1 - g[..., None]) + gcol * g[..., None]
    c = Canvas()
    c.shadow(tile, 0.006 * S, 0.014 * S, 0.014 * S, 0.4)
    c.over(img, tile)
    return c.image(out)


# --------------------------------------------------------------- 10. graffiti

SPRAY = ["#FF2E63", "#08D9D6", "#FFDE03", "#7CFC00", "#FF6F00", "#B388FF"]


def graffiti(svg, name, out=256):
    rng = rng_of(name)
    paint = rgb(pick(name, SPRAY))
    splash_c = rgb(pick(name, SPRAY, 2))
    chip = (noise(seed_of(name) + 9, 18, 3) - 0.5) * 0.025 * S
    sd = sd_roundrect(0.45, 0.03) + chip
    wall = cov(sd)
    conc = 128 + 40 * (noise(seed_of(name) + 1, 60, 4) - 0.5) + 30 * (noise(seed_of(name) + 2, 3, 2) - 0.5)
    pores = (noise(seed_of(name) + 3, 4, 1) < 0.08).astype(float)
    conc = conc - pores * 40
    img = np.repeat(conc[..., None], 3, axis=2) * np.array([1.0, 0.98, 0.95])

    speck = (rng.random((S, S)) < 0.08).astype(float)
    splash = blur(cov(0.3 * S - np.hypot(XX - CX + 0.06 * S, YY - CY + 0.04 * S)
                      + (noise(seed_of(name) + 4, 50, 2) - 0.5) * 0.2 * S), 0.03 * S)
    splash = np.clip(splash * 0.75 + speck * splash * 0.3, 0, 1)
    img = img * (1 - splash[..., None]) + splash_c * splash[..., None]

    g = glyph(svg, 0.58, 1.8)
    gsd = glyph_sd(g)
    # drips from the lowest points of the strokes
    drip = np.zeros((S, S))
    cols_on = np.where(g.max(axis=0) > 0.5)[0]
    for _ in range(4):
        if not len(cols_on):
            break
        x = int(rng.choice(cols_on))
        ys_ = np.where(g[:, x] > 0.5)[0]
        y_end = ys_.max()
        L = int((0.06 + rng.random() * 0.14) * S)
        wdt = 0.007 * S
        seg = cov(wdt - np.abs(XX - x)) * ((YY > y_end - 5) & (YY < y_end + L))
        drop = cov(wdt * 1.7 - np.hypot(XX - x, YY - (y_end + L)))
        drip = np.maximum(drip, np.maximum(seg, drop))
    over_spray = blur(g, 0.012 * S) * 0.6 * (rng.random((S, S)) < 0.5)
    outline = cov(gsd + 0.014 * S)
    img = img * (1 - outline[..., None] * 0.95) + np.array([15, 15, 18]) * outline[..., None] * 0.95
    body = np.clip(np.maximum(g, drip), 0, 1)
    img = img * (1 - over_spray[..., None]) + paint * over_spray[..., None]
    img = img * (1 - body[..., None]) + paint * body[..., None]
    shine = np.clip(1 - np.abs(gsd - 0.6 * np.percentile(gsd[gsd > 0], 90)) / 2.5, 0, 1) \
        * (np.abs(((XX - YY) % 70)) < 30) * g
    img = img * (1 - shine[..., None] * 0.8) + 255 * shine[..., None] * 0.8

    c = Canvas()
    c.shadow(wall, 0.006 * S, 0.016 * S, 0.016 * S, 0.5)
    c.over(np.clip(img, 0, 255), wall)
    return c.image(out)


STYLES = {
    "neubrutal": ("Необрутализм", neubrutal),
    "sticker": ("Наклейки", sticker),
    "glitch": ("Глитч", glitch),
    "stained": ("Витраж", stained_glass),
    "bricks": ("Конструктор", bricks),
    "patch": ("Нашивка", patch),
    "sketch": ("Скетч в тетради", sketch),
    "riso": ("Ризограф", risograph),
    "bauhaus": ("Баухаус", bauhaus),
    "graffiti": ("Граффити", graffiti),
}
