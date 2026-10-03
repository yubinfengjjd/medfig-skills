"""Small statistics helpers for panels (no plotting).

Odds ratios after MenglinLu/Retinal_VascularEvents, OR.py (MIT licence): Woolf (log) 95% CI and risk
groups compared with the lowest group. Changes: explicit 2x2 counts, Haldane-Anscombe 0.5 correction
when any cell is 0 (flagged, never silent), quantile groups built with one np.quantile call.
"""
import numpy as np
import pandas as pd

Z95 = 1.959963984540054


def odds_ratio(a, b, c, d, z=Z95):
    """OR = (a d) / (b c) for exposed (a events, b non-events) vs reference (c events, d non-events).

    Returns dict(or_, lo, hi, corrected): Woolf CI exp(ln OR ± z sqrt(1/a + 1/b + 1/c + 1/d)); a zero
    cell adds 0.5 to all four cells and sets ``corrected=True`` (report it in the caption)."""
    cells = np.array([a, b, c, d], float)
    if cells.shape != (4,) or not np.isfinite(cells).all() or (cells < 0).any():
        raise ValueError("odds_ratio needs four finite, non-negative counts")
    corrected = bool((cells == 0).any())
    if corrected:
        cells = cells + 0.5
    a, b, c, d = cells
    lor = np.log(a * d / (b * c))
    se = np.sqrt((1 / cells).sum())
    return dict(or_=float(np.exp(lor)), lo=float(np.exp(lor - z * se)), hi=float(np.exp(lor + z * se)),
                corrected=corrected)


def risk_group_or(y_true, y_prob, n_groups=10, edges=None):
    """OR of each predicted-risk group vs the lowest group.

    ``edges`` (inner cut points, e.g. [0.25, 0.75]) or ``n_groups`` quantile groups. Group i holds
    edges[i-1] <= p < edges[i] (last group closed). Returns a DataFrame: group, lo_edge, hi_edge, n,
    events, or_, lo, hi, corrected (row 0 = reference, OR 1, no CI)."""
    y = np.asarray(y_true)
    p = np.asarray(y_prob, float)
    if y.shape != p.shape or y.ndim != 1 or not np.isin(y, (0, 1)).all() or not np.isfinite(p).all():
        raise ValueError("risk_group_or needs binary 1-D y_true and finite y_prob of equal length")
    inner = (np.asarray(edges, float) if edges is not None
             else np.quantile(p, np.linspace(0, 1, int(n_groups) + 1)[1:-1]))
    g = np.searchsorted(inner, p, side="right")
    bounds = np.r_[p.min(), inner, p.max()]
    ref = g == 0
    c, d = int(y[ref].sum()), int((~y[ref].astype(bool)).sum())
    rows = []
    for i in range(len(inner) + 1):
        m = g == i
        a, b = int(y[m].sum()), int(m.sum() - y[m].sum())
        r = (dict(or_=1.0, lo=np.nan, hi=np.nan, corrected=False) if i == 0 else odds_ratio(a, b, c, d))
        rows.append(dict(group=i + 1, lo_edge=float(bounds[i]), hi_edge=float(bounds[i + 1]),
                         n=int(m.sum()), events=a, **r))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- agreement, P text, evidence checks
def bland_altman(a, b, k=1.96, ci=0.95, ddof=1):
    """Bland-Altman agreement of paired measurements ``a`` (e.g. predicted) and ``b`` (e.g. measured).

    diff = a - b, mean = (a + b) / 2; bias = mean diff, limits of agreement bias ± k·SD. SD uses ``ddof=1``
    (sample SD, Bland & Altman 1986); statsmodels' mean_diff_plot uses ddof = 0 -- pass ``ddof=0`` to
    reproduce it. Bias CI: Student t with n - 1 df. Pairs with a
    non-finite value are dropped and counted in ``n_dropped`` (report it). Returns a dict of arrays / floats."""
    from scipy import stats as st
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.shape != b.shape or a.ndim != 1:
        raise ValueError("bland_altman: a and b must be 1-D arrays of the same length")
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    n = len(a)
    if n < 3:
        raise ValueError("bland_altman needs at least 3 finite pairs")
    d = a - b
    bias, sd = float(d.mean()), float(d.std(ddof=ddof))
    t = float(st.t.ppf(0.5 + ci / 2, n - 1))
    se = float(d.std(ddof=1)) / np.sqrt(n)
    return dict(n=n, n_dropped=int((~m).sum()), mean=(a + b) / 2, diff=d, bias=bias, sd=sd,
                loa_lo=bias - k * sd, loa_hi=bias + k * sd, bias_lo=bias - t * se, bias_hi=bias + t * se, k=k,
                ddof=ddof)


