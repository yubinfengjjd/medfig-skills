"""Scatter panels: gated bubble (area ∝ n, failing gate hollow + hatch) and size-keyed group scatter.

S3: points are coloured (palette or ``style.DATA_CYCLE``); the size key and reference lines are aux grey.
"""
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from .. import style

GREY = style.GREY


def bubble_area(n, n_ref, s_ref=40.0, s_min=4.0):
    """Marker area (pt²) proportional to n: ``s_ref`` at ``n_ref``, never below ``s_min``."""
    return np.maximum(s_min, s_ref * np.asarray(n, float) / float(n_ref))


def gated_bubble(ax, rows: pd.DataFrame, color=None, n_ref=None, ref=None, hatch="//////",
                 label_col="label", annotate_fail=True):
    """Estimate + CI per row, bubble area ∝ ``n``; rows failing the gate stay visible.

    ``rows``: ``x``, ``est``, ``lo``, ``hi``, ``n``, ``passes`` (bool), optional ``label``. Passing rows:
    filled bubble + solid CI. Failing rows: hollow bubble with ``hatch`` in the same colour + dashed CI,
    annotated "(n)" when ``annotate_fail``. ``ref``: aux dashed y reference (e.g. AUROC 0.5).
    Stores ``ax._anchor_gate`` {label: passes} and ``ax._anchor_area`` (marker areas)."""
    rows = rows.reset_index(drop=True)
    color = color or style.DATA_CYCLE[0]
    n_ref = n_ref or float(rows["n"].max())
    area = bubble_area(rows["n"], n_ref)
    if ref is not None:
        style.aux(ax.axhline(ref, color=GREY, linestyle="--", linewidth=0.6, zorder=1))
    for r, s in zip(rows.itertuples(index=False), area):
        ok = bool(r.passes)
        ax.plot([r.x, r.x], [r.lo, r.hi], color=color, linewidth=0.7, linestyle="-" if ok else "--", zorder=2)
        ax.scatter([r.x], [r.est], s=s, facecolor=color if ok else "white", edgecolor=color,
                   hatch=None if ok else hatch, linewidths=0.7, zorder=3)
        if not ok and annotate_fail:
            ax.annotate(f"({int(r.n)})", (r.x, r.est), xytext=(3, 3), textcoords="offset points", fontsize=6)
    labels = rows[label_col] if label_col in rows else rows.index.astype(str)
    ax._anchor_gate = dict(zip(labels, rows["passes"].astype(bool)))
    ax._anchor_area = area
    return ax


def sized(ax, df: pd.DataFrame, x, y, group, size, palette=None, s_ref=30.0, n_ref=None,
          key_sizes=None, symlog=False, linthresh=1e-3, alpha=0.7, legend_loc="lower right"):
    """One coloured scatter per ``group`` value, marker area ∝ ``size`` column.

    ``palette``: {group: {color, marker, label[, edge]}} (e.g. toml cohort palette); missing groups get
    ``style.DATA_CYCLE``. ``key_sizes`` (e.g. [10, 100]) adds aux-grey size-key handles to the legend.
    ``symlog=True`` -> symlog x axis with ``linthresh``. Stores ``ax._anchor_groups`` {group: n points}."""
    palette = palette or {}
    n_ref = n_ref or float(df[size].max())
    handles, counts = [], {}
    for i, (g, sub) in enumerate(df.groupby(group, sort=False)):
        st = palette.get(g, {})
        c = st.get("color", style.DATA_CYCLE[i % len(style.DATA_CYCLE)])
        h = ax.scatter(sub[x], sub[y], s=bubble_area(sub[size], n_ref, s_ref, 2.0),
                       marker=st.get("marker", "o"), facecolor=c, edgecolor=st.get("edge", c),
                       linewidths=0.3, alpha=alpha, label=f"{st.get('label', g)} ({len(sub):,})", zorder=3)
        handles.append(h)
        counts[g] = int(len(sub))
    for k in key_sizes or ():
        ms = float(np.sqrt(bubble_area([k], n_ref, s_ref, 2.0)[0]))
        handles.append(style.aux(Line2D([], [], linestyle="none", marker="o", ms=ms, mfc=GREY, mec=GREY,
                                        label=f"{k:,}")))
    if symlog:
        ax.set_xscale("symlog", linthresh=linthresh, linscale=0.5)
        style.log_ticks(ax, "x")  # true-minus decade labels
    ax.legend(handles=handles, loc=legend_loc, frameon=False, handletextpad=0.3, labelspacing=0.3)
    ax._anchor_groups = counts
    return ax
