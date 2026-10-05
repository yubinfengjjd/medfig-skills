"""Automatic checks on a schematic image returned by the image model (PNG / JPG).

The visual logic (flow, arrows, labels, structure) is reviewed by eye against references/evaluation.md;
this script only measures what pixels can tell:
  - aspect ratio vs the spec (ERROR when off by > 5 %)
  - effective resolution at the spec width (WARN below 300 dpi: the image is a draft for redrawing)
  - colour: share of saturated pixels far from every palette colour, with the main off-palette colours listed
  - each colour of distinct_groups (e.g. classes) is present (found by hue), how far the drawn colour drifted
    from the requested hex, and whether the drawn class colours stay apart in greyscale (L* difference >= MIN_DL)

Usage: python image_check.py image.png --spec schematic.yaml [--json report.json]
Exit 1 when any ERROR is found. Only reads.
"""
import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import schematic_spec  # noqa: E402

ASPECT_TOL = 0.05
MIN_DPI = 300
MIN_DL = 10.0          # L* difference two class colours need to stay apart in greyscale
SAT_CHROMA = 20.0      # Lab chroma above which a pixel counts as coloured
OFF_DE = 18.0          # ΔE76 from the nearest palette colour above which a coloured pixel is off-palette
OFF_SHARE_WARN = 0.15  # share of coloured pixels that may be off-palette (anti-aliasing, tints)
HUE_TOL = 20.0         # degrees of Lab hue within which a saturated pixel belongs to a distinct colour
MIN_PRESENT = 0.0005   # ... and such pixels make up at least this share of the image
DRIFT_DE = 12.0        # ΔE76 between requested and measured distinct colour above which it has drifted
MAX_SIDE = 900


def hex_rgb(hx):
    hx = hx.lstrip("#")
    return np.array([int(hx[i:i + 2], 16) for i in (0, 2, 4)], dtype=float)


def rgb_to_lab(rgb):
    """(..., 3) sRGB 0-255 -> CIE Lab (D65)."""
    c = np.asarray(rgb, dtype=float) / 255.0
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def tint_distance(pixels, lab, pal_rgb):
    """ΔE76 from each pixel to the nearest palette colour OR one of its tints (mix with white, as image models
    draw light fills and anti-aliased edges). (N,) array."""
    white = np.array([255.0, 255.0, 255.0])
    best = np.full(len(pixels), np.inf)
    for c in pal_rgb:
        v = c - white
        vv = float(v @ v)
        a = np.ones(len(pixels)) if vv == 0 else np.clip(((pixels - white) @ v) / vv, 0.0, 1.0)
        proj = white + a[:, None] * v
        best = np.minimum(best, np.linalg.norm(lab - rgb_to_lab(proj), axis=1))
    return best


def load_pixels(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    s = min(1.0, MAX_SIDE / max(w, h))
    small = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.NEAREST) if s < 1 else im
    return (w, h), np.asarray(small, dtype=float).reshape(-1, 3)