_SUP = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def p_text(p, floor=1e-6):
    """Exact P for figures and tables: 'P = 0.012' (3 dp below 0.05 ... 2 dp from 0.1), 'P = 4.2 × 10⁻⁴'
    below 0.001, 'P < 1 × 10⁻⁶' below ``floor``, 'P > 0.99' at the top. Never stars."""
    p = float(p)
    if not np.isfinite(p) or not 0 <= p <= 1:
        raise ValueError(f"p_text: P must be in [0, 1], got {p}")
    if p > 0.99:
        return "P > 0.99"
    if p < floor:
        e = int(np.floor(np.log10(floor)))
        return f"P < 1 × 10{str(e).translate(_SUP)}"
    if p < 0.001:
        m, e = f"{p:.1e}".split("e")
        return f"P = {m} × 10{str(int(e)).translate(_SUP)}"
    if p < 0.1:
        return f"P = {p:.3f}"
    return f"P = {p:.2f}"


def structure_strength(x, y, kind="paired", nbins=10):
    """Will a per-sample cloud SHOW a structure? (pre-check before drawing a paired / mechanism scatter).

    After taoge946/academic-figure-patterns, afp/evidence.py ``structure_strength`` (MIT licence,
    Copyright (c) 2026 Jintao Li); thresholds are that project's calibrated conventions, not tests.
    kind="paired": passes when |r| > 0.9. kind="mechanism": passes when |r| > 0.5 or the rise of binned
    medians (quantile bins in x, >= 5 points) exceeds the median IQR width. A failing check means: choose
    another form (difference distribution, table row), not another result."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    r = float(np.corrcoef(x, y)[0, 1]) if len(x) > 2 else float("nan")
    out = dict(n=int(len(x)), corr=r, kind=kind)
    if kind == "paired":
        out["passes"] = bool(abs(r) > 0.9)
        return out
    if kind != "mechanism":
        raise ValueError("structure_strength: kind must be 'paired' or 'mechanism'")
    b = binned_median(x, y, nbins=nbins, min_count=5)
    rise = float(np.max(b["median"]) - np.min(b["median"])) if len(b["median"]) else float("nan")
    band = float(np.median(b["q75"] - b["q25"])) if len(b["median"]) else float("nan")
    out.update(median_rise=rise, median_iqr=band, passes=bool(abs(r) > 0.5 or rise > band))
    return out


def binned_median(x, y, nbins=10, min_count=5):
    """Quantile bins in x -> per-bin centre (median x), median / q25 / q75 of y and count (bins with fewer
    than ``min_count`` points dropped). Idea after taoge946/academic-figure-patterns (MIT)."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    edges = np.quantile(x, np.linspace(0, 1, nbins + 1))
    idx = np.clip(np.searchsorted(edges, x, side="right") - 1, 0, nbins - 1)
    rows = []
    for k in range(nbins):
        s = idx == k
        if s.sum() >= min_count:
            q25, med, q75 = np.percentile(y[s], [25, 50, 75])
            rows.append((np.median(x[s]), med, q25, q75, int(s.sum())))
    a = np.array(rows, float).reshape(-1, 5)
    return dict(center=a[:, 0], median=a[:, 1], q25=a[:, 2], q75=a[:, 3], count=a[:, 4].astype(int))


def exceedance(values, xs=None, n=200):
    """Fraction of samples strictly above each x (survival-style tail curve of an error / score).
    ``xs`` default: ``n`` points spanning the finite values. Returns (xs, fraction)."""
    v = np.asarray(values, float)
    v = np.sort(v[np.isfinite(v)])
    if not len(v):
        raise ValueError("exceedance needs at least one finite value")
    xs = np.linspace(v[0], v[-1], n) if xs is None else np.asarray(xs, float)
    frac = 1.0 - np.searchsorted(v, xs, side="right") / len(v)
    return xs, frac
