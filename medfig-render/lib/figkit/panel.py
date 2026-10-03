"""Panel marking and standalone per-panel export (spec S4).

``mark_panel(ax, "a", extra_axes=[cbar.ax])`` tags an axes as a panel; ``export.save`` then writes
each marked panel as its own PDF + SVG at exactly the size it occupies in the composite, with every
panel label hidden. Labels are recognised by the ``_figkit_panel_label`` flag (set by
``label_panels``) or heuristically: a bold one-letter (optionally + digit, optionally parenthesised)
text outside its axes' data area -- an annotation in axes fraction (scipilot ``add_panel_labels``),
``ax.text(..., transform=ax.transAxes)`` outside [0, 1]^2, or ``fig.text`` near an axes' upper-left.
"""
import re
from pathlib import Path

import matplotlib as mpl
import matplotlib.text as mtext
import matplotlib.transforms as mtransforms

_LABEL_RE = re.compile(r"^\(?[A-Za-z]\d?\)?$")


def mark_panel(ax, pid, extra_axes=None):
    """Tag ``ax`` as panel ``pid``; ``extra_axes`` (colorbar, inset axes) are exported with it."""
    ax._figkit_panel_id = str(pid)
    ax._figkit_panel_extra = list(extra_axes or [])
    return ax


def label_panels(fig, axes, labels, **kw):
    """Wrap scipilot ``layout_tools.add_panel_labels`` and flag the created labels as panel labels."""
    from . import config
    from .export import _import_file
    d = Path(config.resolve_cfg(kw.pop("cfg", None)).ensure_scipilot()).resolve()
    add = _import_file("labels", d / "layout_tools.py").add_panel_labels
    placed = add(fig, axes=list(axes), labels=list(labels), **kw)
    for t in placed:
        t._figkit_panel_label = True
    return placed


def _bold(t):
    w = t.get_fontweight()
    return w in ("bold", "heavy", "extra bold", "black", "demibold", "semibold", "demi") or (
        isinstance(w, (int, float)) and w >= 600)


def _outside(t):
    """Heuristic: text anchored in axes fraction outside the unit square, or offset outside it."""
    if isinstance(t, mtext.Annotation):
        ax = t.axes
        if not (t.xycoords == "axes fraction" or (ax is not None and t.xycoords is ax.transAxes)):
            return False
        x, y = t.xy
        return not (0 < x < 1 and 0 < y < 1)
    ax = t.axes
    if ax is not None and t.get_transform() is ax.transAxes:
        x, y = t.get_position()
        return not (0 < x < 1 and 0 < y < 1)
    fig = t.figure
    if ax is None and fig is not None and t.get_transform() is fig.transFigure:
        return _near_axes_corner(fig, *t.get_position())
    return False


def _near_axes_corner(fig, x, y, tol=0.08):
    """fig.text at the upper-left of some axes, outside its data area (figure fraction)."""
    for a in fig.axes:
        x0, y0, x1, y1 = a.get_position().extents
        outside = x < x0 or y > y1
        if outside and x0 - tol <= x <= x0 + tol and y1 - tol <= y <= y1 + tol:
            return True
    return False


def is_panel_label(t):
    if getattr(t, "_figkit_panel_label", False):
        return True
    return bool(_bold(t) and _LABEL_RE.match(t.get_text().strip()) and _outside(t))


def panel_labels(fig):
    texts = list(fig.texts)
    for ax in fig.axes:
        texts.extend(ax.texts)
    return [t for t in texts if is_panel_label(t)]


def marked_panels(fig):
    axes = [a for a in fig.axes if getattr(a, "_figkit_panel_id", None) is not None]
    ids = [a._figkit_panel_id for a in axes]
    dup = {i for i in ids if ids.count(i) > 1}
    if dup:
        raise ValueError(f"duplicate panel ids: {sorted(dup)}")
    return sorted(axes, key=lambda a: a._figkit_panel_id)


