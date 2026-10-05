"""
scipilot-medimg-figure-skill :: image_qa.py
===========================================
Deterministic self-checks for medical-image panels (run by image_panel.render).

Q1  image/mask grid mismatch           -> raised while loading (ShapeMismatchError)
Q2  effective resolution < MIN_PPI     -> WARN
Q3  displayed aspect != native aspect  -> FAIL (stretched image)
Q4  heatmap without colorbar /
    mask or contour without legend     -> FAIL
Q5  zoom box colour != inset border    -> FAIL
Q6  scale bar without pixel spacing    -> INFO (raised while drawing)
Q7  JPEG requested as output           -> FAIL
Perceptual checks (Q9) stay with the AI read-back, see references/visual_review.md.
"""
from __future__ import annotations

from matplotlib.colors import to_hex

MIN_PPI = 300
ASPECT_TOL = 0.01


def _ax_size_in(ax):
    fig = ax.figure
    pos = ax.get_position()
    return pos.width * fig.get_figwidth(), pos.height * fig.get_figheight()


def audit_image_panel(fig, plan: dict, prep: dict, formats: list) -> list[tuple[str, str]]:
    issues: list[tuple[str, str]] = []

    bad = [f for f in formats if f in ("jpg", "jpeg")]
    if bad:
        issues.append(("FAIL", f"output formats {bad}: JPEG is lossy - use pdf/svg/png/tif"))
    unknown = [f for f in formats if f not in ("pdf", "svg", "png", "tif", "tiff", "jpg", "jpeg")]
    if unknown:
        issues.append(("FAIL", f"unsupported output formats {unknown}"))

    for pc in plan["cells"]:
        w = pc["where"]
        if pc["ppi"] < MIN_PPI:
            issues.append(("WARN", f"{w}: effective resolution {pc['ppi']:.0f} ppi at final size "
                                   f"(< {MIN_PPI}); show fewer columns, crop tighter or give "
                                   "this panel more width - upsampling adds no detail"))
        cw, ch = _ax_size_in(pc["ax"])
        x, y, wp, hp = pc["crop"]
        dev = abs((cw / ch) / (wp / hp) - 1)
        if dev > ASPECT_TOL:
            issues.append(("FAIL", f"{w}: displayed aspect deviates {dev:.1%} from native pixels "
                                   "(image stretched)"))
        for z in pc["zooms"]:
            iw, ih = _ax_size_in(z["inset_ax"])
            bw, bh = z["box"][2], z["box"][3]
            if abs((iw / ih) / (bw / bh) - 1) > ASPECT_TOL:
                issues.append(("FAIL", f"{w}: zoom inset {z['box']} is stretched"))
            spine = to_hex(next(iter(z["inset_ax"].spines.values())).get_edgecolor())
            rect = [p for p in pc["ax"].patches if hasattr(p, "get_edgecolor")
                    and p.get_width() == bw and p.get_height() == bh]
            if not rect or to_hex(rect[0].get_edgecolor()) != spine:
                issues.append(("FAIL", f"{w}: zoom box colour does not match its inset border"))
            expected_w = bw * pc["in_per_px"] * z["factor"]
            if abs(iw / expected_w - 1) > ASPECT_TOL:
                issues.append(("FAIL", f"{w}: inset magnification is not {z['factor']}x"))

    cells = prep["cells"]
    has_heat = any(o["type"] == "heatmap" and not o["flat"] for c in cells for o in c["overlays"])
    if has_heat and not plan["colorbars"]:
        issues.append(("FAIL", "heatmap shown without a colorbar"))
    needs_legend = any(o["type"] in ("contour", "fill", "label_mask")
                       for c in cells for o in c["overlays"])
    if needs_legend and not plan["legend"]:
        issues.append(("FAIL", "masks/contours shown without a legend"))
    return issues
