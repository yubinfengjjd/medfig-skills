"""Interval panels: forest, dumbbell and paired estimation plots (S3: coloured data, grey guides only)."""
import numpy as np
import pandas as pd

from .. import style

GREY, BAND = style.GREY, style.BAND


def _col(rows, name, default):
    return rows[name].tolist() if name in rows else [default] * len(rows)


def forest(ax, rows: pd.DataFrame, ref, band_rows=None, color=None):
    """Point estimate + interval per row; row order is top -> bottom.

    ``rows``: ``label``, ``est``, ``lo``, ``hi``; optional ``color`` / ``marker`` per row (default
    ``color`` argument or the first ``style.DATA_CYCLE`` colour, marker "o"). ``ref`` draws a dashed
    reference line (axvline, auxiliary); ``band_rows`` (row positions) get an auxiliary grey band.
    """
    rows = rows.reset_index(drop=True)
    n = len(rows)
    y = np.arange(n)[::-1].astype(float)
    for i in (() if band_rows is None else band_rows):
        style.aux(ax.axhspan(y[i] - 0.5, y[i] + 0.5, color=BAND, zorder=0, linewidth=0))
    if ref is not None:
        ax.axvline(ref, color=GREY, linestyle="--", linewidth=0.6, zorder=1)
    colors = _col(rows, "color", color or style.DATA_CYCLE[0])
    markers = _col(rows, "marker", "o")
    for yi, r, c, m in zip(y, rows.itertuples(index=False), colors, markers):
        ax.errorbar(r.est, yi, xerr=[[r.est - r.lo], [r.hi - r.est]], fmt=m, color=c,
                    ms=3.5, elinewidth=0.8, capsize=0, zorder=3)
    ax.set_yticks(y, rows["label"].tolist())
    ax.set_ylim(-0.6, n - 0.4)
    ax._anchor_y = dict(zip(rows["label"], y))
    return ax


def dumbbell(ax, rows: pd.DataFrame, a_kw=None, b_kw=None, segment_color=None):
    """Horizontal dumbbell per row (top -> bottom): segment from ``a`` to ``b`` plus one marker per end.

    ``rows``: ``label``, ``a``, ``b``. Defaults: a = Okabe-Ito blue circles, b = vermillion diamonds,
    segment = sky blue; ``a_kw`` / ``b_kw`` update the scatter kwargs (pass ``label=`` for a legend).
    """
    rows = rows.reset_index(drop=True)
    n = len(rows)
    y = np.arange(n)[::-1].astype(float)
    ax.hlines(y, rows["a"], rows["b"], color=segment_color or style.DATA_CYCLE[5], linewidth=0.8, zorder=1)
    ka = dict(s=12, zorder=3, color=style.DATA_CYCLE[0], marker="o")
    ka.update(a_kw or {})
    kb = dict(s=12, zorder=3, color=style.DATA_CYCLE[1], marker="D")
    kb.update(b_kw or {})
    ax.scatter(rows["a"], y, **ka)
    ax.scatter(rows["b"], y, **kb)
    ax.set_yticks(y, rows["label"].tolist())
    ax.set_ylim(-0.6, n - 0.4)
    ax._anchor_delta = (rows["b"] - rows["a"]).to_numpy()
    return ax


