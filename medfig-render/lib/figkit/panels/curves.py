"""Curve panels: ordered-stage ladder, grouped x-y lines (capture, intervention) and mean ± SD ROC.

S3: every data line is coloured (``figkit.toml`` palette or ``style.DATA_CYCLE``); orders / methods
are told apart by linestyle + marker on top of colour, never by black vs grey.
"""
import numpy as np
import pandas as pd

from .. import config, style

GREY = style.GREY
LINESTYLES = ["-", "--", ":", "-."]
MARKERS = ["o", "s", "^", "D", "v", "P"]


def _palette(kind, palette):
    """Explicit palette, else the ``figkit.toml`` table ``kind`` when a config is active, else {}."""
    if palette is not None:
        return palette
    try:
        return style.palette(kind)
    except (RuntimeError, KeyError):
        return {}


def _entry(pal, key, i):
    s = pal.get(key)
    if s:
        c = s.get("color", style.DATA_CYCLE[i % len(style.DATA_CYCLE)])
        return c, s.get("marker", "o"), s.get("label", str(key)), s.get("edge", c)
    c = style.DATA_CYCLE[i % len(style.DATA_CYCLE)]
    return c, MARKERS[i % len(MARKERS)], str(key), c


def step_ladder(ax, df: pd.DataFrame, stages, group="dataset", palette=None, stage="stage",
                value="value", probe="probe"):
    """x = stage index (ordered stages, so points are connected), one line per ``group`` value.

    Styles come from ``palette`` ({name: {color, marker, label, edge}}) or the config's ``cohort``
    palette; unknown groups get ``style.DATA_CYCLE`` colours. Rows whose ``probe`` column is True are
    hollow markers (face = white, edge = group colour); the column is optional. ``stage`` / ``value`` /
    ``probe`` name the columns."""
    stages = list(stages)
    pal = _palette("cohort", palette)
    for i, (key, g) in enumerate(df.groupby(group, sort=False)):
        g = g.assign(_x=g[stage].map(stages.index)).sort_values("_x")
        color, marker, label, edge = _entry(pal, key, i)
        ax.plot(g["_x"], g[value], color=color, linewidth=0.8, label=label, zorder=2)
        hol = g[probe].astype(bool) if probe in g else pd.Series(False, index=g.index)
        solid, hollow = g[~hol], g[hol]
        ax.plot(solid["_x"], solid[value], linestyle="none", marker=marker, ms=3,
                mfc=color, mec=edge, mew=0.5, zorder=3)
        if len(hollow):
            ax.plot(hollow["_x"], hollow[value], linestyle="none", marker=marker, ms=3,
                    mfc="white", mec=edge, mew=0.7, zorder=3)
    ax.set_xticks(range(len(stages)), stages)
    ax.set_xlim(-0.3, len(stages) - 0.7)
    return ax


def _grouped_lines(ax, df, x, y, group, colors=None, color_key=None, style_key=None, label=str):
    """One line per ``group`` value (``group`` may be a list -> tuple keys).

    Colour: ``colors[key]`` or ``colors[color_key(key)]``, else ``DATA_CYCLE`` by colour key.
    Linestyle + marker: by ``style_key(key)`` (redundant encoding), else by group index."""
    colors = colors or {}
    ckeys, skeys = {}, {}
    for i, (key, g) in enumerate(df.groupby(group, sort=False)):
        g = g.sort_values(x)
        ck = color_key(key) if color_key else key
        sk = style_key(key) if style_key else None
        ci = ckeys.setdefault(ck, len(ckeys))
        si = skeys.setdefault(sk, len(skeys)) if style_key else 0
        c = colors.get(key) or colors.get(ck) or style.DATA_CYCLE[ci % len(style.DATA_CYCLE)]
        ax.plot(g[x], g[y], color=c, linewidth=0.9, ms=2.5,
                linestyle=LINESTYLES[si % len(LINESTYLES)],
                marker=MARKERS[(si if style_key else ci) % len(MARKERS)], label=label(key))
    return ax


