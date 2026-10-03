"""Comparison panels in the soft-theme look (idea after senlanke/figures4papers, re-derived; that repository
has no licence, so no code is taken): multi-metric bars with a shared legend, ordinal ablation bars,
cumulative area trend, plus P-value brackets (bracket idea after O0000-code/SSCI-Plots, MIT; exact P
instead of stars).

2026-10-07 rulings: one saturated emphasis colour for the proposed method, light controls; flat bars (no
edge, no hatch); values printed on the bars (<= ``VALUE_LABEL_MAX`` bars per axes); thin dark error bars
with caps; runs are summarised (whisker = min-max for n <= 5, else ± SD, stated in ``ax._anchor_whisker``
for the caption), run points only on request; a value axis that does not start at 0 carries a break mark
(``style.axis_break``; ``qa.bar_baseline_audit`` fails the export otherwise).
"""
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

from .. import stats, style

VALUE_LABEL_MAX = 5  # up to this many bars: 6 pt horizontal value labels; more bars: 5 pt (qa.VALUE_LABEL_PT),
#                      rotated 90° when a horizontal label would be wider than its bar slot


def method_colours(methods, emphasis=None, controls="pastel", palette=None):
    """{method: face colour}: ``emphasis`` -> ``style.SOFT_EMPHASIS``, the others -> ``style.soft_controls``
    (``controls`` = "pastel" | "gradient"); ``palette`` ({method: colour}) overrides."""
    if palette is not None:
        return {m: palette[m] for m in methods}
    others = [m for m in methods if m != emphasis]
    ctrl = style.soft_controls(len(others), kind=controls) if others else []
    out = dict(zip(others, ctrl))
    if emphasis is not None:
        out[emphasis] = style.SOFT_EMPHASIS
    return {m: out[m] for m in methods}


def _floor(lo, hi, base=None):
    """Truncated axis start: ``base`` if given, else lo minus 40% of the span, rounded down to a 0.05 /
    0.1 / 0.5 ... step and never below 0."""
    if base is not None:
        return float(base)
    span = max(hi - lo, 1e-9)
    raw = lo - 0.4 * span
    step = 10 ** np.floor(np.log10(span))
    step = step / 2 if span / step < 3 else step
    return max(0.0, float(np.floor(raw / step) * step))


def _fmt(v, decimals):
    return f"{v:.{decimals}f}".replace("-", "−")  # true minus


def metric_bars(ax, df: pd.DataFrame, metric, methods, method_col="method", value_col="value",
                emphasis=None, controls="pastel", palette=None, ylabel=None, higher_is_better=True,
                ylim=None, truncate="auto", values=True, decimals=3, show_runs=False):
    """One metric, one flat bar per method (mean over runs), method order = ``methods``.

    ``df``: long table with ``method_col`` and ``value_col`` (one row per run / seed / fold). Whisker =
    min-max over runs when n <= 5, else mean ± SD (``ax._anchor_whisker`` names it for the caption).
    ``ylim``: (lo, hi); ``truncate``: "auto" (start the value axis below the data when the bars would
    otherwise look flat: lowest mean > 40% of the top) | True | False (from 0). A truncated axis gets a
    break mark. ``values``: print means on the bars (6 pt; > ``VALUE_LABEL_MAX`` bars: 5 pt, rotated 90°
    when too wide). x ticks are
    hidden: pair with ``legend_panel`` / ``legend_inside``. Stores ``ax._anchor_bars`` {method: mean, lo,
    hi, n}, ``ax._anchor_ylim``, ``ax._anchor_truncated``, ``ax._anchor_colours``."""
    col = method_colours(methods, emphasis, controls, palette)
    summ = {}
    for m in methods:
        v = df.loc[df[method_col] == m, value_col].to_numpy(float)
        v = v[np.isfinite(v)]
        if not len(v):
            raise ValueError(f"metric_bars: no finite values for method {m!r}")
        if len(v) <= 5:
            lo, hi = float(v.min()), float(v.max())
        else:
            sd = float(v.std(ddof=1)); lo, hi = float(v.mean()) - sd, float(v.mean()) + sd
        mu = float(v.mean())
        summ[m] = dict(mean=mu, lo=min(lo, mu), hi=max(hi, mu), n=int(len(v)), runs=v)  # float-safe whisker
    lo_all = min(s["lo"] for s in summ.values())
    hi_all = max(s["hi"] for s in summ.values())
    if ylim is not None:
        y0, y1 = map(float, ylim)
    else:
        trunc = truncate is True or (truncate == "auto" and lo_all > 0 and min(s["mean"] for s in summ.values())
                                     > 0.4 * hi_all)
        y0 = _floor(lo_all, hi_all) if trunc else 0.0
        y1 = hi_all + (hi_all - y0) * (0.16 if values else 0.08)
    x = np.arange(len(methods), dtype=float)
    dense = len(methods) > VALUE_LABEL_MAX
    vfs = 5.0 if dense else 6.0
    labels = []
    for xi, m in zip(x, methods):
        s = summ[m]
        ax.bar([xi], [s["mean"] - y0], bottom=y0, width=0.72, color=col[m], edgecolor="none", linewidth=0,
               zorder=2)
        eb = ax.errorbar([xi], [s["mean"]], yerr=[[s["mean"] - s["lo"]], [s["hi"] - s["mean"]]], fmt="none",
                         ecolor=style.ERR_COLOUR, elinewidth=0.7, capsize=2, capthick=0.7, zorder=3)
        for a in eb.lines[1] + eb.lines[2]:  # caps / whisker: auxiliary (dark grey, not data colour)
            style.aux(a)
        if s["n"] <= 5 and show_runs:
            ax.scatter(np.full(s["n"], xi), s["runs"], s=5, color=style.ERR_COLOUR, linewidth=0, zorder=4)
        if values:
            t = ax.text(xi, s["hi"] + (y1 - y0) * 0.02, _fmt(s["mean"], decimals), ha="center", va="bottom",
                        fontsize=vfs, zorder=5)
            t._figkit_value_label = True
            labels.append(t)
    ax.set_xticks([])
    ax.set_xlim(-0.6, len(methods) - 0.4)
    ax.set_ylim(y0, y1)
    if labels and dense:  # rotate when a horizontal label is wider than one bar slot
        r = ax.figure.canvas.get_renderer()
        slot = ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]
        if max(t.get_window_extent(r).width for t in labels) > 0.92 * slot:
            for t in labels:
                t.set_rotation(90)
            tall = max(t.get_window_extent(r).height for t in labels) / max(ax.bbox.height, 1)
            y1 = hi_all + (y1 - y0) * (tall + 0.06) / max(1 - tall - 0.06, 0.3)
            ax.set_ylim(y0, y1)
    if y0 > 0:
        style.axis_break(ax, "y")
    arrow = " ↑" if higher_is_better else " ↓"
    ax.set_ylabel(ylabel if ylabel is not None else f"{metric}{arrow}")
    controls_used = [col[m] for m in methods if m != emphasis]
    if controls_used:
        style.mark_controls(ax, controls_used)
    ax._anchor_bars = {m: {k: v for k, v in s.items() if k != "runs"} for m, s in summ.items()}
    ax._anchor_whisker = "min–max over runs" if max(s["n"] for s in summ.values()) <= 5 else "mean ± SD"
    ax._anchor_ylim = (y0, y1)
    ax._anchor_truncated = y0 > 0
    ax._anchor_colours = col
    return ax


