"""Generate all icon pack resources for one pack (Android product flavor).

usage: python tools/build_pack.py [--pack graphite|noir] [--size 256] [--jobs N]

All styles share the app list, glyphs and app id (they are flavors of one app):
  graphite  tools/iconstyle.py    android/app/src/generated
  noir      tools/style_noir.py   android/app/src/generated-noir
  glass     tools/style_glass.py  android/app/src/generated-glass
  white     tools/style_white.py  android/app/src/generated-white

Reads  pack/selection.json, third_party/lawnicons/{svgs,appfilter.xml}, pack/glyphs/*.svg
Writes <out>/res/drawable-nodpi/*.png      icons + iconback/iconupon/iconmask
       <out>/res/xml/{appfilter,drawable}.xml and the same in <out>/assets/
       <out>/res/values/iconpack.xml       icon list for older launchers
       <out>/res/mipmap-*/ic_launcher*.png the pack's own launcher icon
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import re
import shutil
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, str(Path(__file__).parent))
import iconstyle  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LAWN = ROOT / "third_party/lawnicons"
GLYPHS = ROOT / "pack/glyphs"

OWN_DRAWABLE = "my_icon_pack"
ACTIVITY = "com.myicon.graphite.MainActivity"   # Java namespace is shared by all flavors
PACKS = {
    # every style is a flavor of the same app (com.myicon.graphite);
    # scale: size of unthemed app icons inside the frame
    "graphite": dict(out="android/app/src/generated", scale=0.58, launcher_bg="#242424"),
    "noir": dict(out="android/app/src/generated-noir", scale=0.56, launcher_bg="#1B1B1B",
                 module="style_noir"),
    "glass": dict(out="android/app/src/generated-glass", scale=0.6, launcher_bg="#E6E8EC",
                  module="style_glass"),
    "white": dict(out="android/app/src/generated-white", scale=0.5, launcher_bg="#E6E7E9",
                  module="style_white"),
}
APP_ID = "com.myicon.graphite"

_renderer = None


def _init():
    global _renderer
    _renderer = iconstyle.Renderer()


def _style_module(pack: str):
    """Style module of a pack (None for graphite, which uses iconstyle.Renderer)."""
    name = PACKS[pack].get("module")
    if not name:
        return None
    import importlib
    return importlib.import_module(name)


def render_icon(pack: str, name: str, size: int):
    """One themed icon as a PIL RGBA image."""
    mod = _style_module(pack)
    if mod is not None:
        fn = next(iter(mod.STYLES.values()))[1]
        return fn(glyph_svg(name), name, size)
    global _renderer
    if _renderer is None:
        _init()
    return iconstyle.finish(_renderer.compose(iconstyle.glyph_from_svg(glyph_svg(name))), size)


def frame_layers(pack: str, size: int):
    """iconback, iconupon, iconmask for apps the pack has no icon for."""
    mod = _style_module(pack)
    if mod is not None:
        return mod.back(size), mod.upon(size), mod.mask(size)
    r = iconstyle.Renderer()
    return r.render(None, size), r.upon(size), r.mask(size)


def glyph_svg(name: str) -> str:
    p = GLYPHS / f"{name}.svg"
    if not p.exists():
        p = LAWN / "svgs" / f"{name}.svg"
    return p.read_text(encoding="utf-8")


def android_string(text: str) -> str:
    t = escape(text).replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')
    if t[:1] in ("@", "?"):
        t = "\\" + t
    return t


def save_png(img, path: Path):
    """Grey icons are stored as grey+alpha (half the size); tinted ones as RGBA."""
    import numpy as np
    from PIL import Image
    arr = np.asarray(img, dtype=np.int16)
    vis = arr[..., 3] > 8
    spread = np.abs(arr[..., 0] - arr[..., 1]) + np.abs(arr[..., 1] - arr[..., 2])
    if not vis.any() or spread[vis].max() <= 6:
        r, g, b, a = img.split()
        Image.merge("LA", (r, a)).save(path, optimize=True)
    else:
        img.save(path, optimize=True)


def _render_one(args):
    pack, name, size, out_dir = args
    save_png(render_icon(pack, name, size), Path(out_dir) / f"{name}.png")
    return name


def render_launcher_icon(pack: str, res: Path):
    import numpy as np
    work = np.asarray(render_icon(pack, OWN_DRAWABLE, iconstyle.WORK), dtype=np.float64)
    for q, px in {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}.items():
        d = res / f"mipmap-{q}"
        d.mkdir(parents=True, exist_ok=True)
        icon = iconstyle.finish(work, px)
        icon.save(d / "ic_launcher.png", optimize=True)
        # adaptive foreground: 108dp canvas, our tile spans ~74dp of it
        fg_px = px * 108 // 48
        from PIL import Image
        fg = Image.new("RGBA", (fg_px, fg_px), (0, 0, 0, 0))
        inner = iconstyle.finish(work, int(fg_px * 0.70))
        o = (fg_px - inner.width) // 2
        fg.alpha_composite(inner, (o, o))
        fg.save(d / "ic_launcher_foreground.png", optimize=True)
    any_dir = res / "mipmap-anydpi-v26"
    any_dir.mkdir(parents=True, exist_ok=True)
    adaptive = ('<?xml version="1.0" encoding="utf-8"?>\n'
                '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
                '    <background android:drawable="@color/launcher_background" />\n'
                '    <foreground android:drawable="@mipmap/ic_launcher_foreground" />\n'
                '</adaptive-icon>\n')
    (any_dir / "ic_launcher.xml").write_text(adaptive)
    (any_dir / "ic_launcher_round.xml").write_text(adaptive)
    vals = res / "values"
    vals.mkdir(parents=True, exist_ok=True)
    (vals / "launcher_colors.xml").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
        f'    <color name="launcher_background">{PACKS[pack]["launcher_bg"]}</color>\n</resources>\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", choices=sorted(PACKS), default="graphite")
    ap.add_argument("--out", default=None)
    ap.add_argument("--size", type=int, default=256)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    ap.add_argument("--limit", type=int, default=0, help="render only N icons (testing)")
    args = ap.parse_args()
    cfg = PACKS[args.pack]
    own_component = f"{APP_ID}/{ACTIVITY}"

    out = Path(args.out) if args.out else ROOT / cfg["out"]
    if out.exists():
        shutil.rmtree(out)
    res = out / "res"
    draw = res / "drawable-nodpi"
    xml = res / "xml"
    assets = out / "assets"
    for d in (draw, xml, assets, res / "values"):
        d.mkdir(parents=True, exist_ok=True)

    sel = json.loads((ROOT / "pack/selection.json").read_text(encoding="utf-8"))
    cats = sel["categories"]
    names = sel["names"]
    drawables = []
    for c in cats:
        for d in c["drawables"]:
            if d not in drawables:
                drawables.append(d)
    if OWN_DRAWABLE not in drawables:
        drawables.append(OWN_DRAWABLE)
    calendar = [f"themed_icon_calendar_{i}" for i in range(1, 32)] if sel.get("calendar") else []
    todo = drawables + calendar
    if args.limit:
        todo = todo[:args.limit]

    # ---- icons
    with mp.Pool(args.jobs) as pool:
        for i, _ in enumerate(pool.imap_unordered(
                _render_one, [(args.pack, n, args.size, str(draw)) for n in todo], chunksize=4), 1):
            if i % 50 == 0 or i == len(todo):
                print(f"  rendered {i}/{len(todo)}", flush=True)

    # ---- iconback / iconupon / iconmask for apps without an icon
    back, upon, mask = frame_layers(args.pack, args.size)
    save_png(back, draw / "iconback.png")
    save_png(upon, draw / "iconupon.png")
    save_png(mask, draw / "iconmask.png")

    # ---- appfilter.xml
    lawn_af = (LAWN / "appfilter.xml").read_text(encoding="utf-8")
    entries = re.findall(r"^\s*(<(?:item|calendar) [^>]*/>)\s*$", lawn_af, flags=re.M)
    rendered = set(todo)
    keep = []
    for e in entries:
        m = re.search(r'(?:drawable|prefix)="([^"]+)"', e)
        d = m.group(1)
        if e.startswith("<calendar"):
            if calendar and calendar[0] in rendered:
                keep.append(e)
        elif d in rendered:
            keep.append(e)
    af = ['<?xml version="1.0" encoding="utf-8"?>',
          "<!-- My-Icon. Glyphs: Lawnicons (Apache-2.0), see NOTICE -->",
          "<resources>",
          '  <iconback img1="iconback" />',
          '  <iconmask img1="iconmask" />',
          '  <iconupon img1="iconupon" />',
          f'  <scale factor="{cfg["scale"]}" />',
          f'  <item component="ComponentInfo{{{own_component}}}" drawable="{OWN_DRAWABLE}" '
          f'name="My-Icon" />']
    af += ["  " + e for e in keep]
    af.append("</resources>")
    af_text = "\n".join(af) + "\n"
    (xml / "appfilter.xml").write_text(af_text, encoding="utf-8")
    (assets / "appfilter.xml").write_text(af_text, encoding="utf-8")

    # ---- drawable.xml (icon picker)
    dx = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>", "  <version>1</version>"]
    for c in cats:
        items = [d for d in c["drawables"] if d in rendered]
        if not items:
            continue
        dx.append(f"  <category title={quoteattr(c['title'])} />")
        dx += [f'  <item drawable="{d}" />' for d in items]
    if calendar and calendar[0] in rendered:
        dx.append('  <category title="Календарь" />')
        dx += [f'  <item drawable="{d}" />' for d in calendar]
    dx.append("</resources>")
    dx_text = "\n".join(dx) + "\n"
    (xml / "drawable.xml").write_text(dx_text, encoding="utf-8")
    (assets / "drawable.xml").write_text(dx_text, encoding="utf-8")

    # ---- res/values/iconpack.xml (ADW/Apex style list + names)
    order = [d for d in drawables + calendar if d in rendered]
    vx = ['<?xml version="1.0" encoding="utf-8"?>', "<resources>",
          '  <string-array name="icon_pack" translatable="false">']
    vx += [f"    <item>{d}</item>" for d in order]
    vx += ["  </string-array>", '  <string-array name="icon_names" translatable="false">']
    vx += [f"    <item>{android_string(names.get(d, d))}</item>" for d in order]
    vx += ["  </string-array>", "</resources>"]
    (res / "values" / "iconpack.xml").write_text("\n".join(vx) + "\n", encoding="utf-8")

    render_launcher_icon(args.pack, res)

    total = sum(p.stat().st_size for p in draw.glob("*.png"))
    print(f"icons: {len(rendered)}, appfilter entries: {len(keep) + 1}, "
          f"png total: {total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