def capture(ax, df: pd.DataFrame, colors=None, x="budget", y="capture", group="signal",
            xlabel="Review budget", ylabel="Error capture", color_key=None, style_key=None):
    """``y`` vs ``x``, one coloured line per ``group`` value; ``colors``: {group value: colour}.

    ``group`` may be a list (tuple keys). ``color_key(key)`` / ``style_key(key)`` pick the colour key and
    the linestyle + marker key (e.g. colour = signal, linestyle = cohort), so callers never restyle
    lines after the fact."""
    _grouped_lines(ax, df, x, y, group, colors=colors, color_key=color_key, style_key=style_key)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return ax


def intervention(ax, df: pd.DataFrame, colors=None, x="k", y="preserved", action="action",
                 order="order", xlabel="k", ylabel="Prediction preserved"):
    """``y`` vs ``x``, one line per (action, order): colour by action, linestyle + marker by order
    (first order solid circles, second dashed squares, ...). ``colors``: {(action, order): colour} or
    {action: colour}. Line labels are "action / order"."""
    _grouped_lines(ax, df, x, y, [action, order], colors=colors,
                   color_key=lambda key: key[0], style_key=lambda key: key[1],
                   label=lambda key: f"{key[0]} / {key[1]}")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    return ax


# ---------------------------------------------------------------- S5 ROC (mean ± SD over runs)
# Style after MenglinLu/Retinal_VascularEvents, visualization/ROC curve.py (MIT licence): square axes,
# dashed chance diagonal, each run's TPR interpolated onto a common FPR grid, mean curve with a ±SD band,
# "AUC = mean ± SD" in a lower-right legend. Changes: np.interp instead of scipy.interp, x label
# "1 − specificity" (the original's "Specificity" was a mislabel), Okabe-Ito colours.

def roc_points(y_true, y_score):
    """ROC curve (fpr, tpr) of binary labels vs scores, ties handled as one threshold step."""
    y = np.asarray(y_true)
    s = np.asarray(y_score, float)
    if y.shape != s.shape or y.ndim != 1 or not np.isfinite(s).all():
        raise ValueError("roc_points needs 1-D y_true / y_score of equal length with finite scores")
    if not np.isin(y, (0, 1)).all():
        raise ValueError("y_true must be binary (0 / 1)")
    P, N = int((y == 1).sum()), int((y == 0).sum())
    if P == 0 or N == 0:
        raise ValueError("ROC needs both classes in y_true")
    o = np.argsort(-s, kind="mergesort")
    s, y = s[o], y[o]
    last = np.r_[np.flatnonzero(np.diff(s)), len(s) - 1]  # last index of each distinct score
    tp = np.cumsum(y == 1)[last]
    fp = np.cumsum(y == 0)[last]
    return np.r_[0.0, fp / N], np.r_[0.0, tp / P]


def _check_curve(fpr, tpr):
    """Validate a precomputed ROC curve: equal-length 1-D finite arrays, fpr and tpr non-decreasing in
    [0, 1], fpr from 0 to 1, tpr ending at 1."""
    fpr, tpr = np.asarray(fpr, float), np.asarray(tpr, float)
    why = None
    if fpr.ndim != 1 or fpr.shape != tpr.shape or len(fpr) < 2:
        why = "fpr / tpr must be 1-D arrays of equal length >= 2"
    elif not (np.isfinite(fpr).all() and np.isfinite(tpr).all()):
        why = "non-finite values"
    elif fpr.min() < 0 or fpr.max() > 1 or tpr.min() < 0 or tpr.max() > 1:
        why = "values outside [0, 1]"
    elif (np.diff(fpr) < 0).any() or (np.diff(tpr) < 0).any():
        why = "fpr / tpr not monotone non-decreasing"
    elif fpr[0] != 0 or fpr[-1] != 1 or tpr[-1] != 1:
        why = "fpr must start at 0 and end at 1, tpr must end at 1"
    if why:
        raise ValueError(f"roc_mean_sd(kind='curve'): invalid ROC curve: {why}")
    return fpr, tpr


