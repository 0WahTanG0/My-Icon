"""Copy the Lawnicons subset selected in pack/apps.txt into third_party/lawnicons.

usage: python tools/vendor_lawnicons.py <path to a Lawnicons checkout>

Writes:
  third_party/lawnicons/svgs/*.svg      the glyphs we use
  third_party/lawnicons/appfilter.xml   matching appfilter entries
  third_party/lawnicons/LICENSE         Apache-2.0
  pack/selection.json                   categories -> drawables (for drawable.xml)
"""

import json
import re
import shutil
import subprocess
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path
from xml.sax.saxutils import quoteattr

ROOT = Path(__file__).resolve().parent.parent
ITEM_RE = re.compile(
    r'<(item|calendar) component="ComponentInfo\{([^/}]+)/([^}]*)\}" '
    r'(?:drawable|prefix)="([^"]+)" name="([^"]*)"\s*/>')


def parse_apps(path):
    cats = OrderedDict()
    cur = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            cur = line[1:-1]
            cats.setdefault(cur, [])
            continue
        if cur is None:
            raise SystemExit(f"entry before any [Category]: {line}")
        cats[cur].append(line)
    return cats


def main():
    lawn = Path(sys.argv[1])
    entries = ITEM_RE.findall((lawn / "app/assets/appfilter.xml").read_text(encoding="utf-8"))
    by_pkg = defaultdict(list)
    by_drawable = defaultdict(list)
    for e in entries:
        by_pkg[e[1]].append(e)
        if e[0] == "item":
            by_drawable[e[3]].append(e)

    cats = parse_apps(ROOT / "pack/apps.txt")
    custom_glyphs = {p.stem for p in (ROOT / "pack/glyphs").glob("*.svg")}

    selection = OrderedDict()      # category -> [drawable]
    seen_drawables = set()
    own_maps = []                  # (pkg, act, drawable, name)
    calendars = []                 # calendar entries
    missing = []

    def add(cat, drawable, always=False):
        if drawable in seen_drawables and not always:
            return
        seen_drawables.add(drawable)
        if drawable not in selection.setdefault(cat, []):
            selection[cat].append(drawable)

    for cat, lines in cats.items():
        for line in lines:
            if line.startswith("prefix:"):
                pref = line[len("prefix:"):]
                pk = sorted(p for p in by_pkg if p.startswith(pref))
            elif line.startswith("drawable:"):
                add(cat, line[len("drawable:"):])
                continue
            elif line.startswith("map:"):
                comp, target = line[len("map:"):].split("=", 1)
                drawable, _, label = target.partition("|")
                pkg, act = comp.split("/", 1)
                own_maps.append((pkg, act, drawable.strip(), label.strip()))
                add(cat, drawable.strip(), always=True)
                continue
            else:
                pk = [line]
            if not any(p in by_pkg for p in pk):
                missing.append(line)
                continue
            for p in pk:
                for kind, _pkg, act, drawable, name in by_pkg.get(p, []):
                    if kind == "calendar":
                        calendars.append((p, act, drawable, name))
                    else:
                        add(cat, drawable)

    # every appfilter item that points to one of our drawables (forks, OEM variants)
    items = []
    for d in seen_drawables:
        for kind, pkg, act, drawable, name in by_drawable.get(d, []):
            items.append((pkg, act, drawable, name))
    items.sort(key=lambda x: (x[3].lower(), x[0], x[1]))

    out = ROOT / "third_party/lawnicons"
    if (out / "svgs").exists():
        shutil.rmtree(out / "svgs")
    (out / "svgs").mkdir(parents=True)
    need = set(seen_drawables)
    if calendars:
        need |= {f"themed_icon_calendar_{i}" for i in range(1, 32)}
    copied = 0
    for d in sorted(need):
        if d in custom_glyphs:
            continue
        src = lawn / "svgs" / f"{d}.svg"
        if not src.exists():
            raise SystemExit(f"no Lawnicons svg for drawable {d}")
        shutil.copy(src, out / "svgs" / src.name)
        copied += 1
    shutil.copy(lawn / "LICENSE", out / "LICENSE")

    rev = subprocess.run(["git", "-C", str(lawn), "rev-parse", "HEAD"],
                         capture_output=True, text=True).stdout.strip()
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             f"<!-- Subset of Lawnicons appfilter.xml (Apache-2.0), commit {rev} -->",
             "<resources>"]
    for pkg, act, drawable, name in calendars:
        lines.append(f'  <calendar component="ComponentInfo{{{pkg}/{act}}}" '
                     f'prefix="themed_icon_calendar_" name={quoteattr(name)} />')
    used = set()
    for pkg, act, drawable, name in own_maps + items:
        if (pkg, act) in used:   # own mappings win over Lawnicons ones
            continue
        used.add((pkg, act))
        lines.append(f'  <item component="ComponentInfo{{{pkg}/{act}}}" '
                     f'drawable="{drawable}" name={quoteattr(name)} />')
    lines.append("</resources>")
    (out / "appfilter.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")

    names = {}
    for pkg, act, drawable, name in items + own_maps:
        if name:
            names.setdefault(drawable, name)
    sel = {"lawnicons_commit": rev,
           "categories": [{"title": c, "drawables": sorted(ds, key=lambda d: (names.get(d, d).lower(), d))}
                          for c, ds in selection.items()],
           "names": names,
           "calendar": bool(calendars)}
    (ROOT / "pack/selection.json").write_text(json.dumps(sel, ensure_ascii=False, indent=1) + "\n",
                                              encoding="utf-8")
    print(f"drawables: {len(seen_drawables)}, svgs copied: {copied}, appfilter items: "
          f"{len(items) + len(own_maps)}, calendars: {len(calendars)}")
    if missing:
        print("not in Lawnicons (skipped):", " ".join(missing))


if __name__ == "__main__":
    main()
