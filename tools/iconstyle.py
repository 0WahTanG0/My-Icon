"""Graphite "saucer" icon style renderer (Python + Pillow + NumPy).

Every icon is a dark matte squircle tile with a raised frame, a recessed
saucer in the middle and a slightly domed monochrome glyph lying in it.
Light comes from the top-left.  Everything is drawn procedurally from a
height field (frame + saucer + glyph) lit by one directional light, plus
soft cast shadows.  Rendering happens at WORK px and is downsampled.

Glyphs are Lawnicons SVGs (Apache-2.0) rasterised with CairoSVG, or masks
drawn by our own scripts.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

import numpy as np
from PIL import Image
from scipy import ndimage

WORK = 1024  # internal working resolution


@dataclass(frozen=True)
class Style:
    # geometry, as fractions of the canvas
    tile_half: float = 0.435      # half-size of the squircle tile
    tile_offset: float = -0.008   # tile shifted up-left, room for its shadow
    squircle_n: float = 4.4       # superellipse exponent
    edge_round: float = 0.022     # rounding radius of the outer tile edge
    edge_height: float = 0.010
    rim: float = 0.050            # flat frame between tile edge and saucer
    wall: float = 0.062           # sloped saucer wall
    depth: float = 0.017          # saucer depth
    glyph_box: float = 0.56       # size of the 192-unit Lawnicons box
    glyph_stroke_scale: float = 1.18
    glyph_height: float = 0.013   # dome height of the glyph
    # colours (sRGB levels)
    tile_color: float = 46.0      # ~#2A2A2A on average after shading
    floor_color: float = 43.0
    glyph_color: float = 54.0
    gradient: float = 5.0         # top-left lighter, bottom-right darker
    # lighting
    light: tuple = (-1.0, -1.0, 1.3)
    diffuse_gain: float = 95.0
    glyph_diffuse_gain: float = 165.0
    spec_gain: float = 20.0
    glyph_spec_gain: float = 140.0
    spec_power: float = 30.0
    # shadows
    inner_shadow: float = 0.40
    inner_highlight: float = 10.0
    long_shadow_len: float = 0.30
    long_shadow_strength: float = 0.72
    drop_shadow: float = 0.5


STYLE = Style()


# ----------------------------------------------------------------- helpers

def _blur(a: np.ndarray, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return a
    return ndimage.gaussian_filter(a, sigma, mode="constant", truncate=3.0)


def _shift(a: np.ndarray, dx: int, dy: int) -> np.ndarray:
    """Shift image by integer (dx, dy) with zero fill."""
    out = np.zeros_like(a)
    h, w = a.shape
    if abs(dx) >= w or abs(dy) >= h:
        return out
    sx = slice(max(dx, 0), w + min(dx, 0))
    sy = slice(max(dy, 0), h + min(dy, 0))
    tx = slice(max(-dx, 0), w + min(-dx, 0))
    ty = slice(max(-dy, 0), h + min(-dy, 0))
    out[sy, sx] = a[ty, tx]
    return out


def _normalize(v):
    v = np.asarray(v, dtype=np.float64)
    return v / np.linalg.norm(v)


def squircle_sdf(size: int, half: float, offset: float, n: float) -> np.ndarray:
    """Smooth approximate signed distance (px, + inside) of a superellipse."""
    c = (size - 1) / 2 + offset * size
    a = half * size
    y, x = np.mgrid[0:size, 0:size].astype(np.float64)
    nx = np.abs((x - c) / a) + 1e-9
    ny = np.abs((y - c) / a) + 1e-9
    f = (nx ** n + ny ** n) ** (1 / n)
    grad = f ** (1 - n) * np.sqrt(nx ** (2 * n - 2) + ny ** (2 * n - 2))
    return a * (1 - f) / grad


def _scale_strokes(svg: str, k: float) -> str:
    if abs(k - 1) < 1e-3:
        return svg
    svg = re.sub(r'(stroke-width=)"([0-9.]+)"',
                 lambda m: f'{m.group(1)}"{float(m.group(2)) * k:.3f}"', svg)
    svg = re.sub(r'(stroke-width:)\s*([0-9.]+)',
                 lambda m: f"{m.group(1)}{float(m.group(2)) * k:.3f}", svg)
    return svg


def _place(alpha: np.ndarray, style: Style, size: int) -> np.ndarray:
    box = alpha.shape[0]
    canvas = np.zeros((size, size))
    o = int(round((size - box) / 2 + style.tile_offset * size))
    canvas[o:o + box, o:o + box] = alpha
    return canvas


def glyph_from_svg(svg_text: str, style: Style = STYLE, size: int = WORK) -> np.ndarray:
    import cairosvg

    svg_text = _scale_strokes(svg_text, style.glyph_stroke_scale)
    # SVG default miter limit is 4 (cairo uses 10 -> spikes on sharp joins)
    svg_text = svg_text.replace("<svg ", '<svg stroke-miterlimit="4" stroke-linejoin="round" ', 1)
    box = int(round(style.glyph_box * size))
    png = cairosvg.svg2png(bytestring=svg_text.encode(), output_width=box,
                           output_height=box)
    g = Image.open(io.BytesIO(png)).convert("RGBA")
    alpha = np.asarray(g.split()[-1], dtype=np.float64) / 255.0
    return _place(alpha, style, size)


def glyph_from_image(img: Image.Image, style: Style = STYLE, size: int = WORK) -> np.ndarray:
    """Glyph from an L/RGBA image laid out on the 192-unit Lawnicons box."""
    box = int(round(style.glyph_box * size))
    if img.mode != "L":
        img = img.convert("RGBA").split()[-1]
    img = img.resize((box, box), Image.LANCZOS)
    return _place(np.asarray(img, dtype=np.float64) / 255.0, style, size)


# ----------------------------------------------------------------- renderer

class Renderer:
    """Pre-computes everything that does not depend on the glyph."""

    def __init__(self, style: Style = STYLE, size: int = WORK):
        self.s = s = style
        self.S = S = size

        sd = squircle_sdf(S, s.tile_half, s.tile_offset, s.squircle_n)
        self.tile_cov = np.clip(sd + 0.5, 0, 1)

        # height field of tile + saucer
        Re = s.edge_round * S
        t = np.clip(sd / Re, 0, 1)
        h = s.edge_height * S * np.sqrt(1 - (1 - t) ** 2)
        dr = sd - s.rim * S
        u = np.clip(dr / (s.wall * S), 0, 1)
        h = h - s.depth * S * (1 - (1 - u) ** 2)   # concave saucer wall
        h = _blur(h, 1.5)
        self.recess_cov = np.clip(dr + 0.5, 0, 1)
        self.floor_cov = np.clip(dr - s.wall * S * 0.8, 0, 1)
        self.gy, self.gx = np.gradient(h)

        y, x = np.mgrid[0:S, 0:S].astype(np.float64) / S
        self.grad = (0.5 - (x + y) / 2) * 2 * s.gradient

        L = _normalize(s.light)
        Hv = _normalize(L + np.array([0, 0, 1.0]))
        self.L, self.Hv = L, Hv

        shade, spec = self._light(self.gx, self.gy)
        base = s.tile_color + self.grad + (s.floor_color - s.tile_color) * _blur(self.recess_cov, 5)
        col = base + shade * s.diffuse_gain + spec * s.spec_gain

        # inner shadow (top-left) and soft highlight (bottom-right) of the saucer
        off = int(0.020 * S)
        in_sh = self.recess_cov * (1 - _blur(_shift(self.recess_cov, off, off), 0.018 * S))
        in_hl = self.recess_cov * (1 - _blur(_shift(self.recess_cov, -off // 2, -off // 2), 0.010 * S))
        col = col * (1 - s.inner_shadow * in_sh) + s.inner_highlight * in_hl
        self.back_col = col

        self.shadow_clip = np.clip(_blur(self.recess_cov, 0.008 * S) * 1.05, 0, 1)

        doff = int(0.014 * S)
        self.drop = _blur(_shift(self.tile_cov, doff, doff), 0.02 * S) * s.drop_shadow

    def _light(self, gx, gy):
        nrm = np.sqrt(gx * gx + gy * gy + 1)
        nx, ny, nz = -gx / nrm, -gy / nrm, 1 / nrm
        L, Hv = self.L, self.Hv
        diff = nx * L[0] + ny * L[1] + nz * L[2]
        shade = diff - L[2]
        ndh = np.clip(nx * Hv[0] + ny * Hv[1] + nz * Hv[2], 0, 1)
        spec = np.clip(ndh ** self.s.spec_power - Hv[2] ** self.s.spec_power, 0, None)
        return shade, spec

    # ------------------------------------------------------------------
    def _long_shadow(self, glyph: np.ndarray) -> np.ndarray:
        s, S = self.s, self.S
        k2 = 2  # compute at half resolution
        g = glyph.reshape(S // k2, k2, S // k2, k2).mean(axis=(1, 3))
        N = int(s.long_shadow_len * S / k2)
        acc = np.zeros_like(g)
        near = np.zeros_like(g)
        nlen = max(2, int(N * 0.16))
        for k in range(1, N):
            sh = _shift(g, k, k)
            np.maximum(acc, sh * (1 - k / N) ** 1.6, out=acc)
            if k < nlen:
                np.maximum(near, sh * (1 - k / nlen), out=near)
        far = _blur(acc, 0.028 * S / k2)
        near = _blur(near, 0.006 * S / k2)
        sh = np.clip(0.8 * far + 0.5 * near, 0, 1)
        sh = np.asarray(Image.fromarray(sh.astype(np.float32), "F").resize((S, S), Image.BILINEAR))
        return sh

    def compose(self, glyph: np.ndarray | None) -> np.ndarray:
        """Return straight-alpha RGBA float image (0..255) at WORK size."""
        s, S = self.s, self.S
        col = self.back_col.copy()
        if glyph is not None:
            # domed glyph height from a blurred mask: smooth, no EDT banding
            sigma = 0.0075 * S
            B = _blur(glyph, sigma)
            p = np.clip((B - 0.5) * 2.2, 0, 1)
            hg = s.glyph_height * S * (1 - (1 - p) ** 2)
            hg = _blur(hg, 1.2)
            ggy, ggx = np.gradient(hg)
            shade, spec = self._light(self.gx + ggx, self.gy + ggy)

            shadow = self._long_shadow(glyph) * self.shadow_clip * s.long_shadow_strength
            col = col * (1 - shadow * (1 - glyph))

            gcol = (s.glyph_color + self.grad + shade * s.glyph_diffuse_gain
                    + spec * s.glyph_spec_gain)
            col = col * (1 - glyph) + gcol * glyph

        col = np.clip(col, 0, 255)
        a_t = self.tile_cov
        a = a_t + self.drop * (1 - a_t)
        rgb = col * a_t / np.maximum(a, 1e-6)
        img = np.zeros((S, S, 4))
        img[..., 0] = img[..., 1] = img[..., 2] = rgb
        img[..., 3] = a * 255
        return img

    def render(self, glyph: np.ndarray | None, out_size: int = 256) -> Image.Image:
        return finish(self.compose(glyph), out_size)

    def mask(self, out_size: int = 256) -> Image.Image:
        """iconmask: opaque where the original app icon must be erased."""
        S = self.S
        img = np.zeros((S, S, 4))
        img[..., 3] = (1 - _blur(self.floor_cov, 2)) * 255
        return finish(img, out_size)

    def upon(self, out_size: int = 256) -> Image.Image:
        """iconupon: inner shadow of the saucer drawn over the app icon."""
        s, S = self.s, self.S
        off = int(0.020 * S)
        in_sh = self.recess_cov * (1 - _blur(_shift(self.recess_cov, off, off), 0.018 * S))
        img = np.zeros((S, S, 4))
        img[..., 3] = np.clip(in_sh * s.inner_shadow, 0, 1) * 255
        return finish(img, out_size)


def finish(img: np.ndarray, out_size: int) -> Image.Image:
    """Downsample a straight-alpha float RGBA image with premultiplication."""
    a = img[..., 3:4] / 255.0
    pm = np.concatenate([img[..., :3] * a, img[..., 3:4]], axis=-1)
    if out_size != pm.shape[0]:
        bands = [Image.fromarray(pm[..., i].astype(np.float32), "F")
                 .resize((out_size, out_size), Image.LANCZOS) for i in range(4)]
        pm = np.stack([np.asarray(b) for b in bands], axis=-1).astype(np.float64)
    a = np.clip(pm[..., 3:4], 0, 255)
    rgb = np.where(a > 0.5, pm[..., :3] / np.maximum(a, 1e-6) * 255, 0)
    out = np.concatenate([np.clip(rgb, 0, 255), a], axis=-1)
    return Image.fromarray(np.round(out).astype(np.uint8), "RGBA")
