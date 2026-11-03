"""Ten alternative icon styles, all drawn procedurally (Python + Pillow + NumPy).

Every style is a function  style(svg_text, name, out_size) -> PIL RGBA image.
`name` (the drawable name) seeds per-app colours and textures, so every app
gets its own hue in the colourful styles but stays the same between builds.

Shared helpers come from iconstyle.py (glyph rasterisation, finish()).
"""

from __future__ import annotations

import colorsys
import hashlib
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

import iconstyle
from iconstyle import Style, finish

S = iconstyle.WORK
YY, XX = np.mgrid[0:S, 0:S].astype(np.float64)
CX = CY = (S - 1) / 2

# vivid hues for the colourful styles (fractions of the colour wheel)
HUES = [0.95, 0.58, 0.08, 0.78, 0.45, 0.0, 0.66, 0.14, 0.52, 0.87]


# ----------------------------------------------------------------- helpers

def seed_of(name: str) -> int:
    return int(hashlib.md5(name.encode()).hexdigest()[:8], 16)


def app_hue(name: str) -> float:
    return HUES[seed_of(name) % len(HUES)]


def hsv(h, s, v):
    return np.array(colorsys.hsv_to_rgb(h % 1.0, s, v)) * 255


def hsl(h, s, l):
    return np.array(colorsys.hls_to_rgb(h % 1.0, l, s)) * 255


def blur(a, s):
    if np.isscalar(s) and s <= 0:
        return a
    return ndimage.gaussian_filter(a, s, mode="nearest", truncate=3.0)


def shift(a, dx, dy):
    return iconstyle._shift(a, int(round(dx)), int(round(dy)))


def cov(sd):
    return np.clip(sd + 0.5, 0, 1)


def sd_squircle(half=0.44, n=5.0, cx=CX, cy=CY):
    a = half * S
    nx = np.abs((XX - cx) / a) + 1e-9
    ny = np.abs((YY - cy) / a) + 1e-9
    f = (nx ** n + ny ** n) ** (1 / n)
    g = f ** (1 - n) * np.sqrt(nx ** (2 * n - 2) + ny ** (2 * n - 2))
    return a * (1 - f) / g


def sd_roundrect(half=0.44, r=0.1, cx=CX, cy=CY):
    h, rr = half * S, r * S
    qx = np.abs(XX - cx) - (h - rr)
    qy = np.abs(YY - cy) - (h - rr)
    out = np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - rr
    return -out


def sd_circle(r=0.44, cx=CX, cy=CY):
    return r * S - np.hypot(XX - cx, YY - cy)


def glyph(svg_text, box=0.56, stroke=1.0):
    st = Style(glyph_box=box, glyph_stroke_scale=stroke, tile_offset=0.0)
    return iconstyle.glyph_from_svg(svg_text, st, S)


def glyph_sd(g):
    """Signed distance in px (positive inside) of a coverage mask."""
    inside = g >= 0.5
    d_in = ndimage.distance_transform_edt(inside)
    d_out = ndimage.distance_transform_edt(~inside)
    return blur(np.where(inside, d_in - 0.5, -(d_out - 0.5)), 1.2)


def stroke_halfwidth(gsd):
    inside = gsd[gsd > 0]
    return float(np.percentile(inside, 99)) if inside.size else 10.0


def noise(seed, scale, octaves=4, persistence=0.5):
    """Smooth fBm noise in ~[0,1] with feature size `scale` px."""
    rng = np.random.default_rng(seed)
    total = np.zeros((S, S))
    amp, norm, sc = 1.0, 0.0, scale
    for _ in range(octaves):
        n = max(2, int(S / sc) + 2)
        small = rng.random((n, n))
        big = ndimage.zoom(small, S / (n - 1), order=3)[:S, :S]
        total += amp * big
        norm += amp
        amp *= persistence
        sc /= 2
    t = total / norm
    return (t - t.min()) / (np.ptp(t) + 1e-9)