def _auc(fpr, tpr):
    return float(np.sum(np.diff(fpr) * (tpr[1:] + tpr[:-1]) / 2))


def roc_mean_sd(ax, runs, label=None, color=None, n_grid=100, kind="scores", band_alpha=0.2, legend=True,
                linestyle="-"):
    """Mean ROC over repeated runs (seeds / folds) with a ±SD band; call once per model on one axes.

    ``runs``: list of ``(y_true, y_score)`` (``kind="scores"``, default) or of ``(fpr, tpr)``
    (``kind="curve"``: validated -- monotone, in [0, 1], fpr 0 -> 1, tpr ending at 1 -- else ValueError).
    There is no auto-detection: sorted labels / scores look like a curve and would be misread.
    Each run's TPR is interpolated onto ``linspace(0, 1, n_grid)`` with ``np.interp`` (tpr[0] = 0,
    last point = 1). The legend shows "label (AUC = mean ± SD)" -- mean and sample SD (ddof = 1) of the
    per-run trapezoidal AUCs; a single run draws no band and shows "label (AUC = 0.xxx)" (say so in
    the caption). ``legend=False``: no per-axes legend (small multiples: draw ONE key with
    ``shared_key`` and the per-cell numbers with ``value_block``). ``linestyle`` styles the mean curve
    (colour + linestyle redundancy, S3). Stores ``ax._anchor_mean_auc``, ``_anchor_sd_auc`` (NaN for one run),
    ``_anchor_fpr_grid``, ``_anchor_mean_tpr``, ``_anchor_sd_tpr`` and ``_anchor_auc`` {label: (mean, sd)}.
    """
    runs = list(runs)
    if not runs:
        raise ValueError("roc_mean_sd needs at least one run")
    if kind not in ("scores", "curve"):
        raise ValueError(f"kind must be 'scores' or 'curve', got {kind!r}")
    grid = np.linspace(0, 1, int(n_grid))
    tprs, aucs = [], []
    for a, b in runs:
        fpr, tpr = _check_curve(a, b) if kind == "curve" else roc_points(a, b)
        aucs.append(_auc(fpr, tpr))
        t = np.interp(grid, fpr, tpr)
        t[0] = 0.0
        tprs.append(t)
    T = np.vstack(tprs)
    mean_tpr = T.mean(0)
    mean_tpr[-1] = 1.0
    n = len(runs)
    mean_auc = float(np.mean(aucs))
    sd_auc = float(np.std(aucs, ddof=1)) if n > 1 else float("nan")
    sd_tpr = T.std(0, ddof=1) if n > 1 else np.zeros_like(mean_tpr)

    k = getattr(ax, "_figkit_roc_count", 0)
    color = color or style.DATA_CYCLE[k % len(style.DATA_CYCLE)]
    auc_txt = f"AUC = {mean_auc:.3f}" + (f" ± {sd_auc:.3f}" if n > 1 else "")
    text = f"{label} ({auc_txt})" if label else auc_txt
    if not getattr(ax, "_figkit_roc_diag", False):
        style.aux(ax.axline((0, 0), (1, 1), color=GREY, linestyle="--", linewidth=0.6, zorder=1))
        ax._figkit_roc_diag = True
    if n > 1:  # coloured data band (not auxiliary)
        ax.fill_between(grid, np.clip(mean_tpr - sd_tpr, 0, 1), np.clip(mean_tpr + sd_tpr, 0, 1),
                        color=color, alpha=band_alpha, linewidth=0, zorder=2)
    ax.plot(grid, mean_tpr, color=color, linewidth=1.0, linestyle=linestyle, label=text, zorder=3)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("1 − specificity")
    ax.set_ylabel("Sensitivity")
    if legend:
        ax.legend(loc="lower right", frameon=False)
    ax._figkit_roc_count = k + 1
    ax._anchor_mean_auc = mean_auc
    ax._anchor_sd_auc = sd_auc
    ax._anchor_fpr_grid = grid
    ax._anchor_mean_tpr = mean_tpr
    ax._anchor_sd_tpr = sd_tpr
    if not hasattr(ax, "_anchor_auc"):
        ax._anchor_auc = {}
    ax._anchor_auc[label] = (mean_auc, sd_auc)
    return ax


