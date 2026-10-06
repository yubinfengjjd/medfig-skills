"""Decide whether the active artboard must grow so placed text stays >= the font floor.

The cached runtime scales the whole figure by
    scale = min(artboard_w * max_w_frac / view_w, artboard_h * max_h_frac / view_h)
so the smallest placed font is ``min_source_font * scale``.  When that falls
below the floor, the artboard is enlarged (never shrunk) by the smallest
amount that restores it, preserving the artboard's aspect-neutral fit fractions.

Prints one machine-readable line:
    FIT|action=keep|...      artboard already large enough
    FIT|action=resize|...    caller must enlarge to width x height before drawing
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

# Native postflight may still shave 0.5 pt steps off a label, so the placed
# minimum is targeted slightly above the hard 8 pt floor.
DEFAULT_FLOOR_PT = 8.0
DEFAULT_HEADROOM = 1.05


def min_source_font(cache: dict) -> float:
    sizes = [float(atom["text"]["fontSize"]) for atom in cache.get("atoms", [])
             if atom.get("kind") == "text" and atom.get("text", {}).get("fontSize")]
    if not sizes:
        raise ValueError("geometry cache contains no text atoms")
    return min(sizes)


def plan(view_w: float, view_h: float, min_font: float, artboard_w: float, artboard_h: float,
         max_w_frac: float, max_h_frac: float, floor_pt: float = DEFAULT_FLOOR_PT,
         headroom: float = DEFAULT_HEADROOM) -> dict:
    if min(view_w, view_h, min_font, artboard_w, artboard_h, max_w_frac, max_h_frac) <= 0:
        raise ValueError("all dimensions and fractions must be positive")
    scale = min(artboard_w * max_w_frac / view_w, artboard_h * max_h_frac / view_h)
    placed_min = min_font * scale
    required_scale = floor_pt * headroom / min_font
    result = {
        "min_source_font": round(min_font, 4),
        "current_scale": round(scale, 6),
        "placed_min_font_pt": round(placed_min, 3),
        "required_scale": round(required_scale, 6),
        "floor_pt": floor_pt,
        "from": [round(artboard_w, 3), round(artboard_h, 3)],
    }
    if scale >= required_scale:
        result.update(action="keep", to=result["from"])
        return result
    # Grow each side only as much as its own fit fraction needs; never shrink.
    width = max(artboard_w, math.ceil(required_scale * view_w / max_w_frac))
    height = max(artboard_h, math.ceil(required_scale * view_h / max_h_frac))
    new_scale = min(width * max_w_frac / view_w, height * max_h_frac / view_h)
    result.update(action="resize", to=[float(width), float(height)],
                  new_scale=round(new_scale, 6), new_placed_min_font_pt=round(min_font * new_scale, 3))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True)
    parser.add_argument("--artboard-width", type=float, required=True)
    parser.add_argument("--artboard-height", type=float, required=True)
    parser.add_argument("--max-width-fraction", type=float, required=True)
    parser.add_argument("--max-height-fraction", type=float, required=True)
    parser.add_argument("--floor-pt", type=float, default=DEFAULT_FLOOR_PT)
    parser.add_argument("--report")
    args = parser.parse_args()

    cache = json.loads(Path(args.cache).read_text(encoding="utf-8-sig"))
    view = cache["view_box"]
    result = plan(float(view[2]), float(view[3]), min_source_font(cache),
                  args.artboard_width, args.artboard_height,
                  args.max_width_fraction, args.max_height_fraction, args.floor_pt)
    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("FIT|action={action}|width={w}|height={h}|placed_min_pt={p}|min_source_font={m}".format(
        action=result["action"], w=result["to"][0], h=result["to"][1],
        p=result.get("new_placed_min_font_pt", result["placed_min_font_pt"]), m=result["min_source_font"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