def _handles(methods, col, labels):
    labels = labels or {}
    return [Patch(facecolor=col[m], edgecolor="none", label=labels.get(m, m)) for m in methods]


def legend_panel(ax, methods, labels=None, emphasis=None, controls="pastel", palette=None, title=None,
                 ncol=1, frame=True):
    """Legend-only auxiliary axes for a row of ``metric_bars`` (figures4papers style 1: framed box)."""
    col = method_colours(methods, emphasis, controls, palette)
    leg = ax.legend(handles=_handles(methods, col, labels), loc="center left", frameon=frame, title=title,
                    ncol=ncol, handlelength=1.4, handleheight=1.0, borderaxespad=0, borderpad=0.6,
                    fancybox=False, edgecolor=style.GREY)
    leg.get_frame().set_linewidth(0.6)
    ax.set_axis_off()
    style.aux(ax)
    return ax


def legend_inside(ax, methods, labels=None, emphasis=None, controls="pastel", palette=None, ncol=2):
    """Legend inside the axes, top (figures4papers style 2); leave head room with ``metric_bars(ylim=...)``."""
    col = method_colours(methods, emphasis, controls, palette)
    ax.legend(handles=_handles(methods, col, labels), loc="upper left", ncol=ncol, frameon=False,
              handlelength=1.2, handleheight=0.9, columnspacing=0.8, borderaxespad=0.2)
    return ax