# ---------------------------------------------------------------- calibration (reliability diagram)
# After MenglinLu/Retinal_VascularEvents, visualization/Calibration plot.py (MIT licence): one curve per
# model with the Brier score in the legend, perfect-calibration diagonal. Changes: own numpy binning
# instead of scikitplot, uniform or quantile bins, empty bins dropped (never drawn at 0), aux diagonal,
# palette colours instead of the pastel map, square axes.

def calibration_bins(y_true, y_prob, n_bins=10, strategy="uniform"):
    """(mean predicted, observed fraction, count) per non-empty bin + Brier score.

    ``strategy``: "uniform" (equal-width bins on [0, 1]) or "quantile" (equal-count edges)."""
    y = np.asarray(y_true)
    p = np.asarray(y_prob, float)
    if y.shape != p.shape or y.ndim != 1 or len(y) == 0:
        raise ValueError("calibration needs 1-D y_true / y_prob of equal, non-zero length")
    if not np.isin(y, (0, 1)).all():
        raise ValueError("y_true must be binary (0 / 1)")
    if not np.isfinite(p).all() or p.min() < 0 or p.max() > 1:
        raise ValueError("y_prob must be finite probabilities in [0, 1]")
    if strategy == "uniform":
        edges = np.linspace(0, 1, int(n_bins) + 1)
    elif strategy == "quantile":
        edges = np.unique(np.quantile(p, np.linspace(0, 1, int(n_bins) + 1)))
    else:
        raise ValueError(f"strategy must be 'uniform' or 'quantile', got {strategy!r}")
    idx = np.clip(np.searchsorted(edges[1:-1], p, side="right"), 0, len(edges) - 2)
    cnt = np.bincount(idx, minlength=len(edges) - 1)
    keep = cnt > 0
    mp = np.bincount(idx, weights=p, minlength=len(cnt))[keep] / cnt[keep]
    fo = np.bincount(idx, weights=y.astype(float), minlength=len(cnt))[keep] / cnt[keep]
    brier = float(np.mean((p - y) ** 2))
    return mp, fo, cnt[keep], brier


def calibration(ax, y_true, y_prob, label=None, color=None, marker="o", n_bins=10, strategy="uniform"):
    """Reliability curve for one model; call once per model on the same axes.

    Legend "label (Brier = 0.xxx)" upper left; aux grey dashed diagonal; square [0, 1] axes. Stores
    ``ax._anchor_calibration`` {label: dict(mean_pred, frac_pos, count, brier)}."""
    mp, fo, cnt, brier = calibration_bins(y_true, y_prob, n_bins, strategy)
    k = getattr(ax, "_figkit_cal_count", 0)
    color = color or style.DATA_CYCLE[k % len(style.DATA_CYCLE)]
    if not getattr(ax, "_figkit_cal_diag", False):
        style.aux(ax.axline((0, 0), (1, 1), color=GREY, linestyle="--", linewidth=0.6, zorder=1))
        ax._figkit_cal_diag = True
    text = f"{label} (Brier = {brier:.3f})" if label else f"Brier = {brier:.3f}"
    ax.plot(mp, fo, color=color, linewidth=0.9, marker=marker, ms=2.5, label=text, zorder=3)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed fraction positive")
    ax.legend(loc="upper left", frameon=False)
    ax._figkit_cal_count = k + 1
    ax.__dict__.setdefault("_anchor_calibration", {})[label] = dict(
        mean_pred=mp, frac_pos=fo, count=cnt, brier=brier)
    return ax