def analyse(size, pixels, spec):
    """Return (issues, report) for one image."""
    issues, rep = [], {}
    w, h = size
    rep["size_px"] = [w, h]
    if spec.get("aspect"):
        ar = w / h
        rep["aspect"] = round(ar, 3)
        rel = abs(ar - spec["aspect"]) / spec["aspect"]
        if rel > ASPECT_TOL:
            issues.append(("ERROR", f"aspect {ar:.3f} vs spec {spec['aspect']:.3f} ({rel:.0%} off): "
                                    "ask for the stated ratio again"))
    if spec.get("width_mm"):
        dpi = w / (float(spec["width_mm"]) / 25.4)
        rep["dpi_at_width"] = round(dpi)
        if dpi < MIN_DPI:
            issues.append(("WARN", f"{dpi:.0f} dpi at {spec['width_mm']} mm: draft resolution, "
                                   "redraw as vectors (Illustrator) for submission"))

    lab = rgb_to_lab(pixels)
    names = list(spec["colours"].values())
    pal_rgb = np.array([hex_rgb(h) for h in spec["colours"]])
    nearest = tint_distance(pixels, lab, pal_rgb)
    chroma = np.hypot(lab[:, 1], lab[:, 2])
    coloured = chroma > SAT_CHROMA
    n_col = int(coloured.sum())
    rep["coloured_share"] = round(n_col / len(lab), 4)
    if n_col:
        off = coloured & (nearest > OFF_DE)
        share = off.sum() / n_col
        rep["off_palette_share"] = round(float(share), 4)
        if share > OFF_SHARE_WARN:
            q = (pixels[off] // 32 * 32 + 16).astype(int)
            vals, cnt = np.unique(q, axis=0, return_counts=True)
            top = [("#%02X%02X%02X" % tuple(v), round(c / n_col, 3)) for v, c in
                   sorted(zip(vals, cnt), key=lambda t: -t[1])[:5]]
            rep["off_palette_top"] = top
            issues.append(("WARN", f"{share:.0%} of coloured pixels are off the palette; main colours {top} -- "
                                   "name the hex value for that element in the next round"))

    # Image models drift colours (a requested #0072B2 comes back as a brighter blue), so each distinct colour is
    # located by hue among saturated pixels, then the measured colour is compared with the requested one.
    hue = np.degrees(np.arctan2(lab[:, 2], lab[:, 1])) % 360
    distinct, measured = {}, {}
    for g in spec["distinct_groups"]:
        for name, hx in spec["palette"][g].items():
            key = f"{g}.{name}"
            t = rgb_to_lab(hex_rgb(hx))
            t_c, t_h = np.hypot(t[1], t[2]), np.degrees(np.arctan2(t[2], t[1])) % 360
            dh = np.abs((hue - t_h + 180) % 360 - 180)
            near = (chroma > max(SAT_CHROMA, 0.5 * t_c)) & (dh < HUE_TOL)
            if near.sum() / len(lab) < MIN_PRESENT:
                issues.append(("WARN", f"{key} ({hx}) not found in the image: check that colour is used "
                                       "for that element"))
                continue
            med = np.median(pixels[near], axis=0)
            de = float(np.linalg.norm(rgb_to_lab(med) - t))
            mhex = "#%02X%02X%02X" % tuple(int(round(v)) for v in med)
            measured[key] = {"requested": str(hx).upper(), "measured": mhex, "delta_e": round(de, 1)}
            distinct[key] = float(rgb_to_lab(med)[0])
            if de > DRIFT_DE:
                issues.append(("WARN", f"{key}: requested {hx}, drawn as about {mhex} (ΔE {de:.0f}); "
                                       "restate the hex value for every element of that class, or recolour "
                                       "in Illustrator"))
    rep["distinct_measured"] = measured
    rep["distinct_L"] = {k: round(v, 1) for k, v in distinct.items()}
    req_L = {f"{g}.{n}": float(rgb_to_lab(hex_rgb(h))[0])
             for g in spec["distinct_groups"] for n, h in spec["palette"][g].items()}
    for (k1, l1), (k2, l2) in combinations(distinct.items(), 2):
        if abs(l1 - l2) >= MIN_DL:
            continue
        if abs(req_L[k1] - req_L[k2]) < MIN_DL:
            msg = (f"greyscale: {k1} and {k2} are close in L* already in the palette "
                   f"({abs(req_L[k1] - req_L[k2]):.1f}); keep a text label next to every class colour")
        else:
            msg = (f"greyscale: {k1} and {k2} differ by L* {abs(l1 - l2):.1f} as drawn (< {MIN_DL:.0f}, palette "
                   f"{abs(req_L[k1] - req_L[k2]):.1f}); colour drift merged them, restate the hex values")
        issues.append(("WARN", msg))
    rep["palette_names"] = names
    return issues, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("image")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    spec = schematic_spec.load(a.spec)
    size, px = load_pixels(a.image)
    issues, rep = analyse(size, px, spec)
    for level, msg in issues:
        print(f"{level}: {msg}")
    print(json.dumps({k: v for k, v in rep.items() if k != "palette_names"}, ensure_ascii=False))
    if a.json:
        rep["issues"] = [list(i) for i in issues]
        Path(a.json).write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    n_err = sum(1 for lv, _ in issues if lv == "ERROR")
    print(f"image_check: {n_err} error(s), {len(issues) - n_err} warning(s)")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main())