def light(h, L=(-1.0, -1.0, 1.3), power=24.0):
    gy, gx = np.gradient(h)
    nrm = np.sqrt(gx * gx + gy * gy + 1)
    nx, ny, nz = -gx / nrm, -gy / nrm, 1 / nrm
    L = np.asarray(L) / np.linalg.norm(L)
    H = L + np.array([0, 0, 1.0])
    H /= np.linalg.norm(H)
    diff = nx * L[0] + ny * L[1] + nz * L[2]
    ndh = np.clip(nx * H[0] + ny * H[1] + nz * H[2], 0, 1)
    spec = np.clip(ndh ** power - H[2] ** power, 0, None)
    return diff - L[2], spec, (nx, ny, nz)


def dome(sd, width, height):
    t = np.clip(sd / width, 0, 1)
    return height * np.sqrt(1 - (1 - t) ** 2)


def tube_height(g, sigma, height, sharp=2.2):
    B = blur(g, sigma)
    p = np.clip((B - 0.5) * sharp, 0, 1)
    return height * (1 - (1 - p) ** 2)


def ramp(t, stops):
    """Piecewise-linear colour ramp; stops = [(pos, (r,g,b)), ...]."""
    t = np.clip(t, 0, 1)
    pos = np.array([p for p, _ in stops])
    cols = np.array([c for _, c in stops], dtype=np.float64)
    out = np.zeros(t.shape + (3,))
    for ch in range(3):
        out[..., ch] = np.interp(t, pos, cols[:, ch])
    return out


class Canvas:
    """Straight-alpha float canvas with 'over' and additive compositing."""

    def __init__(self):
        self.rgb = np.zeros((S, S, 3))
        self.a = np.zeros((S, S))

    def over(self, rgb, a):
        rgb = np.broadcast_to(np.asarray(rgb, dtype=np.float64), (S, S, 3)) if np.ndim(rgb) < 3 else rgb
        a = np.clip(a, 0, 1)
        out_a = a + self.a * (1 - a)
        num = rgb * a[..., None] + self.rgb * (self.a * (1 - a))[..., None]
        self.rgb = np.where(out_a[..., None] > 1e-6, num / np.maximum(out_a, 1e-6)[..., None], 0)
        self.a = out_a

    def shadow(self, mask, dx, dy, sigma, alpha, color=(0, 0, 0)):
        self.over(np.asarray(color, dtype=np.float64), blur(shift(mask, dx, dy), sigma) * alpha)

    def image(self, out_size):
        img = np.zeros((S, S, 4))
        img[..., :3] = np.clip(self.rgb, 0, 255)
        img[..., 3] = np.clip(self.a, 0, 1) * 255
        return finish(img, out_size)


def tonemap(x):
    """Soft clip for additive light (0..1 in, 0..1 out)."""
    return 1 - np.exp(-np.maximum(x, 0) * 1.25)


# ----------------------------------------------------------------- 1. neon

def neon(svg, name, out=256):
    hue = app_hue(name)
    col = hsv(hue, 0.85, 1.0) / 255
    sd = sd_roundrect(0.44, 0.11)
    tile = cov(sd)

    # dark brick wall
    bh, bw, mort = 0.074 * S, 0.17 * S, 0.006 * S
    row = np.floor(YY / bh)
    xo = XX + (row % 2) * bw / 2
    colx = np.floor(xo / bw)
    rng = np.random.default_rng(seed_of(name))
    tone = rng.random((int(S / bh) + 2, int(S / bw) + 3))
    brick_tone = tone[row.astype(int), colx.astype(int) % tone.shape[1]]
    in_mortar = (np.minimum(YY % bh, bh - YY % bh) < mort) | (np.minimum(xo % bw, bw - xo % bw) < mort)
    wall = 0.055 + 0.02 * brick_tone + 0.012 * noise(seed_of(name) + 1, 12, 3)
    wall = np.where(in_mortar, 0.03, wall)
    wall = blur(wall, 1.0)
    vign = np.clip(1 - 0.55 * (np.hypot(XX - CX, YY - CY) / (0.62 * S)) ** 2, 0.3, 1)
    lin = np.repeat((wall * vign)[..., None], 3, axis=2) * np.array([0.9, 0.9, 1.15])

    g = glyph(svg, 0.54, 0.8)
    # unlit tube shadow on the wall
    lin *= (1 - 0.7 * blur(shift(g, 0.01 * S, 0.02 * S), 0.006 * S))[..., None]
    halo = (blur(g, 0.010 * S) * 1.1 + blur(g, 0.035 * S) * 0.9 + blur(g, 0.09 * S) * 0.55)
    lin += halo[..., None] * col
    # glow catches the brick edges a little
    lin = tonemap(lin)
    gsd = glyph_sd(g)
    t = np.clip(gsd / max(stroke_halfwidth(gsd), 1), 0, 1)
    core = (col * (1 - 0.85 * t[..., None]) + 0.85 * t[..., None]) * 1.0
    rgb = lin * (1 - g[..., None]) + core * g[..., None]

    # thin metal frame
    frame = np.clip(1 - np.abs(sd - 0.012 * S) / (0.006 * S), 0, 1)
    rgb = rgb * (1 - 0.6 * frame[..., None]) + 0.18 * frame[..., None]

    c = Canvas()
    c.shadow(tile, 0.012 * S, 0.02 * S, 0.02 * S, 0.5)
    c.over(rgb * 255, tile)
    return c.image(out)


