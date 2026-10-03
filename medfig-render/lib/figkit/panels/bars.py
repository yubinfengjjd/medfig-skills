"""Bar panels: per-row stacked composition (e.g. conformal set sizes), absent rows hatched aux.

S3: segments take a light -> dark palette (no grey data); absent rows are aux hatched bars.
"""
import numpy as np
import pandas as pd

from .. import style


def stacked_fraction(ax, rows: pd.DataFrame, parts, palette=None, hatch="////", absent_text="absent"):
    """Horizontal 100% stacked bar per row (top -> bottom).

    ``rows``: ``label`` + one column per ``parts`` key holding counts (or fractions). A row whose parts
    sum to 0 / NaN is drawn as a full-width aux hatched bar with ``absent_text``. ``palette``:
    {part: {color, label}} (light -> dark order recommended); missing parts get ``style.DATA_CYCLE``.
    Stores ``ax._anchor_frac`` {label: {part: fraction}} and ``ax._anchor_absent`` (labels)."""
    rows = rows.reset_index(drop=True)
    palette = palette or {}
    n = len(rows)
    y = np.arange(n)[::-1].astype(float)
    frac, absent = {}, []
    for yi, r in zip(y, rows.to_dict("records")):
        v = np.array([float(r.get(p, 0) or 0) for p in parts])
        tot = np.nansum(v)
        if not np.isfinite(tot) or tot <= 0:
            style.aux(*ax.barh([yi], [1.0], height=0.7, color=style.NA_FILL, hatch=hatch,
                               edgecolor=style.GREY, linewidth=0).patches)
            ax.text(0.5, yi, absent_text, ha="center", va="center", fontsize=6, color=style.DARK_GREY)
            absent.append(r["label"])
            continue
        f = v / tot
        left = 0.0
        for i, (p, fi) in enumerate(zip(parts, f)):
            st = palette.get(p, {})
            c = st.get("color", style.DATA_CYCLE[i % len(style.DATA_CYCLE)])
            ax.barh([yi], [fi], left=left, height=0.7, color=c, edgecolor="none",
                    label=st.get("label", str(p)) if not frac else None)
            left += fi
        frac[r["label"]] = dict(zip(parts, map(float, f)))
    ax.set_yticks(y, rows["label"].tolist())
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Fraction")
    ax._anchor_frac = frac
    ax._anchor_absent = absent
    return ax
