"""Figure QA: geometry audit, banned words, font floor, true minus, S1-S3 panel checks.

geometry_audit only looks at text that is actually drawn (visible, non-empty, tick labels inside the
view), one frame box per legend, and data points from marker lines + collection offsets placed with
offset_transform(offset) + transform(origin), clipped to the axes view; identity pseudo-offsets are skipped.
"""
import colorsys
import itertools
import re

import numpy as np
import matplotlib.colors as mcolors
import matplotlib.lines as mlines
import matplotlib.text as mtext
import matplotlib.transforms as mtransforms
from matplotlib.axes._secondary_axes import SecondaryAxis

from .style import INSET_TICK_PT, MIN_FONT_PT

# Default banned list shared by figures, tables and captions. A project adjusts it ONLY in figkit.toml:
# [qa] banned_extra = [...] adds words, [qa] banned_allow = [...] lifts default words (banned_list()).
BANNED = ["validated", "superior", "clinical benefit", "UMAP", "deployment",
          "diagnostic", "clinically proven"]

_ASCII_MINUS = re.compile(r"(?<![\w.])-(?=\.?\d)")


def _tick_labels(ax):
    if not ax.axison:
        return []
    out = []
    for axis, lim in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
        if not axis.get_visible():
            continue
        lo, hi = sorted(lim)
        for t in axis.get_major_ticks():
            if not lo - 1e-9 <= t.get_loc() <= hi + 1e-9:
                continue
            for lab in (t.label1, t.label2):  # label2: top / right ticks (tick_top, secondary axes)
                if lab.get_visible() and lab.get_text():
                    out.append(lab)
    return out


def _ax_texts(ax):
    items = [t for t in ax.texts if t.get_visible() and t.get_text()]
    for lab in (ax.xaxis.label, ax.yaxis.label, ax.title, ax._left_title, ax._right_title):
        if lab.get_visible() and lab.get_text():
            items.append(lab)
    return items


def _drawn_texts(fig):
    items = []
    for i, ax in enumerate(fig.axes):
        items += [(f"ax{i}.tick", t) for t in _tick_labels(ax)]
        items += [(f"ax{i}.text", t) for t in _ax_texts(ax)]
    items += [("fig.text", t) for t in fig.texts if t.get_visible() and t.get_text()]
    return items


def _legends(fig):
    legs = list(fig.legends) + [ax.get_legend() for ax in fig.axes if ax.get_legend()]
    return [leg for leg in legs if leg.get_visible()]


def _data_points(ax):
    """Display-space coordinates of marker-bearing lines and offset collections (scatter, hexbin)."""
    pts, bb = [], ax.bbox

    def _clip(artist, p):
        # clipped artists are only drawn inside the axes: drop points outside the view
        if artist.get_clip_on() and len(p):
            p = p[(p[:, 0] >= bb.x0) & (p[:, 0] <= bb.x1) & (p[:, 1] >= bb.y0) & (p[:, 1] <= bb.y1)]
        return p

    for ln in ax.get_lines():
        xy = ln.get_xydata()
        if len(xy) and ln.get_marker() not in (None, "", "None", " ") and ln.get_visible():
            pts.append(_clip(ln, ax.transData.transform(xy)))
    for c in ax.collections:
        offs = np.asarray(c.get_offsets(), float)
        if not (c.get_visible() and len(offs)):
            continue
        otr = c.get_offset_transform()
        if isinstance(otr, mtransforms.IdentityTransform) and not offs.any():
            continue  # LineCollection / PolyCollection default (0, 0) pseudo-offset
        # drawn position = offset_transform(offset) + transform(path origin): scatter paths are in points
        # (identity transform); hexbin uses AffineDeltaTransform(transData) and carries the translation
        # through transData, so both terms are needed.
        p = otr.transform(offs) + c.get_transform().transform(np.zeros((1, 2)))
        pts.append(_clip(c, p))
    return pts