# ----------------------------------------------------------- 2. liquid glass

def liquid_glass(svg, name, out=256):
    hue = app_hue(name)
    rng = np.random.default_rng(seed_of(name))
    sd = sd_squircle(0.44, 5.0)
    tile = cov(sd)

    bg = np.zeros((S, S, 3)) + hsv(hue, 0.75, 0.55)
    for k, dh in enumerate((0.0, 0.11, -0.09)):
        bx = CX + (rng.random() - 0.5) * 0.6 * S
        by = CY + (rng.random() - 0.5) * 0.6 * S
        r = (0.22 + 0.1 * rng.random()) * S
        blob = np.exp(-((XX - bx) ** 2 + (YY - by) ** 2) / (2 * r * r))
        bg += blob[..., None] * (hsv(hue + dh, 0.9, 1.0) - bg) * 0.9
    bg = blur(bg.transpose(2, 0, 1), (0, 6, 6)).transpose(1, 2, 0)

    # glass slab: rounded rim refracts the background
    h = dome(sd, 0.09 * S, 0.06 * S)
    gy, gx = np.gradient(h)
    k = 55.0
    coords = [np.clip(YY + gy * k, 0, S - 1), np.clip(XX + gx * k, 0, S - 1)]
    refr = np.stack([ndimage.map_coordinates(bg[..., i], coords, order=1) for i in range(3)], -1)
    refr = refr * 0.88 + 255 * 0.12
    shade, spec, _ = light(h, power=40)
    _, spec2, _ = light(h, L=(1.0, 1.0, 1.3), power=40)   # back light on the far rim
    rgb = refr + shade[..., None] * 95 + spec[..., None] * 230 + spec2[..., None] * 120
    rim = np.clip(1 - np.abs(sd - 0.004 * S) / (0.004 * S), 0, 1)
    rgb += rim[..., None] * 80
    sheen = np.exp(-((YY - (CY - 0.24 * S)) / (0.11 * S)) ** 2) * np.clip((sd - 0.03 * S) / (0.03 * S), 0, 1)
    rgb = rgb * (1 - 0.2 * sheen[..., None]) + 255 * 0.2 * sheen[..., None]
    rgb += (noise(seed_of(name) + 7, 3, 2)[..., None] - 0.5) * 6

    g = glyph(svg, 0.52, 1.1)
    dark = hsv(hue, 0.8, 0.25)
    gsh = blur(shift(g, 0.006 * S, 0.016 * S), 0.014 * S) * 0.45
    rgb = rgb * (1 - gsh[..., None]) + dark * gsh[..., None]
    hg = tube_height(g, 0.006 * S, 0.012 * S)
    gshade, gspec, _ = light(hg, power=30)
    gcol = 246 + gshade[..., None] * 60 + gspec[..., None] * 60
    rgb = rgb * (1 - 0.94 * g[..., None]) + gcol * 0.94 * g[..., None]

    c = Canvas()
    c.shadow(tile, 0, 0.03 * S, 0.035 * S, 0.45, hsv(hue, 0.8, 0.3))
    c.over(np.clip(rgb, 0, 255), tile)
    return c.image(out)