# ---------------------------------------------------------------- decision curve analysis
# After MenglinLu/Retinal_VascularEvents, visualization/Decision curve.py (MIT licence): net benefit
# tp/n - fp/n * t/(1 - t) per threshold with treat-all / treat-none references. Changes: vectorised
# counts (no confusion_matrix per threshold), treat all = prev - (1 - prev) t/(1 - t), treat none = aux
# zero line, no crimson fill, values below the y floor are recorded instead of silently cut.

def _check_binary(y, p, what):
    y, p = np.asarray(y), np.asarray(p, float)
    if y.shape != p.shape or y.ndim != 1 or len(y) == 0:
        raise ValueError(f"{what} needs 1-D y_true / scores of equal, non-zero length")
    if not np.isin(y, (0, 1)).all():
        raise ValueError("y_true must be binary (0 / 1)")
    if not np.isfinite(p).all():
        raise ValueError(f"{what}: scores must be finite")
    return y.astype(int), p


def net_benefit(y_true, y_prob, thresholds):
    """(net benefit of the model, net benefit of treat all) at each threshold in (0, 1)."""
    y, p = _check_binary(y_true, y_prob, "net_benefit")
    t = np.asarray(thresholds, float)
    if t.ndim != 1 or (t <= 0).any() or (t >= 1).any():
        raise ValueError("thresholds must be a 1-D array strictly inside (0, 1)")
    n, pos, neg = len(y), np.sort(p[y == 1]), np.sort(p[y == 0])
    tp = len(pos) - np.searchsorted(pos, t, side="right")  # predicted positive: p > t
    fp = len(neg) - np.searchsorted(neg, t, side="right")
    w = t / (1 - t)
    prev = len(pos) / n
    return tp / n - fp / n * w, prev - (1 - prev) * w


DCA_THRESHOLDS = np.round(np.arange(0.01, 0.991, 0.01), 2)


def decision(ax, y_true, y_prob, label=None, color=None, thresholds=DCA_THRESHOLDS, treat_all=True,
             treat_all_color=None, ylim=None, linestyle="-"):
    """Decision curve for one model; call once per model (or cohort) on the same axes.

    Draws the model's net benefit; ``treat_all=True`` adds a dashed treat-all line in
    ``treat_all_color`` (default: the model colour, i.e. cohort-specific prevalence; pass ``"aux"`` for
    one grey auxiliary line). Treat none is an aux grey zero line (drawn once). ``ylim`` (lo, hi):
    defaults to (-0.05, max + 0.05); the first threshold where either curve drops below lo is recorded
    in ``ax._anchor_dca[label]["clipped_from"]`` so the caption can state the truncation."""
    nb, nb_all = net_benefit(y_true, y_prob, thresholds)
    t = np.asarray(thresholds, float)
    k = getattr(ax, "_figkit_dca_count", 0)
    color = color or style.DATA_CYCLE[k % len(style.DATA_CYCLE)]
    if not getattr(ax, "_figkit_dca_none", False):
        style.aux(ax.axhline(0, color=GREY, linewidth=0.6, zorder=1))
        ax._figkit_dca_none = True
    ax.plot(t, nb, color=color, linewidth=0.9, linestyle=linestyle, label=label, zorder=3)
    if treat_all:
        aux_all = treat_all_color == "aux"
        ln = ax.plot(t, nb_all, color=GREY if aux_all else (treat_all_color or color), linewidth=0.7,
                     linestyle="--", zorder=2)[0]
        if aux_all:
            style.aux(ln)
    store = ax.__dict__.setdefault("_anchor_dca", {})
    hi = max([float(np.max(nb))] + [v["max"] for v in store.values()])
    lo, top = ylim if ylim is not None else (-0.05, hi + 0.05)
    below = (nb < lo) | ((nb_all < lo) if treat_all else False)
    store[label] = dict(thresholds=t, net_benefit=nb, treat_all=nb_all, max=float(np.max(nb)),
                        clipped_from=float(t[below][0]) if below.any() else None)
    ax.set_xlim(0, 1)
    ax.set_ylim(lo, top)
    ax.set_xlabel("Threshold probability")
    ax.set_ylabel("Net benefit")
    if label:
        ax.legend(loc="upper right", frameon=False)
    ax._figkit_dca_count = k + 1
    return ax


