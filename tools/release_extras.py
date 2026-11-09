"""Files the app reads from the latest GitHub release: styles.json and a
preview strip per style.

usage: python tools/release_extras.py <dist_dir>    (after build_pack.py for every style)

styles.json lists every style with its APK and preview file name plus the
release version, so the app can offer new styles and updates by itself.
"""

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from build_pack import PACKS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ["whatsapp", "telegram", "generic_camera", "google_chrome", "youtube", "generic_settings"]


def version():
    props = dict(line.split("=", 1) for line in (ROOT / "version.properties").read_text().splitlines()
                 if "=" in line and not line.startswith("#"))
    return props["versionName"].strip(), int(props["versionCode"])


def strip(style: str, out: Path):
    draw = ROOT / PACKS[style]["out"] / "res/drawable-nodpi"
    cell, pad = 150, 14
    W = len(SAMPLE) * cell + (len(SAMPLE) + 1) * pad
    H = cell + 2 * pad
    t = np.linspace(0, 1, W)[None, :, None]
    bg = np.array([236, 230, 220]) * (1 - t) + np.array([196, 214, 236]) * t   # shows see-through styles
    img = Image.fromarray(np.repeat(bg, H, axis=0).astype(np.uint8), "RGB").convert("RGBA")
    for i, name in enumerate(SAMPLE):
        icon = Image.open(draw / f"{name}.png").convert("RGBA").resize((cell, cell), Image.LANCZOS)
        img.alpha_composite(icon, (pad + i * (cell + pad), pad))
    img.convert("RGB").save(out, optimize=True)


def main():
    dist = Path(sys.argv[1])
    dist.mkdir(parents=True, exist_ok=True)
    name, code = version()
    reg = json.loads((ROOT / "pack/styles.json").read_text(encoding="utf-8"))
    styles = []
    for s in reg["styles"]:
        if s["id"] not in PACKS:
            continue
        strip(s["id"], dist / f"preview-{s['id']}.png")
        styles.append(dict(s, apk=f"My-Icon-{s['id']}.apk", preview=f"preview-{s['id']}.png"))
    doc = {"version": name, "code": code, "styles": styles}
    (dist / "styles.json").write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print("styles.json:", name, code, [s["id"] for s in styles])


if __name__ == "__main__":
    main()
