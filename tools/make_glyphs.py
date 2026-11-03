"""Write our own glyph SVGs (192 box, stroke 12, round caps) into pack/glyphs.

usage: python tools/make_glyphs.py pack/glyphs
Used for apps that Lawnicons does not cover.
"""
import math, sys
from pathlib import Path
OUT = Path(sys.argv[1])
TEL = ('M31.072 87.11s65.458-26.771 88.16-36.197c8.702-3.77 38.215-15.837 38.215-15.837s13.621-5.277 12.486 7.541c-.379 5.279-3.406 23.754-6.433 43.738-4.54 28.279-9.459 59.196-9.459 59.196s-.756 8.672-7.188 10.18c-6.433 1.509-15.354-3.781-17.919-4.788-2.565-1.006-28.377-18.098-38.214-26.392-2.65-2.263-5.676-6.788.378-12.066 13.621-12.442 43.526-45.5 43.526-45.5l-66.985 41.352c-4.64 2.13-9.64 2.698-17.404.377-11.351-3.393-25.594-9.917-25.594-9.917s-9.08-5.656 6.433-11.688h-.002Z')

def svg(body, extra=""):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" fill="none" viewBox="0 0 192 192">'
            f'{extra}<g stroke="#000" stroke-width="12" stroke-linecap="round" stroke-linejoin="round">{body}</g></svg>\n')

def pt(cx, cy, r, deg):
    a = math.radians(deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)

def arc(cx, cy, r, d1, d2):
    """Clockwise (screen) arc from angle d1 to d2 (degrees, y down)."""
    x1, y1 = pt(cx, cy, r, d1); x2, y2 = pt(cx, cy, r, d2)
    span = (d2 - d1) % 360
    return f"M{x1:.1f} {y1:.1f}A{r} {r} 0 {1 if span > 180 else 0} 1 {x2:.1f} {y2:.1f}"

def arrowhead(x, y, dx, dy, size=18, spread=40):
    """Chevron with tip at (x,y) pointing along (dx,dy)."""
    a = math.atan2(dy, dx)
    pts = []
    for s in (-1, 1):
        b = a + math.pi + s * math.radians(spread)
        pts.append((x + size * math.cos(b), y + size * math.sin(b)))
    return f"M{pts[0][0]:.1f} {pts[0][1]:.1f}L{x:.1f} {y:.1f}L{pts[1][0]:.1f} {pts[1][1]:.1f}"

g = {}

# Делимобиль: car sharing, car from the front with a key ring above
g["delimobil"] = svg(
    '<path d="M46 98l12-36a12 12 0 0 1 11.4-8.2h53.2A12 12 0 0 1 134 62l12 36"/>'
    '<rect x="28" y="98" width="136" height="46" rx="16"/>'
    '<path d="M50 144v16M142 144v16M82 122h28"/>'
    '<circle cx="56" cy="121" r="6"/><circle cx="136" cy="121" r="6"/>'
    '<path d="M70 76h52"/>')

# Летай: gulls in flight
g["letai"] = svg(
    '<path d="M18 82c26-10 56-4 78 30 22-34 52-40 78-30"/>'
    '<path d="M100 48c10-6 20-4 28 8 8-12 18-14 28-8"/>'
    '<path d="M38 132c8-5 15-3 21 5 6-8 13-10 21-5"/>')

# Мой Налог: receipt with a rouble sign
g["moy_nalog"] = svg(
    '<path d="M46 22h100v148l-16.7-10-16.6 10-16.7-10-16.7 10-16.6-10-16.7 10z"/>'
    '<path d="M84 136V60h22a19 19 0 0 1 0 38H70M70 118h46"/>')

# ЦУПИС: wallet
g["cupis"] = svg(
    '<path d="M146 60V50a12 12 0 0 0-12-12H48a20 20 0 0 0-20 20"/>'
    '<rect x="28" y="58" width="136" height="100" rx="18"/>'
    '<path d="M164 86h-30a22 22 0 0 0 0 44h30"/>'
    '<circle cx="134" cy="108" r="4"/>')

# Яндекс Задания: clipboard with ticked tasks
g["yandex_tasks"] = svg(
    '<path d="M70 34H54a16 16 0 0 0-16 16v106a16 16 0 0 0 16 16h84a16 16 0 0 0 16-16V50a16 16 0 0 0-16-16h-16"/>'
    '<rect x="70" y="22" width="52" height="26" rx="9"/>'
    '<path d="M60 92l10 10 18-20M106 94h28M60 136l10 10 18-20M106 138h28"/>')

# СДЭК: parcel box
g["cdek"] = svg(
    '<path d="M96 22l68 36v76l-68 36-68-36V58z"/>'
    '<path d="M28 58l68 36 68-36M96 94v76"/>'
    '<path d="M62 40l68 36v28"/>')

# EnerGO: power bank with a bolt
g["energo"] = svg(
    '<rect x="52" y="36" width="88" height="136" rx="18"/>'
    '<path d="M78 36V28a6 6 0 0 1 6-6h24a6 6 0 0 1 6 6v8"/>'
    '<path d="M104 66L78 108h36l-26 42"/>')

# Glassify: glass tile with reflections
g["glassify"] = svg(
    '<rect x="28" y="28" width="136" height="136" rx="38"/>'
    '<path d="M60 108l48-48M72 134l62-62"/>')

# Roadside Empire: fuel pump
g["roadside_empire"] = svg(
    '<path d="M42 170V46a18 18 0 0 1 18-18h44a18 18 0 0 1 18 18v124"/>'
    '<path d="M28 170h108"/>'
    '<rect x="58" y="48" width="48" height="36" rx="6"/>'
    '<path d="M122 82h12a10 10 0 0 1 10 10v48a10 10 0 0 0 20 0V74l-16-18"/>')

# SyncTheme: sync arrows around a paint drop
r = 64
up = arc(96, 96, r, 200, 340)          # top arc, left -> right
dn = arc(96, 96, r, 20, 160)           # bottom arc, right -> left
tx, ty = pt(96, 96, r, 340); a = math.radians(340)
h1 = arrowhead(tx, ty, -math.sin(a), math.cos(a))
bx, by = pt(96, 96, r, 160); b = math.radians(160)
h2 = arrowhead(bx, by, -math.sin(b), math.cos(b))
g["synctheme"] = svg(
    f'<path d="{up}"/><path d="{h1}"/><path d="{dn}"/><path d="{h2}"/>'
    '<path d="M96 66s-22 26-22 40a22 22 0 0 0 44 0c0-14-22-40-22-40z"/>')

# Telegram WS Proxy: Telegram plane inside a shield
g["tg_ws_proxy"] = svg(
    '<path d="M96 20l62 22v50c0 40-26 66-62 80-36-14-62-40-62-80V42z"/>'
    f'<g transform="translate(50.5 47) scale(.5)" stroke-width="24"><path d="{TEL}"/></g>')

# VPN админ: globe with a padlock
glob = arc(86, 86, 60, 100, 352)
g["vpn_admin"] = svg(
    f'<path d="{glob}"/>'
    '<path d="M86 26c-16 16-24 38-24 60s8 44 24 60M86 26c16 16 24 38 24 60"/>'
    '<path d="M26 86h70"/>'
    '<rect x="112" y="122" width="58" height="46" rx="10"/>'
    '<path d="M126 122v-10a15 15 0 0 1 30 0v10"/>')

OUT.mkdir(parents=True, exist_ok=True)
for k, v in g.items():
    (OUT / f"{k}.svg").write_text(v)
print(len(g), "glyphs")