# ---------------------------------------------------------------- precision-recall (mean ± SD over runs)
def pr_points(y_true, y_score):
    """(recall, precision, AP) of binary labels vs scores; ties are one threshold step. AP is the
    step-wise sum over recall increments (same definition as sklearn average_precision_score)."""
    y, s = _check_binary(y_true, y_score, "pr_points")
    P = int(y.sum())
    if P == 0 or P == len(y):
        raise ValueError("PR needs both classes in y_true")
    o = np.argsort(-s, kind="mergesort")
    s, y = s[o], y[o]
    last = np.r_[np.flatnonzero(np.diff(s)), len(s) - 1]
    tp = np.cumsum(y == 1)[last].astype(float)
    fp = np.cumsum(y == 0)[last].astype(float)
    prec, rec = tp / (tp + fp), tp / P
    ap = float(np.sum(np.diff(np.r_[0.0, rec]) * prec))
    return np.r_[0.0, rec], np.r_[1.0, prec], ap


def pr_mean_sd(ax, runs, label=None, color=None, n_grid=100, band_alpha=0.2, prevalence=True, legend=True,
               linestyle="-"):
    """Mean precision-recall curve over repeated runs with a ±SD band; call once per model.

    ``runs``: list of ``(y_true, y_score)``. Each run's interpolated precision
    (max precision at recall >= r, the monotone envelope) is evaluated on ``linspace(0, 1, n_grid)``.
    Legend "label (AP = mean ± SD)" (sample SD, ddof = 1; one run -> no band, AP only), lower left.
    ``prevalence=True`` draws the mean positive rate as an aux dotted line in the curve colour's place
    (grey). Stores ``ax._anchor_pr`` {label: dict(mean_ap, sd_ap, recall_grid, mean_prec, sd_prec, prevalence)}."""
    runs = list(runs)
    if not runs:
        raise ValueError("pr_mean_sd needs at least one run")
    grid = np.linspace(0, 1, int(n_grid))
    precs, aps, prevs = [], [], []
    for y, s in runs:
        rec, prec, ap = pr_points(y, s)
        env = np.maximum.accumulate(prec[::-1])[::-1]  # interpolated precision
        idx = np.clip(np.searchsorted(rec, grid, side="left"), 0, len(rec) - 1)
        precs.append(env[idx])
        aps.append(ap)
        prevs.append(float(np.mean(np.asarray(y) == 1)))
    Pm = np.vstack(precs)
    n = len(runs)
    mean_p = Pm.mean(0)
    sd_p = Pm.std(0, ddof=1) if n > 1 else np.zeros_like(mean_p)
    mean_ap = float(np.mean(aps))
    sd_ap = float(np.std(aps, ddof=1)) if n > 1 else float("nan")
    k = getattr(ax, "_figkit_pr_count", 0)
    color = color or style.DATA_CYCLE[k % len(style.DATA_CYCLE)]
    txt = f"AP = {mean_ap:.3f}" + (f" ± {sd_ap:.3f}" if n > 1 else "")
    if n > 1:
        ax.fill_between(grid, np.clip(mean_p - sd_p, 0, 1), np.clip(mean_p + sd_p, 0, 1),
                        color=color, alpha=band_alpha, linewidth=0, zorder=2)
    ax.plot(grid, mean_p, color=color, linewidth=1.0, linestyle=linestyle,
            label=f"{label} ({txt})" if label else txt, zorder=3)
    prev = float(np.mean(prevs))
    if prevalence:
        style.aux(ax.axhline(prev, color=GREY, linestyle=":", linewidth=0.6, zorder=1))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    if legend:
        ax.legend(loc="lower left", frameon=False)
    ax._figkit_pr_count = k + 1
    ax.__dict__.setdefault("_anchor_pr", {})[label] = dict(
        mean_ap=mean_ap, sd_ap=sd_ap, recall_grid=grid, mean_prec=mean_p, sd_prec=sd_p, prevalence=prev)
    return ax