# --------------------------------------------------------------- 3. black gold

GOLD = [(0.0, (38, 22, 6)), (0.3, (120, 78, 22)), (0.55, (196, 146, 58)),
        (0.78, (240, 206, 120)), (1.0, (255, 246, 214))]


def black_gold(svg, name, out=256):
    sd = sd_squircle(0.44, 4.6)
    tile = cov(sd)
    ring_c, ring_w = 0.042 * S, 0.016 * S
    ring = np.clip(1 - ((sd - ring_c) / ring_w) ** 2, 0, 1)
    ring_mask = np.clip((ring_w - np.abs(sd - ring_c)) / 1.5 + 0.5, 0, 1)
    h_ring = 0.016 * S * np.sqrt(ring)

    g = glyph(svg, 0.52, 1.25)
    h_g = tube_height(g, 0.006 * S, 0.016 * S, 2.6)
    h_edge = dome(sd, 0.012 * S, 0.006 * S)
    h = h_ring + h_g + h_edge
    shade, spec, _ = light(h, power=18)

    # brushed metal: noise stretched horizontally
    brushed = ndimage.gaussian_filter(np.random.default_rng(5).random((S, S)), (0.6, 30))
    brushed = (brushed - brushed.mean()) / (brushed.std() + 1e-9)
    I = 0.58 + 1.05 * shade + 0.9 * spec + 0.035 * brushed + 0.12 * ((CX - XX + CY - YY) / S)
    gold = ramp(I, GOLD)

    leather = noise(seed_of(name) + 11, 5, 3)
    base = 13 + 6 * (leather[..., None] - 0.5) + 6 * (0.5 - YY / S)[..., None]
    bshade, bspec, _ = light(h_edge, power=30)
    black = base + bshade[..., None] * 40 + bspec[..., None] * 25

    gm = np.clip(np.maximum(ring_mask, np.clip(g * 1.0, 0, 1)), 0, 1)
    # glyph shadow and warm reflected light on the black
    gsh = blur(shift(g, 0.008 * S, 0.012 * S), 0.01 * S)
    black = black * (1 - 0.6 * gsh[..., None]) + blur(g, 0.03 * S)[..., None] * np.array([40, 26, 6])
    rgb = black * (1 - gm[..., None]) + gold * gm[..., None]

    c = Canvas()
    c.shadow(tile, 0.01 * S, 0.02 * S, 0.025 * S, 0.6)
    c.over(rgb, tile)
    return c.image(out)


# ------------------------------------------------------------------ 4. marble

COPPER = [(0.0, (60, 26, 14)), (0.35, (150, 80, 46)), (0.6, (205, 128, 86)),
          (0.85, (246, 196, 160)), (1.0, (255, 236, 220))]