def geometry_audit(fig):
    """Text-text / legend-text overlap, text outside canvas, legend covering data. Top-level axes only."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W, H = fig.bbox.width, fig.bbox.height
    boxes = [(w, t.get_text(), t.get_window_extent(r)) for w, t in _drawn_texts(fig)]
    legs = _legends(fig)  # each legend joins the text checks as ONE frame box, never its entries
    boxes += [(f"legend{j}", "<legend>", leg.get_window_extent(r)) for j, leg in enumerate(legs)]
    out = []
    for (wa, ta, ba), (wb, tb, bb) in itertools.combinations(boxes, 2):
        if ba.width and bb.width and ba.overlaps(bb):
            out.append(f"overlap {wa}:{ta!r} <-> {wb}:{tb!r}")
    for w, t, b in boxes:
        if b.x0 < -1 or b.y0 < -1 or b.x1 > W + 1 or b.y1 > H + 1:
            out.append(f"outside canvas {w}:{t!r}")
    for leg in legs:
        lb = leg.get_window_extent(r)
        for ax in fig.axes:  # ax.get_lines()/collections never include the legend's own handles
            for p in _data_points(ax):
                if len(p) and ((p[:, 0] > lb.x0) & (p[:, 0] < lb.x1)
                               & (p[:, 1] > lb.y0) & (p[:, 1] < lb.y1)).any():
                    out.append(f"legend covers data in {ax.get_label() or 'axes'}")
                    break
    return out


def banned_list(cfg=None):
    """The project's banned list: BANNED minus [qa] banned_allow plus [qa] banned_extra of ``cfg``
    (default: the active config; plain BANNED when no config is active)."""
    if cfg is None:
        from . import config
        cfg = config._ACTIVE
    if cfg is None:
        return list(BANNED)
    allow = {w.lower() for w in getattr(cfg, "banned_allow", [])}
    out = [w for w in BANNED if w.lower() not in allow]
    for w in getattr(cfg, "banned_extra", []):
        if w.lower() not in {x.lower() for x in out}:
            out.append(w)
    return out


def banned_in_text(text, cfg=None):
    """Banned words (word boundary, case-insensitive) found in a plain string (captions, tables);
    the list is ``banned_list(cfg)``."""
    return [w for w in banned_list(cfg) if re.search(rf"\b{re.escape(w)}\b", str(text), flags=re.I)]


def banned_words(fig, cfg=None):
    return banned_in_text(" ".join(t.get_text() for t in fig.findobj(mtext.Text)), cfg)


# Figure text carries results and reading keys only; caveats, disclaimers and method notes belong in the
# caption. Default caveat phrases (case-insensitive regex); a project lifts one with [qa] caveat_allow = [key].
FIGURE_CAVEATS = {
    "illustrative": r"\billustrative\b",
    "not a clinical": r"\bnot (?:a |for )?clinical\b",
    "no treatment": r"\bno (?:treatment|urgency|discharge)\b",
    "research use only": r"\bresearch (?:use|purposes) only\b",
    "not used for": r"\bnot used (?:for|in)\b",
    "by construction": r"\bby construction\b",
    "descriptive only": r"\bdescriptive(?: only)?\b",
    "not a CI": r"\bnot an? (?:CI|confidence interval)\b",
    "retrospective": r"\bretrospective\b",
    "exploratory": r"\bexploratory\b",
    "post hoc": r"\bpost[- ]hoc\b",
    "interpret with caution": r"\bcaution\b",
}
# Cross-references: a figure must not point at tables / figures (that is the caption's job).
CROSS_REF = re.compile(r"\b(?:(?:Supplementary|Extended Data)\s+)?(?:Fig(?:ure)?s?\.?|Tables?)\s*S?\d+[a-z]?\b",
                       flags=re.I)
# Development history (medfig-plan references/mainline_rules.md): earlier versions are discarded and analyses
# are organised by scientific question, so these never reach a figure. Case-insensitive; a project lifts one
# with [qa] caveat_allow = [key] only when the word is part of a genuine method name.
DEV_HISTORY = {
    "pre-registered": r"\bpre-?regist(?:ered|ration)\b",
    "hypothesis status": r"\bhypothes(?:is|es) status\b",
    "closeout": r"\bclose-?out\b",
    "closure": r"\bclosure\b",
    "wave": r"\bwave[- ]?\d\b",
    "earlier version": r"\b(?:earlier|previous|old|legacy|historical) (?:version|model|anchor|pipeline)\b",
    "repair": r"\brepair(?:ed)?\b",
    "post-outcome": r"\bpost-?outcome\b",
    "reconciliation": r"\breconcil(?:ed|iation)\b",
}


def _cfg_or_active(cfg):
    if cfg is None:
        from . import config
        cfg = config._ACTIVE
    return cfg


def caveat_patterns(cfg=None):
    """{key: regex} of FIGURE_CAVEATS minus ``[qa] caveat_allow`` (active config by default)."""
    allow = {w.lower() for w in getattr(_cfg_or_active(cfg), "caveat_allow", None) or []}
    return {k: v for k, v in FIGURE_CAVEATS.items() if k.lower() not in allow}


def dev_history_patterns(cfg=None):
    """{key: regex} of DEV_HISTORY minus ``[qa] caveat_allow``."""
    allow = {w.lower() for w in getattr(_cfg_or_active(cfg), "caveat_allow", None) or []}
    return {k: v for k, v in DEV_HISTORY.items() if k.lower() not in allow}


def dev_history_in_text(text, cfg=None):
    """Development-history keys found in a plain string (tables, captions, outlines)."""
    return [k for k, p in dev_history_patterns(cfg).items() if re.search(p, str(text), flags=re.I)]


def forbidden_in_text(text, cfg=None):
    """Project code patterns (``[qa] forbidden_patterns``, case-sensitive regex) found in a plain string --
    for tables and other non-figure text, where caveats are allowed (footnotes) but internal codes are not."""
    pats = getattr(_cfg_or_active(cfg), "forbidden_patterns", None) or []
    return [p for p in pats if re.search(p, str(text))]


def _free_figure_texts(fig):
    """Figure-level texts that are not panel labels and not supxlabel / supylabel (shared axis names)."""
    from .panel import is_panel_label
    shared = {id(getattr(fig, a, None)) for a in ("_supxlabel", "_supylabel")}  # may sit in fig.texts
    out = [t for t in fig.texts if t.get_visible() and t.get_text().strip() and not is_panel_label(t)
           and id(t) not in shared]
    sup = getattr(fig, "_suptitle", None)
    if sup is not None and sup.get_visible() and sup.get_text().strip() and sup not in out:
        out.append(sup)
    for sf in getattr(fig, "subfigs", []):
        out += _free_figure_texts(sf)
    return out


def figure_text_audit(fig, cfg=None):
    """Text that is not a result or a reading key: (1) free figure-level text (footers, notes, suptitle;
    panel labels and supxlabel / supylabel allowed), (2) caveats / disclaimers (``caveat_patterns``),
    (3) cross-references to tables / figures, (4) project codes (``[qa] forbidden_patterns``). Checks every
    drawn text: titles, axis labels, ticks, annotations, legend entries and titles, inset axes."""
    out = [f"figure-level text (move to the caption): {t.get_text()!r}" for t in _free_figure_texts(fig)]
    texts = [t for _w, t, _f in _all_texts(fig)]
    for extra in (getattr(fig, "_suptitle", None), getattr(fig, "_supxlabel", None), getattr(fig, "_supylabel", None)):
        if extra is not None and extra.get_visible() and extra.get_text() and extra not in texts:
            texts.append(extra)
    cav = caveat_patterns(cfg)
    seen = set()
    for t in texts:
        s = t.get_text()
        if not s.strip() or s in seen:
            continue
        seen.add(s)
        out += [f"caveat {k!r} in {s!r}" for k, p in cav.items() if re.search(p, s, flags=re.I)]
        out += [f"development history {k!r} in {s!r} (earlier versions / internal plan names never reach a "
                "figure; see medfig-plan references/mainline_rules.md)" for k in dev_history_in_text(s, cfg)]
        if CROSS_REF.search(s):
            out.append(f"cross-reference in {s!r}")
        out += [f"project pattern {p!r} in {s!r}" for p in forbidden_in_text(s, cfg)]
    return out


def _all_texts(fig):
    """(where, Text, floor_pt) for every drawn text, including inset (child) axes and legend entries."""
    fig.canvas.draw()
    items = []

    def _walk(ax, tag, inset):
        items.extend((f"{tag}.tick", t, INSET_TICK_PT if inset else MIN_FONT_PT) for t in _tick_labels(ax))
        items.extend((f"{tag}.text", t, VALUE_LABEL_PT if getattr(t, "_figkit_value_label", False) else MIN_FONT_PT)
                     for t in _ax_texts(ax))
        for j, ch in enumerate(ax.child_axes):
            if ch.get_visible():  # a secondary_x/yaxis is the parent's second scale: normal 6 pt floor
                _walk(ch, f"{tag}.inset{j}", inset or not isinstance(ch, SecondaryAxis))

    for i, ax in enumerate(fig.axes):
        if ax.get_visible():
            _walk(ax, f"ax{i}", _is_inset(ax))
    items += [("fig.text", t, MIN_FONT_PT) for t in fig.texts if t.get_visible() and t.get_text()]
    for j, leg in enumerate(_legends(fig)):
        items += [(f"legend{j}", t, MIN_FONT_PT) for t in leg.get_texts() if t.get_text()]
        title = leg.get_title()
        if title.get_visible() and title.get_text():
            items.append((f"legend{j}.title", title, MIN_FONT_PT))
    return items


VALUE_LABEL_PT = 5.0  # numbers printed on dense bars (compare.metric_bars, > 5 bars); Nature allows 5 pt


def min_font(fig):
    """Text below the floor: 6 pt for everything; 5 pt allowed only for inset-axes tick labels and for
    value labels on dense bars (``_figkit_value_label``)."""
    return [f"font {t.get_fontsize():g} pt < {floor:g} pt at {w}: {t.get_text()!r}"
            for w, t, floor in _all_texts(fig) if t.get_fontsize() < floor - 1e-6]


def true_minus(fig):
    """Drawn text using an ASCII hyphen as a minus sign (e.g. '-1.5'); should be U+2212."""
    return [f"ASCII hyphen as minus at {w}: {t.get_text()!r}"
            for w, t, _ in _all_texts(fig) if _ASCII_MINUS.search(t.get_text())]


# ---------------------------------------------------------------- S1 / S2 panel checks
WHITESPACE_MAX = 0.15  # max left+right blank as a fraction of the grid cell width


def _is_colorbar_axes(ax):
    return hasattr(ax, "_colorbar") or ax.get_label() == "<colorbar>"


def _is_inset(ax):
    """Inset axes: ``ax.child_axes`` members (``ax.inset_axes``) or add_axes axes marked ``_figkit_inset``."""
    return getattr(ax, "_figkit_inset", False)


def _data_axes(fig, children=True):
    """(label, ax) for every visible data axes: grid-placed, ``fig.add_axes`` and subfigure axes, plus
    (``children=True``) inset / child axes, recursively. Colorbar axes and axes marked ``_figkit_aux``
    (``style.aux``: legend-only helpers, decorations) are skipped, and so are ``secondary_xaxis`` /
    ``secondary_yaxis`` axes (child axes that only carry the parent's second scale)."""
    out = []

    def _keep(ax):
        return (ax.get_visible() and not getattr(ax, "_figkit_aux", False) and not _is_colorbar_axes(ax)
                and not isinstance(ax, SecondaryAxis))

    def _walk(ax, label):
        out.append((label, ax))
        if children:
            for j, ch in enumerate(ax.child_axes):
                if _keep(ch):
                    _walk(ch, f"{label}.inset{j}")

    for i, ax in enumerate(fig.axes):
        if _keep(ax):
            _walk(ax, ax.get_label() or f"ax{i}")
    return out


def twin_group(ax):
    """``ax`` plus its twinx / twiny siblings (one panel drawn on overlaid axes)."""
    return list(ax._twinned_axes.get_siblings(ax))


def _grid_axes(fig):
    """S1 audits top-level, non-inset data axes only (child axes and ``_figkit_inset`` axes are skipped)."""
    return [(lab, ax) for lab, ax in _data_axes(fig, children=False) if not _is_inset(ax)]


def _is_image_axes(ax):
    a = ax.get_aspect()
    return bool(ax.images) and (a == "equal" or (not isinstance(a, str) and abs(float(a) - 1) < 1e-9))


def whitespace_audit(fig):
    """S1: grid cells (the axes box set by the layout engine, before aspect shrinking) whose content leaves
    > 15% of the cell width blank (left + right). Axes without a subplotspec (``fig.add_axes``) use their own
    position as the cell, so only letterboxing can leave blank. For equal-aspect image axes the drawn image
    extent replaces the axes box, so letterboxing counts as blank. Inset / child axes are not audited."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    out = []
    for label, ax in _grid_axes(fig):
        # the layout engine's (pre-aspect) box (the add_axes rect for free axes); the gridspec geometry is
        # ignored by constrained layout
        cell = ax.get_position(original=True).transformed(fig.transFigure)
        if _is_image_axes(ax):
            boxes = [mtransforms.Bbox.intersection(im.get_window_extent(r), ax.bbox)
                     for im in ax.images if im.get_visible()]
            boxes += [t.get_window_extent(r) for t in _tick_labels(ax) + _ax_texts(ax)]
            boxes = [b for b in boxes if b is not None and b.width > 0]
            if not boxes:
                continue
            content = mtransforms.Bbox.union(boxes)
        else:
            content = ax.get_tightbbox(r)
            if content is None:
                continue
        overlap = max(0.0, min(cell.x1, content.x1) - max(cell.x0, content.x0))
        blank = (cell.width - overlap) / cell.width if cell.width > 0 else 0.0
        if blank > WHITESPACE_MAX + 1e-9:
            out.append(f"whitespace {label}: left+right blank {blank:.0%} > {WHITESPACE_MAX:.0%}")
    return out


def _data_line(ln, ax):
    if not ln.get_visible() or _is_aux(ln) or _reference_line(ln, ax):
        return False
    n = len(ln.get_xydata())
    return n > 1 or (n == 1 and not _no_marker(ln))  # a single marker is a data point


def text_only_panel(fig):
    """S2: data axes (incl. add_axes and inset axes) with visible text but no data. Reference lines
    (axhline / axvline / axline) and ``style.aux`` artists are not data."""
    out = []
    for label, ax in _data_axes(fig):
        def _ok(a):
            return a.get_visible() and not _is_aux(a)
        has_data = (any(_data_line(ln, ax) for ln in ax.get_lines())
                    or any(_ok(c) for c in ax.collections)
                    or any(_ok(im) for im in ax.images)
                    or any(_ok(p) for p in ax.patches))  # ax.patch (background) is not in ax.patches
        if not has_data and _ax_texts(ax):
            out.append(f"text-only panel {label}")
    return out


# ---------------------------------------------------------------- S3 colour audit
SAT_MIN = 0.15  # an artist is coloured if any of its (non-transparent) colours has HSV saturation > this
GREY_CMAPS = {"gray", "greys", "binary", "gist_gray", "bone", "grey", "gist_grey", "gist_yarg", "gist_yerg"}


def _is_aux(a):
    return getattr(a, "_figkit_aux", False)


def _sat_min():
    """S3 saturation floor: ``SAT_MIN``; the soft theme counts pastels as colour (``style.SOFT_SAT_MIN``)."""
    from . import style
    return style.SOFT_SAT_MIN if style.current_theme() == "soft" else SAT_MIN


def _coloured(colours):
    """True if any non-transparent colour is saturated; also True when nothing visible is drawn."""
    sat_min = _sat_min()
    seen = False
    for c in colours:
        rgba = mcolors.to_rgba(c)
        if rgba[3] == 0:
            continue
        seen = True
        if colorsys.rgb_to_hsv(*rgba[:3])[1] > sat_min:
            return True
    return not seen


def _as_list(c):
    if c is None or (isinstance(c, str) and c.lower() == "none"):
        return []
    arr = np.asarray(c, dtype=object)
    if isinstance(c, str) or (arr.ndim == 1 and len(arr) in (3, 4) and not isinstance(arr[0], str)
                              and np.isscalar(arr[0])):
        return [c]
    return list(c)


def _grey_cmap(cmap):
    name = (getattr(cmap, "name", "") or "").lower()
    return name.removesuffix("_r") in GREY_CMAPS


def _reference_line(ln, ax):
    """Only true reference-line constructors are exempt: ax.axhline / ax.axvline (transform blended with
    ax.transAxes on one axis) and ax.axline. Geometry (flat, y = x) is never enough: mark diagonals drawn
    with ax.plot via ``style.aux``."""
    if isinstance(ln, mlines.AxLine):
        return True
    tr = ln.get_transform()
    # identity checks only: Transform.__eq__ is unreliable (transAxes == transData can be True)
    if tr is ax.get_xaxis_transform() or tr is ax.get_yaxis_transform():
        return True
    if isinstance(tr, mtransforms.BlendedGenericTransform):
        return tr._x is ax.transAxes or tr._y is ax.transAxes
    return False


def _no_marker(ln):
    return ln.get_marker() in (None, "", "None", " ")


def colour_audit(fig):
    """S3: data artists drawn only in black / white / grey. Auxiliary elements (reference lines, aux-marked
    artists, raw medical images marked ``_figkit_raw_image`` or axes ``_figkit_image_axes``) are exempt."""
    out = []
    for label, ax in _data_axes(fig):
        bad = []
        for ln in ax.get_lines():
            if not ln.get_visible() or _is_aux(ln) or _reference_line(ln, ax):
                continue
            if _no_marker(ln) and len(ln.get_xydata()) < 2:  # a line with nothing to draw
                continue
            cols = [] if ln.get_linestyle() in ("None", "", " ") else [ln.get_color()]
            if not _no_marker(ln):
                cols += [ln.get_markerfacecolor(), ln.get_markeredgecolor()]
            if not _coloured(cols):
                bad.append("Line2D")
        for c in ax.collections:
            if not c.get_visible() or _is_aux(c):
                continue
            if c.get_array() is not None:  # colour-mapped collection (scatter c=, pcolormesh, hexbin)
                ok = not _grey_cmap(c.get_cmap())
            else:
                ok = _coloured(_as_list(c.get_facecolor()) + _as_list(c.get_edgecolor()))
            if not ok:
                bad.append(type(c).__name__)
        for p in ax.patches:  # ax.patch (the background) is never in ax.patches
            if not p.get_visible() or _is_aux(p):
                continue
            cols = ([p.get_facecolor()] if p.get_fill() else []) + [p.get_edgecolor()]
            if p.get_linewidth() == 0:
                cols = cols[:1] if p.get_fill() else []
            if not _coloured(cols):
                bad.append(type(p).__name__)
        raw_axes = getattr(ax, "_figkit_image_axes", False)
        for im in ax.images:
            if not im.get_visible() or _is_aux(im) or raw_axes or getattr(im, "_figkit_raw_image", False):
                continue
            arr = im.get_array()
            if arr is not None and np.ndim(arr) == 2 and _grey_cmap(im.get_cmap()):
                bad.append(f"{type(im).__name__} (grey cmap {im.get_cmap().name!r})")
        out += [f"colour {label}: achromatic data artist {t}" for t in dict.fromkeys(bad)]
    return out


# ---------------------------------------------------------------- palette clash (near-identical data hues)
PALETTE_MIN_DE = 12.0  # CIEDE2000; Okabe-Ito neighbours are >= 21, the clashes seen in practice were 2-10


def _artist_colours(ax):
    """{artist id: set of saturated base colours (hex, alpha dropped)} for the data artists of ``ax``."""
    out = {}
    sat_min = _sat_min()

    def _add(a, cols):
        hx = set()
        for c in cols:
            rgba = mcolors.to_rgba(c)
            if rgba[3] == 0 or colorsys.rgb_to_hsv(*rgba[:3])[1] <= sat_min:
                continue
            hx.add(mcolors.to_hex(rgba[:3]))
        if hx:
            out[id(a)] = hx

    for ln in ax.get_lines():
        if ln.get_visible() and not _is_aux(ln) and not _reference_line(ln, ax):
            cols = [] if ln.get_linestyle() in ("None", "", " ") else [ln.get_color()]
            if not _no_marker(ln):
                cols += [ln.get_markerfacecolor(), ln.get_markeredgecolor()]
            _add(ln, cols)
    for c in ax.collections:
        if c.get_visible() and not _is_aux(c) and c.get_array() is None:
            _add(c, _as_list(c.get_facecolor()) + _as_list(c.get_edgecolor()))
    for p in ax.patches:
        if p.get_visible() and not _is_aux(p):
            _add(p, ([p.get_facecolor()] if p.get_fill() else []) + [p.get_edgecolor()])
    return out


def palette_clash(fig, min_de=None, cfg=None):
    """Two different data colours in one axes that are nearly the same hue (0 < ΔE00 < ``min_de``) -- e.g.
    an action colour next to an almost identical cohort colour. Identical colours are not flagged (same
    encoding); colours within one artist (face / edge of a marker) are not compared. ``min_de``: argument,
    else ``[qa] palette_min_delta_e`` in figkit.toml, else ``PALETTE_MIN_DE``."""
    from .style import delta_e
    if min_de is None:
        try:
            from . import config
            min_de = config.resolve_cfg(cfg).palette_min_delta_e
        except (RuntimeError, AttributeError):
            min_de = None
    min_de = PALETTE_MIN_DE if min_de is None else float(min_de)
    from . import style
    soft = style.current_theme() == "soft"
    out = []
    for label, ax in _data_axes(fig):
        groups = list(_artist_colours(ax).values())
        controls = getattr(ax, "_figkit_controls", set()) if soft else set()
        seen = set()
        for g1, g2 in itertools.combinations(groups, 2):
            for a in g1:
                for b in g2:
                    key = tuple(sorted((a, b)))
                    if a == b or key in seen:
                        continue
                    seen.add(key)
                    de = delta_e(a, b)
                    lim = style.CONTROL_MIN_DE if a in controls and b in controls else min_de
                    if de < lim:
                        out.append(f"palette clash {label}: {key[0]} vs {key[1]} ΔE00 = {de:.1f} < {lim:g}")
    return out


def bar_baseline_audit(fig):
    """Soft theme: bars on a value axis that excludes 0 (truncated bars) need a break
    mark (``style.axis_break``); without one the export fails. The default theme is not checked here (its
    bars start at 0 by construction of the panel functions). Returns issue strings."""
    from matplotlib.container import BarContainer
    from . import style
    if style.current_theme() != "soft":
        return []
    out = []
    for label, ax in _data_axes(fig):
        for cont in ax.containers:
            if not isinstance(cont, BarContainer) or not len(cont.patches):
                continue
            horiz = getattr(cont, "orientation", "vertical") == "horizontal"
            lo, hi = sorted(ax.get_xlim() if horiz else ax.get_ylim())
            # value axis excludes 0 (bars drawn from a raised bottom or clipped by the limits) -> break mark
            if (lo > 1e-12 or hi < -1e-12) and getattr(ax, "_figkit_axis_break", None) != ("x" if horiz else "y"):
                out.append(f"bars {label}: value axis [{lo:g}, {hi:g}] excludes 0 without a break mark "
                           "(style.axis_break)")
                break
    return out