def ordinal_bars(ax, rows: pd.DataFrame, color=None, label_col="label", value_col="value",
                 lo_col=None, hi_col=None, xlabel="", xlim=None, values=True, decimals=3):
    """Horizontal flat bars for an ORDERED series (ablation completeness, grade): top row = first level,
    colour = single-hue ``style.ordinal_gradient`` light -> dark (2..5 levels; soft ends
    ``style.ORDINAL_SOFT``). Optional interval columns (dark-grey whiskers). The value axis is truncated
    below the data when the bars would look flat (break mark), unless ``xlim`` is given. Values printed at
    the bar ends. Stores ``ax._anchor_ordinal`` {label: value}, ``ax._anchor_xlim``."""
    rows = rows.reset_index(drop=True)
    n = len(rows)
    color = color or style.SOFT_KEYS[0]  # Okabe-Ito blue: 4 soft levels (SOFT_EMPHASIS only 3)
    lo_t, hi_t = style.ORDINAL_SOFT
    g = style.ordinal_gradient(color, n, lo=lo_t, hi=hi_t)
    v = rows[value_col].to_numpy(float)
    lo = rows[lo_col].to_numpy(float) if lo_col else v
    hi = rows[hi_col].to_numpy(float) if hi_col else v
    if xlim is not None:
        x0, x1 = map(float, xlim)
    else:
        x0 = _floor(float(lo.min()), float(hi.max())) if v.min() > 0.4 * hi.max() else 0.0
        x1 = float(hi.max()) + (float(hi.max()) - x0) * (0.2 if values else 0.06)
    y = np.arange(n)[::-1].astype(float)
    for i, yi in enumerate(y):
        ax.barh([yi], [v[i] - x0], left=x0, height=0.68, color=g[i], edgecolor="none", linewidth=0, zorder=2)
        if lo_col and hi_col:
            eb = ax.errorbar([v[i]], [yi], xerr=[[v[i] - lo[i]], [hi[i] - v[i]]], fmt="none",
                             ecolor=style.ERR_COLOUR, elinewidth=0.7, capsize=2, capthick=0.7, zorder=3)
            for a in eb.lines[1] + eb.lines[2]:
                style.aux(a)
        if values:
            ax.text(hi[i] + (x1 - x0) * 0.02, yi, _fmt(v[i], decimals), ha="left", va="center", fontsize=6)
    ax.set_yticks(y, rows[label_col].tolist())
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlim(x0, x1)
    if x0 > 0:
        style.axis_break(ax, "x")
    ax.set_xlabel(xlabel)
    style.mark_ordinal(ax, g)
    ax._anchor_ordinal = dict(zip(rows[label_col], v.astype(float)))
    ax._anchor_xlim = (x0, x1)
    return ax


def area_trend(ax, x, series: dict, colors=None, cumulative=False, hatches=None, events=None):
    """Overlaid area trend: per series a light tint fill from 0 plus a line one tone darker than the key
    colour; an optional hatch is drawn in that darker tone. ``series``: {label: y array} (drawn largest-first
    so smaller areas stay visible). ``events``: [(x, label)] -> short arrow annotation on the top series (a
    reading key). Legend handles combine fill + line. Stores ``ax._anchor_area`` {label: plotted y}."""
    from matplotlib.legend_handler import HandlerTuple
    import matplotlib.lines as mlines
    x = np.asarray(x, float)
    labels = list(series)
    keys = colors or [style.SOFT_EMPHASIS] + style.SOFT_KEYS[1:]
    keys = [keys[i] if isinstance(keys, list) else keys[k] for i, k in enumerate(labels)]
    hatches = hatches or {}
    ys = {k: (np.cumsum(series[k]) if cumulative else np.asarray(series[k], float)) for k in labels}
    handles = []
    for k in sorted(labels, key=lambda k: -float(np.nanmax(ys[k]))):
        c = keys[labels.index(k)]
        face, line = style.tint(c, 0.62), style._mix(c, -0.2)
        h = hatches.get(k, "")
        ax.fill_between(x, 0, ys[k], facecolor=face, edgecolor=line if h else "none", hatch=h,
                               linewidth=0, zorder=1)
        ax.plot(x, ys[k], color=line, linewidth=1.2, zorder=3)
    for k in labels:
        c = keys[labels.index(k)]
        handles.append((Patch(facecolor=style.tint(c, 0.62), edgecolor=style._mix(c, -0.2) if hatches.get(k)
                              else "none", hatch=hatches.get(k, ""), linewidth=0),
                        mlines.Line2D([], [], color=style._mix(c, -0.2), linewidth=1.2)))
    ax.legend(handles, labels, handler_map={tuple: HandlerTuple(ndivide=1, pad=0)}, loc="upper left",
              frameon=False, handlelength=1.6)
    top = max(labels, key=lambda k: float(np.nanmax(ys[k])))
    for ex, et in events or []:
        ey = float(np.interp(ex, x, ys[top]))
        span = float(np.nanmax(ys[top]))
        ax.annotate(et, (ex, ey), xytext=(ex, ey + 0.22 * span), ha="center", va="bottom", fontsize=6,
                    arrowprops=dict(arrowstyle="-|>", lw=0.7, color=style.DARK_GREY, mutation_scale=6))
    ax.set_ylim(0, float(max(np.nanmax(v) for v in ys.values())) * (1.35 if events else 1.08))
    ax.set_xlim(x.min(), x.max())
    ax._anchor_area = ys
    return ax


def p_bracket(ax, x1, x2, y, p, h=None, text=None, fontsize=6):
    """Bracket between x positions ``x1`` and ``x2`` at height ``y`` with the exact P (``stats.p_text``;
    never stars; bracket idea after O0000-code/SSCI-Plots, MIT). Auxiliary line (dark grey). Returns the
    label Text."""
    h = h if h is not None else 0.02 * np.diff(ax.get_ylim())[0]
    ln, = ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], color=style.DARK_GREY, linewidth=0.6, zorder=5,
                  clip_on=False)
    style.aux(ln)
    t = ax.text((x1 + x2) / 2, y + h, text or stats.p_text(p), ha="center", va="bottom", fontsize=fontsize)
    return t