def marble(svg, name, out=256):
    sd = sd_squircle(0.44, 4.0)
    tile = cov(sd)
    sdn = seed_of(name)
    turb = noise(sdn + 1, 300, 3, 0.45)
    clouds = noise(sdn + 2, 300, 3)
    ang = (sdn % 360) / 360 * math.pi
    u = (XX * math.cos(ang) + YY * math.sin(ang)) / S
    p1 = np.abs(np.sin((u * 1.6 + turb * 1.8) * math.pi))
    p2 = np.abs(np.sin((u * 3.4 - turb * 2.2 + 0.3) * math.pi))
    veins = 0.5 * np.exp(-(p1 / 0.045) ** 2) + 0.2 * np.exp(-(p2 / 0.02) ** 2) + 0.16 * np.exp(-(p1 / 0.2) ** 2)
    veins = blur(veins, 1.2)
    base = np.array([238, 236, 231]) - (clouds[..., None] - 0.5) * 18
    vein_col = np.array([118, 120, 128])
    m = base * (1 - veins[..., None]) + vein_col * veins[..., None]

    h = dome(sd, 0.03 * S, 0.02 * S)
    shade, spec, _ = light(h, power=70)
    m = m + shade[..., None] * 90 + spec[..., None] * 160

    g = glyph(svg, 0.52, 1.05)
    gap = np.clip(blur(g, 1.6) * 1.6 - g, 0, 1)
    brushed = ndimage.gaussian_filter(np.random.default_rng(9).random((S, S)), (0.6, 24))
    brushed = (brushed - brushed.mean()) / (brushed.std() + 1e-9)
    hg = tube_height(g, 0.004 * S, 0.006 * S, 3.0)
    gshade, gspec, _ = light(hg, power=20)
    t = 0.55 + 0.28 * ((CX - XX) + (CY - YY)) / S + 0.7 * gshade + 0.5 * gspec + 0.03 * brushed
    copper = ramp(t, COPPER)
    m = m * (1 - 0.75 * gap[..., None])
    rgb = m * (1 - g[..., None]) + copper * g[..., None]

    c = Canvas()
    c.shadow(tile, 0.008 * S, 0.02 * S, 0.025 * S, 0.35)
    c.over(np.clip(rgb, 0, 255), tile)
    return c.image(out)


# -------------------------------------------------------------------- 5. clay

def clay(svg, name, out=256):
    hue = app_hue(name)
    tc = hsl(hue, 0.62, 0.74)
    sd = sd_squircle(0.43, 4.2, CX - 0.01 * S, CY - 0.012 * S)
    tile = cov(sd)
    h = dome(sd, 0.17 * S, 0.1 * S)

    g = glyph(svg, 0.5, 1.45)
    g = np.clip(g, 0, 1)
    hg = tube_height(g, 0.013 * S, 0.035 * S, 1.7)
    shade_t, spec_t, _ = light(h, power=8)
    tile_rgb = tc + shade_t[..., None] * 120 + spec_t[..., None] * 30
    ao = np.clip(1 - sd / (0.05 * S), 0, 1) * 0.12
    tile_rgb *= (1 - ao[..., None])

    gs = blur(shift(g, 0.012 * S, 0.02 * S), 0.018 * S) * 0.42
    tile_rgb = tile_rgb * (1 - gs[..., None]) + hsl(hue, 0.6, 0.35) * gs[..., None]
    shade_g, spec_g, _ = light(h + hg, power=10)
    gcol = np.array([252, 249, 244]) + shade_g[..., None] * 110 + spec_g[..., None] * 40
    rgb = tile_rgb * (1 - g[..., None]) + gcol * g[..., None]

    c = Canvas()
    c.shadow(tile, 0.02 * S, 0.035 * S, 0.035 * S, 0.5, hsl(hue, 0.55, 0.32))
    c.over(np.clip(rgb, 0, 255), tile)
    return c.image(out)


# ------------------------------------------------------------------- 6. paper

def paper(svg, name, out=256):
    hue = app_hue(name)
    sd0 = sd_squircle(0.44, 4.4)
    theta = np.arctan2(YY - CY, XX - CX)
    rng = np.random.default_rng(seed_of(name))
    grain = (noise(seed_of(name) + 5, 2.5, 2) - 0.5) * 7 + (noise(seed_of(name) + 6, 40, 2) - 0.5) * 6

    c = Canvas()
    c.shadow(cov(sd0), 0.008 * S, 0.02 * S, 0.02 * S, 0.45)
    layers = 6
    for k in range(layers):
        inset = k * 0.05 * S
        wave = 0 if k == 0 else 0.014 * S * np.sin(theta * (4 + k) + rng.random() * 6.28) \
            + 0.008 * S * np.sin(theta * (7 + 2 * k) + rng.random() * 6.28)
        sdk = sd0 - inset + wave
        m = cov(sdk)
        if k > 0:
            c.over(np.zeros(3), blur(shift(m, 0.004 * S, 0.012 * S), 0.011 * S) * 0.42 * (c.a > 0))
        light_k = 0.3 + 0.5 * k / (layers - 1)
        col = hsl(hue + 0.015 * k, 0.62, light_k)
        c.over(col + grain[..., None], m)

    g = glyph(svg, 0.48, 1.2)
    c.over(np.zeros(3), blur(shift(g, 0.006 * S, 0.014 * S), 0.01 * S) * 0.5)
    c.over(np.array([251, 250, 246]) + grain[..., None] * 0.6, g)
    return c.image(out)


