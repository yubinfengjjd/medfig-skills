"""Annotated heat map and waterfall with a hard closure check (S3: coloured cmaps / bars only)."""
import string

import numpy as np
import pandas as pd
from matplotlib.colors import Normalize, TwoSlopeNorm
from matplotlib.patches import Rectangle

from .. import qa, style

POS, NEG, TOTAL = "#0072B2", "#D55E00", "#009E73"
NA_FILL, NA_EDGE, NA_TEXT = style.NA_FILL, style.GREY, style.DARK_GREY
CLOSURE_TOL = 1e-5


def _fmt_true_minus(fmt, v):
    """Format ``v`` with ``fmt``; only the sign produced by the number fields becomes U+2212
    (literal hyphens in ``fmt`` are kept)."""
    out = []
    for lit, field, spec, conv in string.Formatter().parse(fmt):
        out.append(lit)
        if field is not None:
            out.append(format(v, spec or "").replace("-", "−"))
    return "".join(out)


def annotated(ax, M: pd.DataFrame, cmap, center=None, fmt="{:.2f}", hatch_mask=None, cbar_label="",
              cbar=False, fontsize=6, vmin=None, vmax=None, gridlines=False):
    """Heat map of DataFrame ``M``; ``center`` -> symmetric TwoSlopeNorm; ``fmt=None`` -> no text;
    ``hatch_mask`` (bool DataFrame, same labels) -> grey hatched "n/a" cells (auxiliary, never blank).
    ``cmap`` must be coloured (grey maps raise: S3). Negative cell values get a true minus (U+2212);
    other characters of ``fmt`` (e.g. hyphens) are left unchanged. ``gridlines=True``: white cell separators
    (auxiliary; soft-theme look)."""
    import matplotlib as mpl
    cm = mpl.colormaps[cmap] if isinstance(cmap, str) else cmap
    if qa._grey_cmap(cm):
        raise ValueError(f"heat.annotated: grey colormap {cm.name!r} is not allowed for data (S3)")
    A = M.to_numpy(float).copy()
    mask = (np.zeros_like(A, bool) if hatch_mask is None
            else hatch_mask.reindex(index=M.index, columns=M.columns).fillna(False).to_numpy(bool))
    A[mask] = np.nan
    fin = A[np.isfinite(A)]
    lo = vmin if vmin is not None else (fin.min() if fin.size else 0.0)
    hi = vmax if vmax is not None else (fin.max() if fin.size else 1.0)
    if center is not None:
        r = max(abs(hi - center), abs(center - lo)) or 1.0
        norm = TwoSlopeNorm(vcenter=center, vmin=center - r, vmax=center + r)
    else:
        norm = Normalize(lo, hi if hi > lo else lo + 1)
    im = ax.imshow(np.ma.masked_invalid(A), cmap=cm, norm=norm, aspect="auto")
    nr, nc = A.shape
    for i, j in zip(*np.nonzero(mask)):
        style.aux(ax.add_patch(Rectangle((j - 0.5, i - 0.5), 1, 1, facecolor=NA_FILL, edgecolor=NA_EDGE,
                                         hatch="////", linewidth=0)))
        ax.text(j, i, "n/a", ha="center", va="center", fontsize=fontsize, color=NA_TEXT)
    if fmt is not None:
        for i in range(nr):
            for j in range(nc):
                if mask[i, j] or not np.isfinite(A[i, j]):
                    continue
                rgb = cm(norm(A[i, j]))[:3]
                lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
                ax.text(j, i, _fmt_true_minus(fmt, A[i, j]), ha="center", va="center",
                        fontsize=fontsize, color="white" if lum < 0.45 else "black")
    ax.set_xticks(range(nc), [str(c) for c in M.columns])
    ax.set_yticks(range(nr), [str(r) for r in M.index])
    ax.tick_params(length=0)
    if gridlines:
        ax.set_xticks(np.arange(-0.5, nc, 1), minor=True)
        ax.set_yticks(np.arange(-0.5, nr, 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=1.0)
        ax.tick_params(which="minor", length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax._anchor_matrix = A
    ax._anchor_mappable = im
    ax._anchor_hatch = mask
    if cbar:
        cb = ax.figure.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cb.set_label(cbar_label, fontsize=fontsize)
        cb.ax.tick_params(labelsize=fontsize, length=2)
        ax._anchor_colorbar = cb
    return ax


def waterfall(ax, start: float, contribs: pd.Series, end: float, start_label="Start",
              end_label="Total", orientation="horizontal", tol=CLOSURE_TOL):
    """Cumulative contribution bars from ``start`` to ``end``.

    Hard checks (never a fallback drawing): every input must be finite (NaN is not silently skipped
    by a sum) -> ``ValueError("... non-finite ...")``; then ``|start + sum(contribs) - end| <= tol``
    -> otherwise ``ValueError("waterfall does not close ...")``. The closure error goes to
    ``ax._anchor_closure_error`` for provenance. Colours: positive blue, negative vermillion,
    start / total bluish green; the zero line is a reference line."""
    contribs = pd.Series(contribs, dtype=float)
    vals = contribs.to_numpy(dtype=float)
    bad = [str(k) for k, v in zip(contribs.index, vals) if not np.isfinite(v)]
    start_ok = np.isfinite(float(start))
    end_ok = np.isfinite(float(end))
    if bad or not start_ok or not end_ok:
        raise ValueError(f"waterfall needs finite values; non-finite: contribs {bad}, "
                         f"start={start!r}, end={end!r}")
    err = float(start + vals.sum() - end)
    if not np.isfinite(err) or abs(err) > tol:
        raise ValueError(f"waterfall does not close: start + sum(contribs) - end = {err:.3g} (tol {tol:g})")
    labels = [start_label] + [str(k) for k in contribs.index] + [end_label]
    bottoms, heights, colors = [0.0], [float(start)], [TOTAL]
    run = float(start)
    for v in vals:
        bottoms.append(run)
        heights.append(float(v))
        colors.append(POS if v >= 0 else NEG)
        run += v
    bottoms.append(0.0)
    heights.append(float(end))
    colors.append(TOTAL)
    pos = np.arange(len(labels), dtype=float)
    if orientation == "horizontal":
        y = pos[::-1]
        ax.barh(y, heights, left=bottoms, color=colors, height=0.65, linewidth=0)
        ax.axvline(0, color=NA_TEXT, linewidth=0.5)
        ax.set_yticks(y, labels)
    elif orientation == "vertical":
        ax.bar(pos, heights, bottom=bottoms, color=colors, width=0.65, linewidth=0)
        ax.axhline(0, color=NA_TEXT, linewidth=0.5)
        ax.set_xticks(pos, labels)
    else:
        raise ValueError(f"orientation must be 'horizontal' or 'vertical', got {orientation!r}")
    ax._anchor_closure_error = err
    ax._anchor_cumulative = np.array(bottoms[1:-1]) + np.array(heights[1:-1])
    return ax