def _members(ax):
    out = [ax] + list(getattr(ax, "_figkit_panel_extra", []))
    for a in list(out):  # twinx / twiny siblings belong to the same panel
        out.extend(s for s in a._twinned_axes.get_siblings(a) if s not in out)
    for a in list(out):
        out.extend(a.child_axes)
    return out


def export_panels(fig, name, out_dir, dpi=600):
    """Write every marked panel of ``fig`` to <out_dir>/panels/<name>/<name>_<id>.{pdf,svg}.

    Returns ``[{'id','pdf','svg','size_in':[w,h]}]``; raises RuntimeError if a PDF is missing/empty.
    """
    panels = marked_panels(fig)
    if not panels:
        return []
    dest = Path(out_dir) / "panels" / name
    dest.mkdir(parents=True, exist_ok=True)
    labels = panel_labels(fig)
    records = []
    fig.canvas.draw()  # settle the composite layout, then freeze it so hiding axes cannot re-flow it
    engine = fig.get_layout_engine()
    fig.set_layout_engine("none")
    try:
        for ax in panels:
            records.append(_export_one(fig, ax, name, dest, labels, dpi))
    finally:
        fig.set_layout_engine(engine)
    return records


def export_whole(fig, name, out_dir, pid="a", dpi=600):
    """Single-panel figure (``export.save(..., panels="none")``): the composite itself is the panel.
    Writes <out_dir>/panels/<name>/<name>_<pid>.{pdf,svg} at the full figure size, panel labels hidden."""
    dest = Path(out_dir) / "panels" / name
    dest.mkdir(parents=True, exist_ok=True)
    hidden = [t for t in panel_labels(fig) if t.get_visible()]
    pdf, svg = dest / f"{name}_{pid}.pdf", dest / f"{name}_{pid}.svg"
    fig.canvas.draw()
    engine = fig.get_layout_engine()
    fig.set_layout_engine("none")  # hiding a label must not re-flow the layout
    try:
        for t in hidden:
            t.set_visible(False)
        with mpl.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"}):
            for p in (pdf, svg):
                fig.savefig(p, dpi=dpi)
    finally:
        for t in hidden:
            t.set_visible(True)
        fig.set_layout_engine(engine)
    for p in (pdf, svg):
        if not p.is_file() or p.stat().st_size == 0:
            raise RuntimeError(f"{name}: standalone panel {pid} not written: {p}")
    w, h = fig.get_size_inches()
    return [{"id": pid, "pdf": str(pdf), "svg": str(svg), "size_in": [round(float(w), 4), round(float(h), 4)]}]


def _export_one(fig, ax, name, dest, labels, dpi):
    keep = _members(ax)
    hidden = [a for a in fig.axes if a not in keep and a.get_visible()]
    hidden += [t for t in labels if t.get_visible()]
    pdf = dest / f"{name}_{ax._figkit_panel_id}.pdf"
    svg = dest / f"{name}_{ax._figkit_panel_id}.svg"
    try:
        for a in hidden:
            a.set_visible(False)
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        boxes = [a.get_tightbbox(r) for a in keep if a.get_visible()]
        box = mtransforms.Bbox.union([b for b in boxes if b is not None])
        box = box.transformed(fig.dpi_scale_trans.inverted())
        with mpl.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none"}):
            for p in (pdf, svg):
                fig.savefig(p, bbox_inches=box, pad_inches=0, dpi=dpi)
    finally:
        for a in hidden:
            a.set_visible(True)
    for p in (pdf, svg):
        if not p.is_file() or p.stat().st_size == 0:
            raise RuntimeError(f"{name}: standalone panel {ax._figkit_panel_id} not written: {p}")
    return {"id": ax._figkit_panel_id, "pdf": str(pdf), "svg": str(svg),
            "size_in": [round(box.width, 4), round(box.height, 4)]}
