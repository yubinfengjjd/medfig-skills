"""Row-normalised confusion matrix with automatic "absent" rows and a shared colourbar helper."""
import numpy as np
import pandas as pd
from matplotlib.patches import Rectangle

from .. import style

ABSENT_FILL, ABSENT_EDGE, ABSENT_TEXT = style.NA_FILL, style.GREY, style.DARK_GREY


def matrix(ax, counts: pd.DataFrame, classes, absent_rows=(), annot="pct_n", cbar=False,
           fontsize=6, tick_labels=None, count_fmt="{:d}", cmap="Blues"):
    """Row-normalised confusion matrix; rows = truth, columns = prediction (``classes`` order).

    ``counts`` has columns ``truth``, ``prediction``, ``count``. ``absent_rows`` plus every row whose
    total count is 0 are drawn as grey hatched rows labelled "absent" (never a blank row that reads as
    0 %) and stored as NaN; the final set is ``ax._anchor_absent`` (classes order).
    ``tick_labels`` overrides the displayed class names (default ``classes``); pass abbreviations when
    long class names collide at small sizes (check with ``qa.geometry_audit`` at the final size).
    ``annot``: "pct_n" -> "xx.x%\\n(n)", "pct" -> "xx.x%", None -> no cell text.
    ``count_fmt``: format string for n in "pct_n" cells (default "{:d}"; "{:,}" -> "12,345").
    ``cmap`` must be a coloured sequential map (S3); the absent hatching is auxiliary.
    """
    classes = list(classes)
    k = len(classes)
    labels = classes if tick_labels is None else list(tick_labels)
    if len(labels) != k:
        raise ValueError(f"tick_labels has {len(labels)} entries, expected {k} (one per class)")
    unknown = [r for r in absent_rows if r not in classes]
    if unknown:
        raise ValueError(f"absent_rows {unknown} are not in classes {classes}")
    C = (counts.pivot_table(index="truth", columns="prediction", values="count", aggfunc="sum")
         .reindex(index=classes, columns=classes).fillna(0).to_numpy(float))
    tot = C.sum(1)
    with np.errstate(invalid="ignore", divide="ignore"):
        M = C / tot[:, None]
    absent = sorted({classes.index(r) for r in absent_rows} | set(np.flatnonzero(tot == 0).tolist()))
    M[absent] = np.nan
    im = ax.imshow(np.ma.masked_invalid(M), cmap=cmap, vmin=0, vmax=1, aspect="equal")
    for i in absent:
        style.aux(ax.add_patch(Rectangle((-0.5, i - 0.5), k, 1, facecolor=ABSENT_FILL,
                                         edgecolor=ABSENT_EDGE, hatch="////", linewidth=0)))
        ax.text((k - 1) / 2, i, "absent", ha="center", va="center", fontsize=fontsize, color=ABSENT_TEXT)
    if annot:
        cm = im.get_cmap()
        for i in range(k):
            if i in absent:
                continue
            for j in range(k):
                v = M[i, j]
                if not np.isfinite(v):
                    continue
                s = f"{100 * v:.1f}%"
                if annot == "pct_n":
                    s += "\n(" + count_fmt.format(int(C[i, j])) + ")"
                r, g, b = cm(v)[:3]
                dark = 0.2126 * r + 0.7152 * g + 0.0722 * b < 0.45
                ax.text(j, i, s, ha="center", va="center", fontsize=fontsize, linespacing=1.0,
                        color="white" if dark else "black")
    ax.set_xticks(range(k), labels)
    ax.set_yticks(range(k), labels)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax._anchor_matrix = M
    ax._anchor_absent = [classes[i] for i in absent]
    ax._anchor_counts = C
    ax._anchor_mappable = im
    if cbar:
        ax._anchor_colorbar = colourbar(ax, None)
    return ax


def colourbar(ax, cax, label="Row proportion", ticks=(0, 0.5, 1.0), fontsize=6):
    """Shared row-proportion colourbar for ``matrix()`` axes. With ``cax`` it is drawn into that axes
    (one bar shared by several matrices); ``cax=None`` steals space from ``ax``."""
    fig = ax.figure
    if cax is None:
        cb = fig.colorbar(ax._anchor_mappable, ax=ax, fraction=0.046, pad=0.04)
    else:
        cb = fig.colorbar(ax._anchor_mappable, cax=cax)
    cb.set_label(label, fontsize=fontsize)
    if ticks is not None:
        cb.set_ticks(list(ticks))
    cb.ax.tick_params(labelsize=fontsize, length=2)
    cb.outline.set_linewidth(0.4)
    return cb