# ---------------------------------------------------------------- 7. pixel 8-bit

GB = [(15, 56, 15), (48, 98, 48), (139, 172, 15), (155, 188, 15)]


def pixel(svg, name, out=256):
    N = 32
    g = glyph(svg, 0.6, 1.3)
    small = g.reshape(N, S // N, N, S // N).mean(axis=(1, 3))
    gp = small > 0.38
    img = np.zeros((N, N, 4), dtype=np.uint8)
    lo, hi = 2, 29
    tile = np.zeros((N, N), bool)
    tile[lo:hi + 1, lo:hi + 1] = True
    for (yy, xx) in [(lo, lo), (lo, hi), (hi, lo), (hi, hi)]:
        tile[yy, xx] = False
    for (yy, xx) in [(lo, lo + 1), (lo + 1, lo), (lo, hi - 1), (lo + 1, hi), (hi, lo + 1), (hi - 1, lo),
                     (hi, hi - 1), (hi - 1, hi)]:
        tile[yy, xx] = False
    body = np.zeros((N, N, 3), dtype=np.uint8)
    body[...] = GB[2]
    # dithered light in the top-left
    yy, xx = np.mgrid[0:N, 0:N]
    dither = ((yy + xx) % 2 == 0) & (yy + xx < 22)
    body[dither] = GB[3]
    body[(yy + xx < 14)] = GB[3]
    edge = tile & ~ndimage.binary_erosion(tile)
    inner = ndimage.binary_erosion(tile)
    inner_edge = inner & ~ndimage.binary_erosion(inner)
    body[inner_edge & ((yy + xx) < 31)] = GB[3]
    body[inner_edge & ((yy + xx) >= 31)] = GB[1]
    gp = gp & ndimage.binary_erosion(inner, iterations=1)
    shadow = np.roll(np.roll(gp, 1, 0), 1, 1) & ~gp & inner
    body[shadow] = GB[1]
    body[gp] = GB[0]
    body[edge] = GB[0]
    img[..., :3] = body
    img[..., 3] = np.where(tile, 255, 0)
    # drop shadow, one pixel down-right
    sh = np.roll(np.roll(tile, 1, 0), 1, 1) & ~tile
    img[sh] = (0, 0, 0, 90)
    im = Image.fromarray(img, "RGBA")
    return im.resize((out, out), Image.NEAREST)


# ------------------------------------------------------------- 8. holographic

def hsv_arr(h, s, v):
    h = (h % 1.0) * 6
    i = np.floor(h).astype(int) % 6
    f = h - np.floor(h)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1) * 255