def estimation(ax_left, ax_right, paired: pd.DataFrame, deltas: pd.DataFrame,
               a_label="A", b_label="B", color=None, *, extra_right=(), ticks=True):
    """Left: paired slope lines a -> b per replicate. Right: delta estimates with CI around y = 0.

    Optional per-row columns (absent -> defaults):
      ``paired``: ``xa``/``xb`` x positions (default 0 / 1), ``a_kw``/``b_kw`` dicts of marker kwargs
      for the a / b end (e.g. ``dict(marker="o", mfc="none")``), ``line_color`` (default ``color`` at
      alpha 0.5, never grey: the slope lines are data).
      ``deltas``: ``x`` position (default 0..n-1), ``kw`` dict of errorbar kwargs (fmt, mfc, mec, color).
    ``extra_right``: further axes that receive the identical delta drawing (segments of a broken y axis;
    the caller sets their limits). ``ticks=False`` leaves x ticks / xlim to the caller.
    """
    color = color or style.DATA_CYCLE[0]
    per_end = "a_kw" in paired or "b_kw" in paired
    for r in paired.to_dict("records"):
        xa, xb = r.get("xa", 0.0), r.get("xb", 1.0)
        lc = r.get("line_color") or color
        la = 1.0 if r.get("line_color") else 0.5
        if not per_end:  # one marker-bearing line per pair
            ax_left.plot([xa, xb], [r["a"], r["b"]], color=lc, alpha=la, linewidth=0.6,
                         marker="o", ms=2.5, mfc=color, mec=color, zorder=2)
            continue
        ax_left.plot([xa, xb], [r["a"], r["b"]], color=lc, alpha=la, linewidth=0.6, zorder=2)
        for x_, y_, kw in ((xa, r["a"], r.get("a_kw")), (xb, r["b"], r.get("b_kw"))):
            k = dict(marker="o", ms=2.5, mfc=color, mec=color, linestyle="none", zorder=3)
            k.update(kw if isinstance(kw, dict) else {})
            ax_left.plot([x_], [y_], **k)
    if ticks:
        ax_left.set_xticks([0, 1], [a_label, b_label])
        ax_left.set_xlim(-0.3, 1.3)
    deltas = deltas.reset_index(drop=True)
    x = deltas["x"].to_numpy(float) if "x" in deltas else np.arange(len(deltas), dtype=float)
    est, lo, hi = (deltas[c].to_numpy(float) for c in ("est", "lo", "hi"))
    for ax in (ax_right, *extra_right):
        ax.axhline(0, color=GREY, linestyle="--", linewidth=0.6, zorder=1)
        for i in range(len(deltas)):
            k = dict(fmt="o", color=color, ms=3.5, elinewidth=0.8, capsize=0, zorder=3)
            kw = deltas["kw"].iloc[i] if "kw" in deltas else None
            k.update(kw if isinstance(kw, dict) else {})
            ax.errorbar([x[i]], [est[i]], yerr=[[est[i] - lo[i]], [hi[i] - est[i]]], **k)
    if ticks:
        ax_right.set_xticks(x, deltas["label"].tolist())
        ax_right.set_xlim(x.min() - 0.6, x.max() + 0.6)
    ax_left._anchor_paired_delta = (paired["b"] - paired["a"]).to_numpy()
    ax_right._anchor_delta_x = x
    return ax_left, ax_right


def or_forest(ax, rows: pd.DataFrame, color=None, ref_label=True):
    """Odds-ratio forest on a log x axis (e.g. ``stats.risk_group_or`` output); rows top -> bottom.

    ``rows``: ``label``, ``or_``, ``lo``, ``hi``; a row with NaN CI is the reference (hollow marker at
    1, "ref" annotation when ``ref_label``). ``corrected`` rows (zero-cell 0.5 correction) get a hollow
    marker too. OR = 1 is an aux dashed line. Stores ``ax._anchor_or`` (label -> (or, lo, hi))."""
    rows = rows.reset_index(drop=True)
    n = len(rows)
    y = np.arange(n)[::-1].astype(float)
    color = color or style.DATA_CYCLE[0]
    style.aux(ax.axvline(1.0, color=GREY, linestyle="--", linewidth=0.6, zorder=1))
    corr = _col(rows, "corrected", False)
    for yi, r, cr in zip(y, rows.itertuples(index=False), corr):
        if not np.isfinite(r.lo):
            ax.plot([1.0], [yi], "o", ms=3.5, mfc="white", mec=color, mew=0.8, zorder=3)
            if ref_label:
                ax.annotate("ref", (1.0, yi), xytext=(4, 0), textcoords="offset points",
                            va="center", fontsize=6)
            continue
        ax.errorbar(r.or_, yi, xerr=[[r.or_ - r.lo], [r.hi - r.or_]], fmt="o", color=color,
                    mfc="white" if cr else color, ms=3.5, elinewidth=0.8, capsize=0, zorder=3)
    ax.set_xscale("log")
    ax.set_yticks(y, rows["label"].tolist())
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlabel("Odds ratio (95% CI)")
    ax._anchor_or = {r.label: (r.or_, r.lo, r.hi) for r in rows.itertuples(index=False)}
    return ax