# ---------------------------------------------------------------- selective prediction (risk-coverage)
def risk_coverage_points(y_correct, confidence):
    """(coverage, risk, AURC): keep the most confident scans first; risk = error rate on the retained
    set. Ties in confidence are one step. AURC = trapezoid area under risk vs coverage."""
    c, conf = _check_binary(y_correct, confidence, "risk_coverage")
    o = np.argsort(-conf, kind="mergesort")
    conf, err = conf[o], 1 - c[o]
    last = np.r_[np.flatnonzero(np.diff(conf)), len(conf) - 1]
    kept = (last + 1).astype(float)
    cov = kept / len(c)
    risk = np.cumsum(err)[last] / kept
    aurc = float(np.sum(np.diff(np.r_[0.0, cov]) * risk))
    return cov, risk, aurc


def risk_coverage(ax, y_correct, confidence, label=None, color=None, linestyle="-"):
    """Risk-coverage curve for one model; call once per model. Legend "label (AURC = 0.xxx)" upper
    left; the full-coverage risk is an aux dotted reference. Stores ``ax._anchor_rc`` {label: dict}."""
    cov, risk, aurc = risk_coverage_points(y_correct, confidence)
    k = getattr(ax, "_figkit_rc_count", 0)
    color = color or style.DATA_CYCLE[k % len(style.DATA_CYCLE)]
    txt = f"AURC = {aurc:.3f}"
    ax.plot(cov, risk, color=color, linewidth=0.9, linestyle=linestyle,
            label=f"{label} ({txt})" if label else txt, zorder=3)
    ax.set_xlim(0, 1)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Coverage (retained fraction)")
    ax.set_ylabel("Error rate on retained")
    ax.legend(loc="upper left", frameon=False)
    ax._figkit_rc_count = k + 1
    ax.__dict__.setdefault("_anchor_rc", {})[label] = dict(
        coverage=cov, risk=risk, aurc=aurc, full_risk=float(risk[-1]))
    return ax


# ---------------------------------------------------------------- ROC inset inside a host panel
INSET_BOUNDS = (0.60, 0.13, 0.36, 0.34)


def roc_inset(ax, curves_, bounds=INSET_BOUNDS, tick_pt=None):
    """Small square ROC as a CHILD axes of ``ax`` (exported with the host panel, exempt from the S1
    whitespace audit). ``curves_``: list of dict(fpr, tpr, color[, linestyle, label]) -- one single-run
    curve each, no ±SD band (say so in the caption). Aux dashed diagonal; ticks at
    ``style.INSET_TICK_PT``. Returns the inset axes; stores ``inset._anchor_auc`` {label: auc}."""
    if not curves_:
        raise ValueError("roc_inset needs at least one curve")
    ins = ax.inset_axes(list(bounds))
    tick_pt = tick_pt or style.INSET_TICK_PT
    style.aux(ins.axline((0, 0), (1, 1), color=GREY, linestyle="--", linewidth=0.5, zorder=1))
    aucs = {}
    for i, c in enumerate(curves_):
        fpr, tpr = _check_curve(c["fpr"], c["tpr"])
        col = c.get("color") or style.DATA_CYCLE[i % len(style.DATA_CYCLE)]
        ins.plot(fpr, tpr, color=col, linestyle=c.get("linestyle", "-"), linewidth=0.7, zorder=3)
        aucs[c.get("label", str(i))] = _auc(fpr, tpr)
    ins.set_xlim(0, 1)
    ins.set_ylim(0, 1)
    ins.set_aspect("equal", adjustable="box")
    ins.set_xticks([0, 1])
    ins.set_yticks([0, 1])
    ins.tick_params(labelsize=tick_pt, length=1.5, pad=1)
    ins.set_xlabel("1 − specificity", fontsize=tick_pt + 1, labelpad=0)
    ins.set_ylabel("Sensitivity", fontsize=tick_pt + 1, labelpad=0)
    ins._anchor_auc = aucs
    return ins


