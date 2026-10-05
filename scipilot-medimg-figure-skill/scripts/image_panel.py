"""
scipilot-medimg-figure-skill :: image_panel.py
==============================================
JSON-spec driven medical-image panels at final journal size.

    python image_panel.py spec.json            # render + self-check + export
    python image_panel.py spec.json --preview  # render + self-check only

    from image_panel import render
    result = render("spec.json")               # -> RenderResult(fig, plan, issues, files)

Design rules (see references/image_panels.md):
- coordinates in the spec are always *native image pixels* (x = column, y = row);
- crops physically remove pixels (nothing hidden outside the frame is exported);
- base images and masks are drawn with interpolation="none" (no smoothing);
- masks are never resized; heatmaps are resized onto the native grid with a declared method;
- heatmaps must declare their normalisation; there is no default;
- a scale bar is drawn only when pixel spacing is supplied;
- any FAIL stops the export: only the preview and the report are written.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
from dataclasses import dataclass, field

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import patheffects as pe  # noqa: E402
from matplotlib.colors import Normalize, to_rgba  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

from image_io import (SpecError, ShapeMismatchError, apply_window,  # noqa: E402
                      compute_window, load_heatmap, load_image, load_mask,
                      resize_heatmap)
from setup_style import setup_style  # noqa: E402

SKILL_VERSION = "scipilot-medimg-figure-skill 0.1.0 (base scipilot-figure-skill 2.1.0 @43098dd)"
MARKER = "scipilot-medimg:image-panel"

JOURNAL_WIDTH_IN = {
    "nature": {"single": 3.5, "double": 7.2},
    "science": {"single": 2.2, "onehalf": 4.7, "double": 7.2},
    "ieee": {"single": 3.5, "double": 7.16},
    "general": {"single": 3.5, "double": 7.0},
}
ROLE_STYLE = {  # colour + line style (redundant encoding), Okabe-Ito
    "truth": ("#009E73", "-", "Ground truth"),
    "prediction": ("#E69F00", (0, (3.0, 1.6)), "Prediction"),
    "other": ("#56B4E9", (0, (1.0, 1.2)), "Contour"),
}
ZOOM_COLORS = ["#56B4E9", "#F0E442", "#CC79A7"]  # distinct from truth/prediction
CLASS_PALETTE = ["#E69F00", "#56B4E9", "#009E73", "#F0E442", "#0072B2",
                 "#D55E00", "#CC79A7", "#999999"]
ALLOWED_CMAPS = {"inferno", "magma", "viridis", "cividis"}
CORNERS = ("upper right", "upper left", "lower right", "lower left")
TEXT_HALO = [pe.withStroke(linewidth=1.6, foreground="black")]


@dataclass
class RenderResult:
    fig: object
    plan: dict
    issues: list = field(default_factory=list)
    files: list = field(default_factory=list)


# --------------------------------------------------------------------------- spec
def _load_spec(spec) -> tuple[dict, str | None]:
    if isinstance(spec, dict):
        return spec, None
    with open(spec, encoding="utf-8") as f:
        return json.load(f), os.path.abspath(spec)


def _req(d: dict, key: str, where: str):
    if key not in d or d[key] is None:
        raise SpecError(f"{where}: missing required field '{key}'")
    return d[key]


def _box(v, where: str) -> tuple[int, int, int, int]:
    if not (isinstance(v, (list, tuple)) and len(v) == 4 and all(float(t).is_integer() for t in v)):
        raise SpecError(f"{where}: expected [x, y, w, h] in integer native pixels, got {v!r}")
    x, y, w, h = (int(t) for t in v)
    if w <= 0 or h <= 0:
        raise SpecError(f"{where}: width/height must be positive, got {v!r}")
    return x, y, w, h


def _inside(box, outer, where: str):
    x, y, w, h = box
    ox, oy, ow, oh = outer
    if x < ox or y < oy or x + w > ox + ow or y + h > oy + oh:
        raise SpecError(f"{where}: region {list(box)} is not inside {list(outer)}")


def _point_inside(pt, outer, where: str):
    ox, oy, ow, oh = outer
    if not (ox <= pt[0] < ox + ow and oy <= pt[1] < oy + oh):
        raise SpecError(f"{where}: point {list(pt)} is outside the displayed region {list(outer)}")


# ------------------------------------------------------------------------ loading
def _prepare(spec: dict) -> tuple[dict, list]:
    """Load every file, validate geometry, compute windows and heatmap scales."""
    issues: list[tuple[str, str]] = []
    grid = _req(spec, "grid", "spec")
    rows = grid.get("rows") or []
    cols = grid.get("cols") or []
    n_rows = int(grid.get("n_rows", len(rows)))
    n_cols = int(grid.get("n_cols", len(cols)))
    if n_rows <= 0 or n_cols <= 0:
        raise SpecError("grid: give 'rows'/'cols' label lists or 'n_rows'/'n_cols'")
    if rows and len(rows) != n_rows or cols and len(cols) != n_cols:
        raise SpecError("grid: label list length does not match n_rows/n_cols")
    label_maps = spec.get("label_maps", {})
    groups = spec.get("groups", {})

    cells = []
    seen = set()
    for i, c in enumerate(_req(spec, "cells", "spec")):
        where = f"cells[{i}]"
        r, k = int(_req(c, "row", where)), int(_req(c, "col", where))
        if not (0 <= r < n_rows and 0 <= k < n_cols):
            raise SpecError(f"{where}: row/col ({r},{k}) outside {n_rows}x{n_cols} grid")
        if (r, k) in seen:
            raise SpecError(f"{where}: grid position ({r},{k}) used twice")
        seen.add((r, k))
        img = load_image(_req(c, "image", where), f"{where}.image")
        H, W = img.shape
        crop = _box(c["crop"], f"{where}.crop") if c.get("crop") else (0, 0, W, H)
        _inside(crop, (0, 0, W, H), f"{where}.crop")
        cell = {"spec": c, "where": where, "row": r, "col": k, "image": img, "crop": crop,
                "group": c.get("group"), "overlays": []}
        for j, ov in enumerate(c.get("overlays", [])):
            ow = f"{where}.overlays[{j}]"
            typ = _req(ov, "type", ow)
            if typ in ("contour", "fill", "label_mask"):
                arr, sha = load_mask(_req(ov, "path", ow), (H, W), ow)
                rec = {"type": typ, "spec": ov, "where": ow, "mask": arr, "sha256": sha}
                if typ == "label_mask":
                    lm_ref = _req(ov, "label_map", ow)
                    lm = label_maps.get(lm_ref) if isinstance(lm_ref, str) else lm_ref
                    if not lm:
                        raise SpecError(f"{ow}: label_map {lm_ref!r} not defined in spec.label_maps")
                    classes = {int(v): d for v, d in _req(lm, "classes", ow + ".label_map").items()}
                    ignore = {int(v) for v in lm.get("ignore", [])}
                    present = {int(v) for v in np.unique(arr)}
                    unknown = sorted(present - set(classes) - ignore)
                    if unknown:
                        raise SpecError(
                            f"{ow}: mask values {unknown} have no class name in label_map "
                            f"{lm_ref!r}. Every value must be named or listed in 'ignore' - "
                            "class meanings are never guessed.")
                    show = [int(v) for v in ov.get("show", sorted(classes))]
                    for n, v in enumerate(sorted(classes)):
                        classes[v] = dict(classes[v])
                        if "name" not in classes[v]:
                            raise SpecError(f"{ow}: class {v} lacks 'name'")
                        classes[v].setdefault("color", CLASS_PALETTE[n % len(CLASS_PALETTE)])
                    rec.update(classes=classes, ignore=ignore, show=show,
                               label_map_name=lm_ref if isinstance(lm_ref, str) else "inline",
                               label_map_source=lm.get("source"))
                cell["overlays"].append(rec)
            elif typ == "heatmap":
                hdef = dict(spec.get("heatmap_defaults", {}))
                hdef.update(ov)
                raw, sha = load_heatmap(_req(hdef, "path", ow), ow, hdef.get("key"))
                norm = hdef.get("normalize")
                if norm not in ("per_image", "shared", "fixed"):
                    raise SpecError(f"{ow}: 'normalize' must be declared as per_image | shared | "
                                    "fixed (no default: it changes what the colours mean)")
                up = _req(hdef, "upsample", ow)
                cmap = hdef.get("cmap", "inferno")
                if cmap not in ALLOWED_CMAPS:
                    raise SpecError(f"{ow}: cmap {cmap!r} not allowed; use one of "
                                    f"{sorted(ALLOWED_CMAPS)} (perceptually uniform)")
                full = resize_heatmap(raw, (H, W), up)
                excl_vals = hdef.get("exclude_image_values")
                excluded = None
                if excl_vals:
                    base = img.array if img.array.ndim == 2 else img.array.min(axis=2)
                    excluded = np.isin(base, [float(v) for v in excl_vals])
                cell["overlays"].append({
                    "type": "heatmap", "spec": hdef, "where": ow, "raw_shape": raw.shape,
                    "raw_min": float(raw.min()), "raw_max": float(raw.max()), "full": full,
                    "sha256": sha, "normalize": norm, "upsample": up, "cmap": cmap,
                    "norm_group": hdef.get("norm_group", "default"), "excluded": excluded,
                    "excluded_fraction": float(excluded.mean()) if excluded is not None else 0.0})
            else:
                raise SpecError(f"{ow}: unknown overlay type {typ!r}")
        cells.append(cell)

    # ---- group windows (computed on full native images of the group)
    windows = {}
    for name in {c["group"] for c in cells}:
        members = [c for c in cells if c["group"] == name]
        gspec = groups.get(name, {}).get("intensity", {"mode": "none"}) if name else {"mode": "none"}
        if name and name not in groups:
            raise SpecError(f"group {name!r} used by cells but not defined in spec.groups")
        windows[name] = compute_window([m["image"].array for m in members], gspec,
                                       f"groups[{name}]")
    for c in cells:
        c["window"] = windows[c["group"]]
        disp, clipped = apply_window(c["image"].array, c["window"], c["image"].bit_depth)
        x, y, w, h = c["crop"]
        c["display"] = disp[y:y + h, x:x + w]
        c["clipped_fraction"] = clipped

    # ---- heatmap scales
    scales = {}
    heat = [(c, o) for c in cells for o in c["overlays"] if o["type"] == "heatmap"]
    for c, o in heat:
        if o["normalize"] == "shared":
            key = ("shared", o["norm_group"], o["cmap"])
            s = scales.setdefault(key, {"vmin": math.inf, "vmax": -math.inf, "members": 0})
            s["vmin"] = min(s["vmin"], float(o["full"].min()))
            s["vmax"] = max(s["vmax"], float(o["full"].max()))
            s["members"] += 1
    for key, s in scales.items():
        if s["vmin"] >= 0:
            s["vmin"] = 0.0
    for c, o in heat:
        f = o["full"]
        spec_o = o["spec"]
        if o["normalize"] == "per_image":
            lo = 0.0 if f.min() >= 0 else float(f.min())
            hi = float(f.max())
            key = ("per_image", "relative", o["cmap"])
            scales.setdefault(key, {"vmin": 0.0, "vmax": 1.0, "members": 0})["members"] += 1
        elif o["normalize"] == "shared":
            key = ("shared", o["norm_group"], o["cmap"])
            lo, hi = scales[key]["vmin"], scales[key]["vmax"]
        else:
            lo, hi = _req(spec_o, "vmin", o["where"]), _req(spec_o, "vmax", o["where"])
            key = ("fixed", f"{lo}:{hi}", o["cmap"])
            scales.setdefault(key, {"vmin": float(lo), "vmax": float(hi), "members": 0})["members"] += 1
        o["scale_key"], o["lo"], o["hi"] = key, float(lo), float(hi)
        o["flat"] = not hi > lo
        if o["flat"]:
            issues.append(("INFO", f"{o['where']}: heatmap is flat (min = max = {hi:g}); "
                                   "nothing is overlaid - disclose in caption"))
            o["norm"] = np.zeros_like(f)
        else:
            o["norm"] = np.clip((f - lo) / (hi - lo), 0, 1)
        if o["normalize"] != "per_image" and "value_label" not in spec_o:
            raise SpecError(f"{o['where']}: shared/fixed heatmaps need 'value_label' "
                            "(what the colour scale measures, e.g. 'Grad-CAM (E2 log-p)')")
        x, y, w, h = c["crop"]
        o["norm_crop"] = o["norm"][y:y + h, x:x + w]
        o["excluded_crop"] = (o["excluded"][y:y + h, x:x + w]
                              if o["excluded"] is not None else None)
    for c in cells:
        x, y, w, h = c["crop"]
        for o in c["overlays"]:
            if "mask" in o:
                o["mask_crop"] = o["mask"][y:y + h, x:x + w]
    return {"cells": cells, "n_rows": n_rows, "n_cols": n_cols, "rows": rows, "cols": cols,
            "scales": scales, "windows": windows}, issues


# ------------------------------------------------------------------------- layout
def _text_lines(labels) -> int:
    return max((str(t).count("\n") + 1 for t in labels if t), default=0)


def _legend_entries(prep: dict) -> list:
    entries, keys = [], set()
    for c in prep["cells"]:
        for o in c["overlays"]:
            s = o["spec"]
            if o["type"] == "contour":
                col, ls, default = ROLE_STYLE[s.get("role", "other")]
                col = s.get("color", col)
                lab = s.get("label", default)
                k = ("line", lab, col, str(ls))
                if k not in keys:
                    keys.add(k)
                    entries.append(Line2D([], [], color=col, ls=ls, lw=1.2, label=lab,
                                          path_effects=[pe.Stroke(linewidth=2.2, foreground="white"),
                                                        pe.Normal()]))
            elif o["type"] == "fill":
                lab = _req(s, "label", o["where"])
                col = _req(s, "color", o["where"])
                k = ("patch", lab, col)
                if k not in keys:
                    keys.add(k)
                    entries.append(Patch(facecolor=to_rgba(col, s.get("alpha", 0.45)),
                                         edgecolor=col, lw=0.6, label=lab))
            elif o["type"] == "label_mask":
                present = {int(v) for v in np.unique(o["mask_crop"])}
                for v in o["show"]:
                    if v not in present or v in o["ignore"]:
                        continue
                    d = o["classes"][v]
                    k = ("patch", d["name"], d["color"])
                    if k not in keys:
                        keys.add(k)
                        entries.append(Patch(facecolor=to_rgba(d["color"], s.get("alpha", 0.45)),
                                             edgecolor=d["color"], lw=0.6, label=d["name"]))
    return entries


def _layout(spec: dict, prep: dict) -> dict:
    fig_s = spec.get("figure", {})
    journal = fig_s.get("journal", "nature")
    width = fig_s.get("width", "double")
    if isinstance(width, (int, float)):
        W = float(width)
    else:
        try:
            W = JOURNAL_WIDTH_IN[journal][width]
        except KeyError as e:
            raise SpecError(f"figure.width {width!r} unknown for journal {journal!r}") from e
    fs = float(plt.rcParams["font.size"])
    line = fs * 1.3 / 72.0
    margin = 0.03
    gap = float(spec["grid"].get("gap_mm", 1.0)) / 25.4
    row_w = (_text_lines(prep["rows"]) * line + 0.05) if prep["rows"] else 0.0
    col_h = (_text_lines(prep["cols"]) * line + 0.04) if prep["cols"] else 0.0
    letter_h = (fs + 2) / 72.0 + 0.03 if fig_s.get("panel_label") else 0.0
    n_cbar = len(prep["scales"])
    cbar_w = n_cbar * 0.62 if n_cbar else 0.0
    legend = _legend_entries(prep)
    ncol = int(spec.get("legend", {}).get("ncol", min(len(legend), 4) or 1))
    leg_rows = math.ceil(len(legend) / ncol) if legend else 0
    legend_h = leg_rows * fs * 1.55 / 72.0 + 0.06 if legend else 0.0

    n_r, n_c = prep["n_rows"], prep["n_cols"]
    grid_w = W - 2 * margin - row_w - cbar_w
    colw = (grid_w - gap * (n_c - 1)) / n_c
    if colw <= 0.2:
        raise SpecError(f"figure too narrow for {n_c} columns (column width {colw:.2f} in)")
    by_pos = {(c["row"], c["col"]): c for c in prep["cells"]}
    row_h = []
    for r in range(n_r):
        hs = [by_pos[(r, k)]["crop"][3] * colw / by_pos[(r, k)]["crop"][2]
              for k in range(n_c) if (r, k) in by_pos]
        if not hs:
            raise SpecError(f"grid row {r} has no cells")
        row_h.append(max(hs))
    grid_h = sum(row_h) + gap * (n_r - 1)
    H = margin * 2 + letter_h + col_h + grid_h + legend_h
    return {"W": W, "H": H, "fs": fs, "margin": margin, "gap": gap, "row_w": row_w,
            "col_h": col_h, "letter_h": letter_h, "cbar_w": cbar_w, "colw": colw,
            "row_h": row_h, "grid_h": grid_h, "legend": legend, "legend_ncol": ncol,
            "legend_h": legend_h, "journal": journal}


# ------------------------------------------------------------------------ drawing
def _extent(x, y, w, h):
    return (x - 0.5, x + w - 0.5, y + h - 0.5, y - 0.5)


def _draw_layers(ax, cell, region):
    """Draw base image + overlays for `region` (native [x,y,w,h], inside the crop)."""
    cx, cy, _, _ = cell["crop"]
    x, y, w, h = region
    sl = (slice(y - cy, y - cy + h), slice(x - cx, x - cx + w))
    base = cell["display"][sl]
    ext = _extent(x, y, w, h)
    if base.ndim == 2:
        ax.imshow(base, cmap="gray", vmin=0, vmax=1, interpolation="none", extent=ext,
                  aspect="auto")
    else:
        ax.imshow(base, interpolation="none", extent=ext, aspect="auto")
    xs, ys = np.arange(x, x + w), np.arange(y, y + h)
    for o in cell["overlays"]:
        s = o["spec"]
        if o["type"] == "heatmap":
            if o["flat"]:
                continue
            n = o["norm_crop"][sl]
            rgba = plt.get_cmap(o["cmap"])(n)
            rgba[..., 3] = np.where(n >= float(s.get("transparent_below", 0.0)),
                                    float(s.get("alpha", 0.5)), 0.0)
            if o["excluded_crop"] is not None:
                rgba[..., 3][o["excluded_crop"][sl]] = 0.0
            ax.imshow(rgba, interpolation="none", extent=ext, aspect="auto")
        elif o["type"] in ("fill", "label_mask"):
            m = o["mask_crop"][sl]
            rgba = np.zeros(m.shape + (4,))
            alpha = float(s.get("alpha", 0.45))
            if o["type"] == "fill":
                region_m = np.isin(m, s["values"]) if "values" in s else m > 0
                rgba[region_m] = to_rgba(s["color"], alpha)
                draw = "fill"
                contours = []
            else:
                draw = s.get("draw", "fill")
                contours = []
                for v in o["show"]:
                    if v in o["ignore"]:
                        continue
                    sel = m == v
                    if draw in ("fill", "both"):
                        rgba[sel] = to_rgba(o["classes"][v]["color"], alpha)
                    if draw in ("contour", "both") and sel.any() and not sel.all():
                        contours.append((sel, o["classes"][v]["color"]))
            if draw in ("fill", "both"):
                ax.imshow(rgba, interpolation="none", extent=ext, aspect="auto")
            for sel, col in contours:
                ax.contour(xs, ys, sel.astype(float), levels=[0.5], colors=[col],
                           linewidths=0.8)
        elif o["type"] == "contour":
            m = o["mask_crop"][sl]
            sel = np.isin(m, s["values"]) if "values" in s else m > 0
            if sel.any() and not sel.all():
                col, ls, _ = ROLE_STYLE[s.get("role", "other")]
                cs = ax.contour(xs, ys, sel.astype(float), levels=[0.5],
                                colors=[s.get("color", col)], linewidths=float(s.get("lw", 0.9)),
                                linestyles=[ls])
                cs.set_path_effects([pe.Stroke(linewidth=float(s.get("lw", 0.9)) + 1.1,
                                               foreground="white"), pe.Normal()])
    ax.set_xlim(x - 0.5, x + w - 0.5)
    ax.set_ylim(y + h - 0.5, y - 0.5)
    ax.set_xticks([]); ax.set_yticks([])


def _corner_xy(corner, bw, bh, cw, ch, pad):
    """Lower-left of a bw x bh box placed in `corner` of a cw x ch cell (inches)."""
    if corner not in CORNERS:
        raise SpecError(f"corner must be one of {CORNERS}, got {corner!r}")
    x = cw - bw - pad if "right" in corner else pad
    y = ch - bh - pad if "upper" in corner else pad
    return x, y


def _overlap(a, b):
    return not (a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1])


def _draw_cell(fig, cell, rect_in, L, plan_cell, issues):
    W, H = L["W"], L["H"]
    x0, y0, cw, ch = rect_in
    ax = fig.add_axes([x0 / W, y0 / H, cw / W, ch / H])
    ax.set_axis_off()
    _draw_layers(ax, cell, cell["crop"])
    cxp, cyp, cwp, chp = cell["crop"]
    s_in = cw / cwp  # inches per native pixel
    plan_cell.update(ax=ax, rect_in=rect_in, in_per_px=s_in, ppi=1.0 / s_in, zooms=[])
    s = cell["spec"]
    fs = L["fs"]

    # --- zoom insets
    for zi, z in enumerate(s.get("zooms", [])):
        zw = f"{cell['where']}.zooms[{zi}]"
        box = _box(_req(z, "box", zw), zw + ".box")
        _inside(box, cell["crop"], zw + ".box")
        factor = _req(z, "factor", zw)
        if not (isinstance(factor, int) and factor >= 2):
            raise SpecError(f"{zw}: factor must be an integer >= 2 (display is exactly factor x)")
        color = z.get("color", ZOOM_COLORS[zi % len(ZOOM_COLORS)])
        bw, bh = box[2] * s_in * factor, box[3] * s_in * factor
        if bw > 0.62 * cw or bh > 0.62 * ch:
            raise SpecError(f"{zw}: inset {bw:.2f}x{bh:.2f} in does not fit the "
                            f"{cw:.2f}x{ch:.2f} in cell; lower 'factor' or the box size")
        src = ((box[0] - cxp) * s_in, (chp - (box[1] - cyp) - box[3]) * s_in,
               box[2] * s_in, box[3] * s_in)
        pad = 0.03
        corners = [z["corner"]] if z.get("corner", "auto") != "auto" else list(CORNERS)
        placed = None
        taken = [p["inset_rect_rel"] for p in plan_cell["zooms"]]
        for cn in corners:
            ix, iy = _corner_xy(cn, bw, bh, cw, ch, pad)
            cand = (ix, iy, bw, bh)
            if not _overlap(cand, src) and not any(_overlap(cand, t) for t in taken):
                placed = (cn, cand)
                break
        if placed is None:
            raise SpecError(f"{zw}: no corner leaves the zoomed region and other insets visible; "
                            "set 'corner' explicitly after moving the box or lowering 'factor'")
        cn, (ix, iy, _, _) = placed
        ax.add_patch(Rectangle((box[0] - 0.5, box[1] - 0.5), box[2], box[3], fill=False,
                               edgecolor=color, lw=1.0, zorder=5))
        iax = fig.add_axes([(x0 + ix) / W, (y0 + iy) / H, bw / W, bh / H])
        _draw_layers(iax, cell, box)
        for sp in iax.spines.values():
            sp.set_visible(True); sp.set_edgecolor(color); sp.set_linewidth(1.2)
        plan_cell["zooms"].append({"box": list(box), "factor": factor, "color": color,
                                   "corner": cn, "inset_ax": iax, "rect_color": color,
                                   "inset_rect_rel": (ix, iy, bw, bh)})

    # --- arrows
    for ai, a in enumerate(s.get("arrows", [])):
        aw = f"{cell['where']}.arrows[{ai}]"
        to = _req(a, "to", aw)
        _point_inside(to, cell["crop"], aw + ".to")
        off = a.get("offset", [-0.12 * cwp, -0.12 * cwp])
        frm = (to[0] + off[0], to[1] + off[1])
        col = a.get("color", "white")
        ann = ax.annotate(
            a.get("text", ""), xy=(to[0], to[1]), xytext=frm, textcoords="data",
            fontsize=a.get("fontsize", max(6.0, fs - 1)), color=col, ha="center", va="center",
            arrowprops=dict(arrowstyle="-|>,head_length=0.45,head_width=0.25", color=col, lw=1.1,
                            shrinkA=2, shrinkB=2.5,
                            path_effects=[pe.Stroke(linewidth=2.3, foreground="black"), pe.Normal()]),
            zorder=6, annotation_clip=False)
        ann.set_path_effects(TEXT_HALO)

    # --- scale bar
    sb = s.get("scale_bar")
    plan_cell["scale_bar"] = None
    if sb:
        spacing = sb.get("pixel_spacing_um")
        if spacing in (None, 0):
            issues.append(("INFO", f"{cell['where']}.scale_bar: no pixel_spacing_um supplied - "
                                   "scale bar omitted (never inferred)"))
        else:
            length_um = float(_req(sb, "length_um", cell["where"] + ".scale_bar"))
            L_px = length_um / float(spacing)
            if L_px > 0.5 * cwp:
                issues.append(("WARN", f"{cell['where']}.scale_bar: bar spans "
                                       f"{L_px / cwp:.0%} of the crop width; choose a shorter length"))
            thick_px = (1.6 / 72.0) / s_in
            pad_px = 0.05 / s_in
            corner = sb.get("corner", "lower right")
            bx = cxp + cwp - pad_px - L_px if "right" in corner else cxp + pad_px
            by = cyp + chp - pad_px - thick_px if "lower" in corner else cyp + pad_px + 0.12 / s_in
            ax.add_patch(Rectangle((bx - 0.5, by - 0.5), L_px, thick_px, facecolor="white",
                                   edgecolor="black", lw=0.4, zorder=6))
            label = sb.get("label", f"{length_um:g} \u00b5m")
            t = ax.text(bx - 0.5 + L_px / 2, by - 0.5 - 0.02 / s_in, label, ha="center",
                        va="bottom", color="white", fontsize=max(6.0, fs - 1), zorder=6)
            t.set_path_effects(TEXT_HALO)
            plan_cell["scale_bar"] = {"pixel_spacing_um": float(spacing), "length_um": length_um,
                                      "length_px": L_px, "axis": sb.get("axis", "x")}

    # --- corner text
    ct = s.get("corner_text")
    if ct:
        corner = ct.get("corner", "upper left")
        xa = 0.03 if "left" in corner else 0.97
        ya = 0.97 if "upper" in corner else 0.03
        t = ax.text(xa, ya, _req(ct, "text", cell["where"] + ".corner_text"),
                    transform=ax.transAxes, ha="left" if "left" in corner else "right",
                    va="top" if "upper" in corner else "bottom", color="white",
                    fontsize=max(6.0, fs - 1), zorder=7)
        t.set_path_effects(TEXT_HALO)
    return ax


def _draw(spec, prep, L, issues):
    fig = plt.figure(figsize=(L["W"], L["H"]))
    W, H, m, gap = L["W"], L["H"], L["margin"], L["gap"]
    fs = L["fs"]
    grid_left = m + L["row_w"]
    grid_top = H - m - L["letter_h"] - L["col_h"]
    by_pos = {(c["row"], c["col"]): c for c in prep["cells"]}
    plan = {"cells": [], "colorbars": [], "legend": None, "layout": {
        k: v for k, v in L.items() if k not in ("legend",)}}

    # column labels
    for k, lab in enumerate(prep["cols"]):
        if lab:
            cx = grid_left + k * (L["colw"] + gap) + L["colw"] / 2
            fig.text(cx / W, (grid_top + 0.03) / H, lab, ha="center", va="bottom", fontsize=fs)
    # rows
    ytop = grid_top
    for r in range(prep["n_rows"]):
        rh = L["row_h"][r]
        if prep["rows"] and prep["rows"][r]:
            fig.text((m + L["row_w"] - 0.05) / W, (ytop - rh / 2) / H, prep["rows"][r],
                     rotation=90, ha="right", va="center", fontsize=fs, multialignment="center")
        for k in range(prep["n_cols"]):
            cell = by_pos.get((r, k))
            if cell is None:
                continue
            cw = L["colw"]
            ch = cell["crop"][3] * cw / cell["crop"][2]
            x0 = grid_left + k * (cw + gap)
            y0 = ytop - rh + (rh - ch) / 2
            pc = {"where": cell["where"], "row": r, "col": k, "crop": list(cell["crop"])}
            _draw_cell(fig, cell, (x0, y0, cw, ch), L, pc, issues)
            plan["cells"].append(pc)
        ytop -= rh + gap
    grid_bottom = ytop + gap

    # colorbars (right of grid, stacked)
    if prep["scales"]:
        n = len(prep["scales"])
        cb_x = grid_left + L["colw"] * prep["n_cols"] + gap * (prep["n_cols"] - 1) + 0.08
        slot = (grid_top - grid_bottom) / n
        for i, (key, sc) in enumerate(sorted(prep["scales"].items(), key=lambda kv: str(kv[0]))):
            h = min(slot - 0.12, 1.8)
            y = grid_top - i * slot - (slot - h) / 2 - h
            cax = fig.add_axes([cb_x / W, y / H, 0.08 / W, h / H])
            member = next(o for c in prep["cells"] for o in c["overlays"]
                          if o["type"] == "heatmap" and o["scale_key"] == key)
            sm = plt.cm.ScalarMappable(norm=Normalize(sc["vmin"], sc["vmax"]), cmap=key[2])
            cb = fig.colorbar(sm, cax=cax)
            cb.solids.set_rasterized(False)
            cb.outline.set_linewidth(0.5)
            cb.ax.tick_params(labelsize=max(6.0, fs - 1), length=2, width=0.5)
            if key[0] == "per_image":
                label = member["spec"].get("value_label", "Relative value") + \
                    "\n(each map / own maximum)"
                cb.set_ticks([0, 0.5, 1])
            else:
                label = member["spec"]["value_label"] + (
                    "\n(shared scale)" if key[0] == "shared" else "\n(fixed scale)")
                cb.formatter.set_powerlimits((-2, 3))
                cb.update_ticks()
            cb.set_label(label, fontsize=max(6.0, fs - 1))
            cb.ax.yaxis.get_offset_text().set_fontsize(max(6.0, fs - 1))
            plan["colorbars"].append({"key": list(map(str, key)), "label": label, "ax": cax,
                                      "vmin": sc["vmin"], "vmax": sc["vmax"],
                                      "members": sc["members"]})
    # legend
    if L["legend"]:
        # matplotlib fills legends column-major; reorder so entries read left -> right
        ent, nc = L["legend"], L["legend_ncol"]
        nr = math.ceil(len(ent) / nc)
        order = [ent[r * nc + k] for k in range(nc) for r in range(nr) if r * nc + k < len(ent)]
        leg = fig.legend(handles=order, loc="lower center",
                         bbox_to_anchor=(0.5, m / H), ncol=L["legend_ncol"], frameon=False,
                         fontsize=max(6.0, fs - 1), handlelength=1.8, columnspacing=1.2,
                         borderaxespad=0.0)
        plan["legend"] = {"artist": leg, "labels": [h.get_label() for h in L["legend"]]}
    # panel letter
    letter = spec.get("figure", {}).get("panel_label")
    if letter:
        fig.text(m / W, (H - m) / H, letter, ha="left", va="top", fontsize=fs + 1,
                 fontweight="bold")
    return fig, plan


# ------------------------------------------------------------- provenance/caption
def _provenance(spec, spec_path, prep, plan, L):
    out = {"generator": SKILL_VERSION, "panel_type": "image_panel",
           "created": _dt.datetime.now().isoformat(timespec="seconds"),
           "spec_path": spec_path, "matplotlib": matplotlib.__version__,
           "figure_size_in": [round(L["W"], 4), round(L["H"], 4)], "journal": L["journal"],
           "cells": [], "colorbars": [
               {k: v for k, v in cb.items() if k != "ax"} for cb in plan["colorbars"]],
           "legend": plan["legend"]["labels"] if plan["legend"] else []}
    by_where = {p["where"]: p for p in plan["cells"]}
    for c in prep["cells"]:
        p = by_where[c["where"]]
        img = c["image"]
        rec = {"where": c["where"], "row": c["row"], "col": c["col"],
               "image": {"path": img.path, "sha256": img.sha256, "mode": img.mode,
                         "bit_depth": img.bit_depth, "native_wh": [img.shape[1], img.shape[0]],
                         "notes": img.notes},
               "crop_xywh": list(c["crop"]), "group": c["group"], "intensity_window": c["window"],
               "clipped_fraction": round(c["clipped_fraction"], 6),
               "display_in": [round(p["rect_in"][2], 4), round(p["rect_in"][3], 4)],
               "effective_ppi": round(p["ppi"], 1), "overlays": [],
               "zooms": [{k: v for k, v in z.items() if k not in ("inset_ax", "inset_rect_rel")}
                         for z in p["zooms"]],
               "arrows": c["spec"].get("arrows", []), "scale_bar": p["scale_bar"],
               "corner_text": (c["spec"].get("corner_text") or {}).get("text")}
        for o in c["overlays"]:
            s = {k: v for k, v in o["spec"].items()}
            r = {"type": o["type"], "path": s.get("path"), "sha256": o["sha256"]}
            if o["type"] == "heatmap":
                r.update(key=s.get("key"), raw_shape=list(o["raw_shape"]), raw_min=o["raw_min"],
                         raw_max=o["raw_max"], upsample=o["upsample"],
                         upsampled_to=[img.shape[0], img.shape[1]], normalize=o["normalize"],
                         norm_group=o["norm_group"], scale_lo=o["lo"], scale_hi=o["hi"],
                         cmap=o["cmap"], alpha=s.get("alpha", 0.5),
                         transparent_below=s.get("transparent_below", 0.0), flat=o["flat"],
                         exclude_image_values=s.get("exclude_image_values"),
                         excluded_fraction=round(o["excluded_fraction"], 6))
            elif o["type"] == "label_mask":
                r.update(label_map=o["label_map_name"], label_map_source=o["label_map_source"],
                         shown={str(v): o["classes"][v]["name"] for v in o["show"]},
                         colors={str(v): o["classes"][v]["color"] for v in o["show"]},
                         draw=s.get("draw", "fill"), alpha=s.get("alpha", 0.45))
            else:
                r.update({k: s[k] for k in ("role", "values", "label", "color", "alpha") if k in s})
            rec["overlays"].append(r)
        out["cells"].append(rec)
    return out


def _caption_methods(prov: dict) -> str:
    lines = ["# Figure methods text (draft - verify before use)", ""]
    wins = {}
    for c in prov["cells"]:
        w = c["intensity_window"]
        wins.setdefault(json.dumps(w, sort_keys=True), (w, []))[1].append(c["where"])
    parts = []
    for w, members in wins.values():
        if w["mode"] == "none":
            parts.append("Images are displayed at native intensity without adjustment")
        elif w["mode"] == "percentile":
            parts.append(
                f"a single linear intensity window ({w['lo_percentile']:g}th-{w['hi_percentile']:g}th "
                f"percentile of the pooled group, i.e. {w['lo_value']:.4g}-{w['hi_value']:.4g}) was "
                f"applied uniformly to every image of the group ({len(members)} images)")
        else:
            parts.append(f"a single linear intensity window ({w['lo_value']:g}-{w['hi_value']:g}) "
                         f"was applied uniformly to {len(members)} images")
    lines.append("Intensity: " + "; ".join(parts) + ". No local or non-linear adjustment was made.")
    crops = [c for c in prov["cells"] if c["crop_xywh"][2:] != c["image"]["native_wh"]]
    if crops:
        lines.append(f"Cropping: {len(crops)} panel(s) are cropped from the native image; "
                     "no resampling of image pixels beyond display scaling.")
    roles, classes, heat, fills = set(), {}, [], set()
    for c in prov["cells"]:
        for o in c["overlays"]:
            if o["type"] == "contour":
                roles.add((o.get("label") or ROLE_STYLE[o.get("role", "other")][2],
                           o.get("color") or ROLE_STYLE[o.get("role", "other")][0],
                           o.get("role", "other")))
            elif o["type"] == "label_mask":
                for v, n in o["shown"].items():
                    classes[n] = (o["colors"][v], o.get("label_map_source"))
            elif o["type"] == "fill":
                fills.add((o.get("label"), o.get("color")))
            else:
                heat.append(o)
    if roles:
        lines.append("Contours: " + "; ".join(
            f"{lab} ({col}, {'solid' if role == 'truth' else 'dashed' if role == 'prediction' else 'dotted'})"
            for lab, col, role in sorted(roles)) + ".")
    if classes:
        srcs = {s for _, s in classes.values() if s}
        lines.append("Segmentation classes (semi-transparent fill): " +
                     ", ".join(f"{n} ({c})" for n, (c, _) in classes.items()) + "." +
                     (f" Label encoding: {'; '.join(sorted(srcs))}." if srcs else ""))
    if fills:
        lines.append("Filled regions: " + ", ".join(f"{l} ({c})" for l, c in sorted(fills)) + ".")
    if heat:
        norms = sorted({o["normalize"] for o in heat})
        ups = sorted({f"{tuple(o['raw_shape'])} -> {tuple(o['upsampled_to'])} by {o['upsample']}"
                      for o in heat})
        desc = {"per_image": "each map was scaled to its own maximum, so colours are not "
                             "comparable in magnitude across panels",
                "shared": "maps in the same group share one colour scale, so colours are "
                          "comparable in magnitude within the group",
                "fixed": "a fixed colour range was used"}
        lines.append("Heatmaps: " + "; ".join(desc[n] for n in norms) + ". Resampling: " +
                     "; ".join(ups) + ". Raw value ranges are recorded in the provenance file.")
        tbs = sorted({o["transparent_below"] for o in heat if o["transparent_below"]})
        if tbs:
            lines.append("Heatmap values below " + ", ".join(f"{t:g}" for t in tbs) +
                         " of the colour range are not drawn.")
        exc = sorted({json.dumps(o["exclude_image_values"]) for o in heat
                      if o.get("exclude_image_values")})
        if exc:
            lines.append("Heatmaps are not drawn over image pixels equal to " +
                         " / ".join(exc) + " (acquisition padding, not tissue).")
        flat = [o for o in heat if o["flat"]]
        if flat:
            lines.append(f"{len(flat)} heatmap(s) were flat (constant) and are shown without overlay.")
    zooms = [(c["where"], z) for c in prov["cells"] for z in c["zooms"]]
    if zooms:
        lines.append("Insets: " + "; ".join(f"{z['factor']}x magnification of the region outlined "
                                            f"in the same colour" for _, z in zooms[:1]) +
                     (f" ({len(zooms)} insets in total)" if len(zooms) > 1 else "") +
                     "; nearest-neighbour display, no interpolation.")
    arrows = sum(len(c["arrows"]) for c in prov["cells"])
    if arrows:
        lines.append(f"Arrows ({arrows}) indicate findings described in the text.")
    sbs = [c["scale_bar"] for c in prov["cells"] if c["scale_bar"]]
    if sbs:
        lines.append("Scale bars: " + "; ".join(sorted({f"{s['length_um']:g} \u00b5m at "
                     f"{s['pixel_spacing_um']:g} \u00b5m/pixel ({s['axis']}-axis)" for s in sbs})) + ".")
    else:
        lines.append("No scale bar is shown (pixel spacing not supplied).")
    return "\n\n".join(lines) + "\n"


# ------------------------------------------------------------------------- export
def _export(fig, basename: str, formats: list, dpi: int) -> list:
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo

    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["svg.fonttype"] = "none"
    saved = []
    os.makedirs(os.path.dirname(os.path.abspath(basename)), exist_ok=True)
    for fmt in formats:
        path = f"{basename}.{fmt}"
        if fmt == "pdf":
            fig.savefig(path, metadata={"Keywords": MARKER, "Creator": SKILL_VERSION})
        elif fmt == "svg":
            fig.savefig(path, metadata={"Keywords": [MARKER], "Creator": SKILL_VERSION})
        elif fmt in ("png", "tif", "tiff"):
            fig.savefig(path, dpi=dpi)
            if fmt == "png":
                im = Image.open(path)
                info = PngInfo()
                info.add_text("Keywords", MARKER)
                im.save(path, pnginfo=info, dpi=(dpi, dpi))
        saved.append(path)
    if "png" in formats:
        gray = f"{basename}_grayscale.png"
        Image.open(f"{basename}.png").convert("L").save(gray, dpi=(dpi, dpi))
        saved.append(gray)
    return saved


# ------------------------------------------------------------------------ public
def render(spec, export: bool = True) -> RenderResult:
    from image_qa import audit_image_panel
    from visual_qa import audit_layout, render_preview

    spec, spec_path = _load_spec(spec)
    fig_s = spec.get("figure", {})
    setup_style(journal=fig_s.get("journal", "nature"), lang=fig_s.get("lang", "en"),
                constrained_layout=False)
    prep, issues = _prepare(spec)
    L = _layout(spec, prep)
    fig, plan = _draw(spec, prep, L, issues)
    formats = [f.lower() for f in fig_s.get("formats", ["pdf", "svg", "png"])]
    issues += audit_image_panel(fig, plan, prep, formats)
    issues += audit_layout(fig)

    out_dir = _req(fig_s, "out_dir", "figure")
    name = _req(fig_s, "name", "figure")
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, name)
    files = [render_preview(fig, base + "_preview.png", dpi=200)]
    prov = _provenance(spec, spec_path, prep, plan, L)
    with open(base + ".qa.json", "w", encoding="utf-8") as f:
        json.dump({"issues": issues}, f, ensure_ascii=False, indent=2)
    files.append(base + ".qa.json")
    if export and not any(s == "FAIL" for s, _ in issues):
        files += _export(fig, base, formats, int(fig_s.get("dpi", 600)))
        with open(base + ".provenance.json", "w", encoding="utf-8") as f:
            json.dump(prov, f, ensure_ascii=False, indent=2, default=str)
        with open(base + ".caption_methods.md", "w", encoding="utf-8") as f:
            f.write(_caption_methods(prov))
        files += [base + ".provenance.json", base + ".caption_methods.md"]
    plan["provenance"] = prov
    return RenderResult(fig=fig, plan=plan, issues=issues, files=files)


def _cli() -> int:
    ap = argparse.ArgumentParser(description="Render a medical-image panel from a JSON spec")
    ap.add_argument("spec")
    ap.add_argument("--preview", action="store_true", help="render + self-check, no export")
    args = ap.parse_args()
    try:
        res = render(args.spec, export=not args.preview)
    except (SpecError, ShapeMismatchError) as e:
        print(f"[FAIL] {e}")
        return 2
    for sev, msg in res.issues:
        print(f"  [{sev}] {msg}")
    if not res.issues:
        print("  [PASS] image-panel self-check clean")
    for f in res.files:
        print("wrote", f)
    return 2 if any(s == "FAIL" for s, _ in res.issues) else 0


if __name__ == "__main__":
    sys.exit(_cli())