def slope(ax, runs: pd.DataFrame, x, y, group, run, order, colors=None, run_alpha=0.5):
    """Slope chart: thin line per (group, run) at ``run_alpha`` in the group colour, bold mean line
    with markers per group. ``order``: x categories left -> right. ``colors``: {group: colour or
    palette dict}. Stores ``ax._anchor_slope_mean`` {group: list of means in ``order``}."""
    colors = colors or {}
    xi = {v: i for i, v in enumerate(order)}
    means = {}
    for k, (g, sub) in enumerate(runs.groupby(group, sort=False)):
        c = colors.get(g) or style.DATA_CYCLE[k % len(style.DATA_CYCLE)]
        c = c["color"] if isinstance(c, dict) else c
        for _, r in sub.groupby(run, sort=False):
            r = r.assign(_x=r[x].map(xi)).sort_values("_x")
            ax.plot(r["_x"], r[y], color=c, alpha=run_alpha, linewidth=0.5, zorder=2)
        m = sub.groupby(x)[y].mean().reindex(order)
        ax.plot(range(len(order)), m.to_numpy(), color=c, linewidth=1.3, marker="o", ms=3.2,
                label=str(g), zorder=3)
        means[g] = m.tolist()
    ax.set_xticks(range(len(order)), list(order))
    ax.set_xlim(-0.3, len(order) - 0.7)
    ax._anchor_slope_mean = means
    return ax


def scorecard(ax, rows: pd.DataFrame, statuses, ref=0.0, legend_loc="lower right"):
    """Hypothesis scorecard: estimate + CI per row (top -> bottom), colour + marker by status.

    ``rows``: ``label``, ``est``, ``lo``, ``hi``, ``status``. ``statuses``: {status: {color, marker,
    label}} (e.g. the toml ``status`` palette). Every status gets a colour (no grey "inconclusive");
    the legend lists only statuses present. ``ref`` = aux dashed line. Unknown status -> ValueError.
    Stores ``ax._anchor_status`` {label: status}."""
    rows = rows.reset_index(drop=True)
    unknown = set(rows["status"]) - set(statuses)
    if unknown:
        raise ValueError(f"scorecard: statuses {sorted(unknown)} not in the status palette")
    n = len(rows)
    y = np.arange(n)[::-1].astype(float)
    if ref is not None:
        style.aux(ax.axvline(ref, color=GREY, linestyle="--", linewidth=0.6, zorder=1))
    seen = []
    for yi, r in zip(y, rows.itertuples(index=False)):
        st = statuses[r.status]
        c = st["color"]
        ax.errorbar(r.est, yi, xerr=[[r.est - r.lo], [r.hi - r.est]], fmt=st.get("marker", "o"),
                    color=c, mec=st.get("edge", c), ms=3.5, elinewidth=0.8, capsize=0, zorder=3)
        if r.status not in seen:
            seen.append(r.status)
    from matplotlib.lines import Line2D
    h = [Line2D([], [], linestyle="none", marker=statuses[s].get("marker", "o"), ms=3.5,
                color=statuses[s]["color"], label=statuses[s].get("label", s)) for s in seen]
    ax.legend(handles=h, loc=legend_loc, frameon=False, handletextpad=0.3)
    ax.set_yticks(y, rows["label"].tolist())
    ax.set_ylim(-0.6, n - 0.4)
    ax._anchor_status = dict(zip(rows["label"], rows["status"]))
    return ax