# ---------------------------------------------------------------- small multiples: one key, per-cell values
def shared_key(fig, axes, entries, ncol=None, pad_in=0.05, **kw):
    """ONE legend for a small-multiple panel whose cells share the same entries (never one per cell).

    ``entries``: list of dicts with ``label`` and ``color`` (+ optional ``linestyle``, ``marker``). The key
    is one row centred over the union of ``axes``, ``pad_in`` inches above the highest cell title. It is
    attached to the first cell, so it is exported with the panel; its handles are keys, not data.
    Returns the Legend (also ``axes[0]._figkit_shared_key``)."""
    from matplotlib.lines import Line2D
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    boxes = [a.get_position() for a in axes]
    x0, x1 = min(b.x0 for b in boxes), max(b.x1 for b in boxes)
    tops = [(a.title.get_window_extent(r).y1 if a.title.get_text() else a.bbox.y1) / fig.bbox.height
            for a in axes]
    top = max(tops + [b.y1 for b in boxes]) + pad_in / fig.get_figheight()
    handles = [Line2D([], [], color=e["color"], linestyle=e.get("linestyle", "-"), marker=e.get("marker"),
                      linewidth=1.0, markersize=3, label=e["label"]) for e in entries]
    a0 = axes[0]
    ax_x, ax_y = a0.transAxes.inverted().transform(fig.transFigure.transform(((x0 + x1) / 2, top)))
    lg = a0.legend(handles=handles, loc="lower center", bbox_to_anchor=(ax_x, ax_y), ncol=ncol or len(entries),
                   frameon=False, handlelength=2.0, columnspacing=1.4, borderaxespad=0, **kw)
    a0._figkit_shared_key = lg
    return lg


def value_block(ax, values, colors, loc="lower right", fmt="{:.3f}", prefix="", pad_pt=3.0, line_pt=7.5,
                fontsize=6):
    """Per-cell numbers (e.g. AUC per model) as a coloured text block in one corner: one line per value in
    the matching data colour, no line handles (the panel's ``shared_key`` explains the colours). ``values``
    may be floats or (mean, sd) pairs (rendered "mean ± sd"; sd None / NaN -> mean only). Offsets are in
    points (``pad_pt`` from the corner, ``line_pt`` per line), so the block keeps its spacing at any cell
    size. Returns the Text artists in ``values`` order."""
    import matplotlib.transforms as mtransforms
    if len(values) != len(colors):
        raise ValueError("value_block needs one colour per value")
    rows = []
    for v in values:
        if isinstance(v, (tuple, list)):
            m, sd = v
            ok = sd is not None and np.isfinite(sd)
            rows.append(prefix + fmt.format(m) + (" ± " + fmt.format(sd) if ok else ""))
        else:
            rows.append(prefix + fmt.format(v))
    right, lower = loc.endswith("right"), loc.startswith("lower")
    out = []
    for i, (txt, c) in enumerate(zip(rows, colors)):
        k = len(rows) - 1 - i if lower else i
        dx = -pad_pt if right else pad_pt
        dy = (pad_pt + k * line_pt) if lower else -(pad_pt + k * line_pt)
        tr = ax.transAxes + mtransforms.ScaledTranslation(dx / 72, dy / 72, ax.figure.dpi_scale_trans)
        out.append(ax.text(1 if right else 0, 0 if lower else 1, txt, transform=tr,
                           ha="right" if right else "left", va="bottom" if lower else "top", color=c,
                           fontsize=fontsize, zorder=5))
    ax._figkit_value_block = out
    return out