def holo(svg, name, out=256):
    sdn = seed_of(name)
    sd = sd_circle(0.44)
    tile = cov(sd)
    h = dome(sd, 0.05 * S, 0.03 * S)
    g = glyph(svg, 0.5, 1.15)
    hg = tube_height(g, 0.006 * S, 0.02 * S, 2.4)
    shade, spec, (nx, ny, _) = light(h + hg, power=35)
    turb = noise(sdn + 3, 160, 4)
    phase = (0.85 * (XX * 0.7 + YY * 0.45) / S + 0.16 * turb + 0.45 * (nx * 0.6 + ny * 0.9)
             + (sdn % 100) / 100)
    holo_rgb = hsv_arr(phase, 0.34 + 0.08 * turb, np.ones_like(phase)) * 0.78 + 222 * 0.22
    u = (XX - YY) / S
    band = np.exp(-((u - 0.12 + 0.06 * turb) / 0.08) ** 2) + 0.6 * np.exp(-((u + 0.32 + 0.05 * turb) / 0.05) ** 2)
    holo_rgb = holo_rgb * (1 - 0.55 * band[..., None]) + 255 * 0.55 * band[..., None]
    rng = np.random.default_rng(sdn)
    glitter = blur((rng.random((S, S)) > 0.9985).astype(float), 1.2) * 4
    holo_rgb = holo_rgb + glitter[..., None] * 200 + shade[..., None] * 90 + spec[..., None] * 120

    gsh = blur(shift(g, 0.008 * S, 0.016 * S), 0.012 * S) * 0.45
    holo_rgb = holo_rgb * (1 - gsh[..., None])
    gcol = np.array([22, 20, 34]) + spec[..., None] * 0.9 * holo_rgb + np.clip(shade, 0, None)[..., None] * holo_rgb * 0.8
    rgb = holo_rgb * (1 - g[..., None]) + gcol * g[..., None]

    c = Canvas()
    c.shadow(tile, 0.01 * S, 0.025 * S, 0.03 * S, 0.45, (60, 30, 90))
    c.over(np.clip(rgb, 0, 255), tile)
    return c.image(out)


# ------------------------------------------------------------------- 9. magma

LAVA = [(0.0, (30, 6, 4)), (0.22, (120, 14, 4)), (0.45, (220, 50, 6)),
        (0.7, (255, 140, 20)), (0.88, (255, 215, 90)), (1.0, (255, 250, 220))]


