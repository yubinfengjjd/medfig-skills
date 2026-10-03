"""Per-sample evidence panels (ideas after taoge946/academic-figure-patterns, MIT licence, Copyright (c)
2026 Jintao Li; re-implemented on figkit conventions): exceedance (tail) curves, paired cloud on the
identity line, binned median + IQR band, Bland-Altman agreement. Prefer these when per-sample data exist
and the claim is about samples (a mean with an error bar hides the structure)."""
import numpy as np

from .. import stats, style


def exceedance(ax, values, color=None, label=None, xs=None, floor=1e-4, logy=True, **kw):
    """Fraction of samples whose value exceeds x ("fewer large errors" reads at the tail). Log y by
    default, clipped at ``floor`` so the curve stays visible. Stores ``ax._anchor_exceedance``."""
    xs, frac = stats.exceedance(values, xs=xs)
    kw.setdefault("linewidth", 1.0)
    ax.step(xs, np.maximum(frac, floor), where="post", color=color, label=label, **kw)
    if logy:
        ax.set_yscale("log")
        style.log_ticks(ax, "y")
    ax.set_ylabel("Fraction of samples above x")
    store = getattr(ax, "_anchor_exceedance", {})
    store[label or f"series{len(store)}"] = (xs, frac)
    ax._anchor_exceedance = store
    return ax


def paired_cloud(ax, x, y, color=None, s=4.0, alpha=0.35, identity=True, lim=None, rasterized=True):
    """Same sample under two conditions (x vs y). Identity line y = x is auxiliary; the claim is the cloud's
    shape (on the diagonal = same, below = y smaller). Stores ``ax._anchor_paired`` with the share below the
    diagonal (``stats``-free, plain count)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    color = color or style.DATA_CYCLE[0]
    ax.scatter(x[m], y[m], s=s, color=color, alpha=alpha, linewidth=0, rasterized=rasterized, zorder=3)
    lo, hi = lim if lim is not None else (min(x[m].min(), y[m].min()), max(x[m].max(), y[m].max()))
    pad = 0.03 * (hi - lo)
    lo, hi = lo - pad, hi + pad
    if identity:
        style.aux(ax.plot([lo, hi], [lo, hi], color=style.GREY, linestyle="--", linewidth=0.6, zorder=1)[0])
    ax.set_xlim(lo, hi); ax.set_ylim(lo, hi)
    ax.set_aspect("equal", adjustable="box")
    ax._anchor_paired = dict(n=int(m.sum()), below_diagonal=float(np.mean(y[m] < x[m])))
    return ax


def binned_median(ax, x, y, nbins=10, color=None, band=True, min_count=5, label=None):
    """Binned medians (quantile bins in x) as a line + markers with an optional IQR band (same hue, light).
    Stores ``ax._anchor_binned`` (the ``stats.binned_median`` dict)."""
    b = stats.binned_median(x, y, nbins=nbins, min_count=min_count)
    color = color or style.DATA_CYCLE[1]
    if band:
        ax.fill_between(b["center"], b["q25"], b["q75"], color=style.tint(color, 0.7), linewidth=0, zorder=2)
    ax.plot(b["center"], b["median"], color=color, marker="o", ms=3, linewidth=1.0, label=label, zorder=4)
    ax._anchor_binned = b
    return ax


def bland_altman(ax, a, b, color=None, s=6.0, alpha=0.5, k=1.96, units="", labels=True, rasterized=True):
    """Bland-Altman agreement: x = mean of the pair, y = difference (a - b); dashed bias and limits of
    agreement (bias ± k·SD, sample SD) as auxiliary reference lines, labelled at the right edge with their
    values. Stores ``ax._anchor_ba`` (``stats.bland_altman`` without the arrays)."""
    r = stats.bland_altman(a, b, k=k)
    color = color or style.DATA_CYCLE[0]
    ax.scatter(r["mean"], r["diff"], s=s, color=color, alpha=alpha, linewidth=0, rasterized=rasterized, zorder=3)
    ax.axhline(r["bias"], color=style.DARK_GREY, linewidth=0.7, zorder=2)
    for v in (r["loa_lo"], r["loa_hi"]):
        ax.axhline(v, color=style.GREY, linestyle="--", linewidth=0.6, zorder=2)
    if labels:
        u = f" {units}" if units else ""
        fmt = lambda v: f"{v:.1f}".replace("-", "−")  # noqa: E731
        for v, name in ((r["bias"], "Bias"), (r["loa_hi"], f"+{k:g} SD"), (r["loa_lo"], f"−{k:g} SD")):
            ax.annotate(f"{name} {fmt(v)}{u}", xy=(1, v), xycoords=("axes fraction", "data"), xytext=(-2, 2),
                        textcoords="offset points", ha="right", va="bottom", fontsize=6)
    ax.set_xlabel(f"Mean of the two measurements{f' ({units})' if units else ''}")
    ax.set_ylabel(f"Difference{f' ({units})' if units else ''}")
    ax._anchor_ba = {k_: v for k_, v in r.items() if k_ not in ("mean", "diff")}
    return ax