def magma(svg, name, out=256):
    sdn = seed_of(name)
    rng = np.random.default_rng(sdn)
    sd = sd_squircle(0.44, 4.2)
    tile = cov(sd)

    # voronoi cracks (F2 - F1), at half resolution for speed
    k2 = 4
    ys, xs = np.mgrid[0:S // k2, 0:S // k2] * k2
    pts = rng.random((22, 2)) * S
    d = np.sort(np.stack([np.hypot(xs - px, ys - py) for px, py in pts]), axis=0)
    crack = ndimage.zoom(d[1] - d[0], k2, order=1)[:S, :S]
    crack_line = np.exp(-(crack / (0.005 * S)) ** 2) * (0.12 + 0.5 * noise(sdn + 4, 120, 2))

    h = dome(sd, 0.02 * S, 0.012 * S)
    shade, spec, _ = light(h, power=60)
    obs = np.zeros((S, S, 3)) + np.array([14, 11, 14])
    refl = np.exp(-(((XX + YY) / S - 0.62) / 0.16) ** 2) * np.clip(1 - (XX + YY) / S * 0.6, 0, 1)
    obs += refl[..., None] * 22 + shade[..., None] * 60 + spec[..., None] * 190

    g = glyph(svg, 0.5, 1.25)
    gsd = glyph_sd(g)
    t = np.clip(gsd / max(stroke_halfwidth(gsd), 1), 0, 1)
    tn = noise(sdn + 8, 40, 3)
    temp = 0.32 + 0.62 * t + 0.32 * (tn - 0.5)
    lava = ramp(temp, LAVA)

    lin = obs / 255
    glow = blur(g, 0.02 * S) * 0.9 + blur(g, 0.06 * S) * 0.6 + blur(crack_line, 0.008 * S) * 0.5
    lin = lin + glow[..., None] * np.array([1.0, 0.32, 0.05])
    lin = lin + crack_line[..., None] * np.array([1.0, 0.45, 0.1]) * 0.9
    # embers
    for _ in range(6):
        ex, ey = rng.random(2) * 0.6 * S + 0.2 * S
        dd = np.hypot(XX - ex, YY - ey)
        lin += (np.exp(-(dd / (0.004 * S)) ** 2) * 1.2 + np.exp(-(dd / (0.015 * S)) ** 2) * 0.25)[..., None] \
            * np.array([1.0, 0.55, 0.15])
    rgb = tonemap(lin) * 255
    rgb = rgb * (1 - g[..., None]) + lava * g[..., None]

    c = Canvas()
    c.shadow(tile, 0.01 * S, 0.022 * S, 0.03 * S, 0.6)
    c.over(np.clip(rgb, 0, 255), tile)
    return c.image(out)


# --------------------------------------------------------------- 10. blueprint

FONT_MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def blueprint(svg, name, out=256):
    sd = sd_roundrect(0.44, 0.07)
    tile = cov(sd)
    base = np.array([18, 74, 168])[None, None] * (1 - YY / S * 0.35)[..., None]
    base = base + (noise(seed_of(name) + 2, 3, 2)[..., None] - 0.5) * 8 \
        + (noise(seed_of(name) + 3, 200, 2)[..., None] - 0.5) * 14

    over = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(over)
    step = S / 32
    for i in range(33):
        v = int(i * step)
        w = 70 if i % 4 else 120
        d.line([(v, 0), (v, S)], fill=w, width=2)
        d.line([(0, v), (S, v)], fill=w, width=2)
    grid = np.asarray(over, dtype=np.float64) / 255 * 0.55

    lines = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(lines)
    c0 = S / 2
    r = 0.34 * S
    for a0 in range(0, 360, 12):   # dashed circle
        d.arc([c0 - r, c0 - r, c0 + r, c0 + r], a0, a0 + 7, fill=170, width=3)
    for xx in range(int(0.1 * S), int(0.9 * S), 40):   # dash-dot cross
        d.line([(xx, c0), (xx + 22, c0)], fill=120, width=2)
        d.line([(c0, xx), (c0, xx + 22)], fill=120, width=2)
    y = 0.86 * S
    x1, x2 = 0.24 * S, 0.76 * S
    d.line([(x1, y), (x2, y)], fill=220, width=3)
    for xx, sgn in ((x1, 1), (x2, -1)):
        d.polygon([(xx, y), (xx + sgn * 26, y - 9), (xx + sgn * 26, y + 9)], fill=220)
        d.line([(xx, y - 30), (xx, y + 14)], fill=220, width=3)
    font = ImageFont.truetype(FONT_MONO, 34)
    label = f"R{(seed_of(name) % 90) + 10}"
    tw = d.textlength(label, font=font)
    d.rectangle([c0 - tw / 2 - 10, y - 22, c0 + tw / 2 + 10, y + 22], fill=0)
    d.text((c0 - tw / 2, y - 21), label, font=font, fill=230)
    tag = name
    for pre in ("generic_", "samsung_", "google_", "themed_icon_"):
        tag = tag.replace(pre, "")
    tag = tag.replace("_", " ").upper()[:16]
    d.text((0.12 * S, 0.1 * S), tag, font=ImageFont.truetype(FONT_MONO, 32), fill=210)
    marks = np.asarray(lines, dtype=np.float64) / 255

    g = glyph(svg, 0.5, 0.6)
    ink = np.clip(grid * 0.5 + marks * 0.8 + blur(g, 0.012 * S) * 0.35, 0, 1)
    rgb = base * (1 - ink[..., None]) + np.array([214, 232, 255]) * ink[..., None]
    rgb = rgb * (1 - g[..., None]) + np.array([248, 252, 255]) * g[..., None]
    frame = np.clip(1 - np.abs(sd - 0.03 * S) / 2.5, 0, 1) + np.clip(1 - np.abs(sd - 0.04 * S) / 1.5, 0, 1)
    rgb = rgb * (1 - frame[..., None] * 0.7) + 230 * frame[..., None] * 0.7

    c = Canvas()
    c.shadow(tile, 0.008 * S, 0.018 * S, 0.02 * S, 0.45)
    c.over(np.clip(rgb, 0, 255), tile)
    return c.image(out)


# ------------------------------------------------------------------ registry

STYLES = {
    "neon": ("Неон", neon),
    "glass": ("Жидкое стекло", liquid_glass),
    "gold": ("Чёрное золото", black_gold),
    "marble": ("Мрамор и медь", marble),
    "clay": ("Пластилин", clay),
    "paper": ("Бумажная аппликация", paper),
    "pixel": ("8-бит", pixel),
    "holo": ("Голограмма", holo),
    "magma": ("Магма", magma),
    "blueprint": ("Чертёж", blueprint),
}
