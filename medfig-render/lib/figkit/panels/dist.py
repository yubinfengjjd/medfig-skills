"""Distribution panels: violin + strip, box + jittered points, ECDF, HDR contours (S3: coloured data)."""
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import gaussian_kde

from .. import style


def violin_strip(ax, df: pd.DataFrame, x, y, hue, order, hue_order, log=False, palette=None,
                 violin_alpha=0.35, point_alpha=0.5):
    """Violins per (x, hue) (``cut=0``, width-normalised) with a light rasterised strip of raw points.

    Colours: ``palette`` (list, or dict keyed by hue / x level) defaults to ``style.DATA_CYCLE``;
    violins are filled at ``violin_alpha`` and the points use the same colours, so every data artist
    is coloured (S3). Only the collections created here are touched.
    """
    kw = dict(data=df, x=x, y=y, order=order, ax=ax)
    levels = hue_order if hue is not None else order
    if hue is not None:
        kw.update(hue=hue, hue_order=hue_order)
    else:  # colour by x level
        kw.update(hue=x, hue_order=order)
    pal = palette if palette is not None else style.DATA_CYCLE[:len(levels)]
    n0 = len(ax.collections)
    sns.violinplot(**kw, palette=pal, inner=None, cut=0, linewidth=0.5, density_norm="width",
                   log_scale=log if log else None, legend=False, saturation=1,
                   dodge=hue is not None)
    for c in ax.collections[n0:]:
        c.set_alpha(violin_alpha)
    n1 = len(ax.collections)
    sns.stripplot(**kw, palette=pal, dodge=hue is not None, size=np.sqrt(1.5), alpha=point_alpha,
                  jitter=0.25, legend=False)
    for c in ax.collections[n1:]:
        c.set_rasterized(True)
    ax.set_xlabel("")
    return ax


def box_swarm(ax, df: pd.DataFrame, x, y, order, color=None, point_color=None,
              point_df=None, hue=None, hue_styles=None, seed=0):
    """Box (no fliers) + deterministic jittered points (``seed``), points rasterised.

    ``color`` (boxes) defaults to Okabe-Ito blue; ``point_color`` defaults to the box colour.
    ``point_df`` draws the points from a different frame (e.g. a subsample) while the boxes summarise
    ``df``; ``hue`` + ``hue_styles`` ({level: dict(color=..., marker=...)}) draw the points per hue
    level with their own colour / marker (levels in dict order)."""
    color = color or style.DATA_CYCLE[0]
    point_color = point_color or color
    data = [df.loc[df[x] == k, y].dropna().to_numpy(float) for k in order]
    pts = df if point_df is None else point_df
    pos = np.arange(len(order), dtype=float)
    ax.boxplot(data, positions=pos, widths=0.55, showfliers=False, patch_artist=True,
               boxprops=dict(facecolor="none", edgecolor=color, linewidth=0.7),
               medianprops=dict(color=color, linewidth=0.9),
               whiskerprops=dict(color=color, linewidth=0.7), capprops=dict(color=color, linewidth=0.7))
    rng = np.random.default_rng(seed)
    groups = [(None, dict(color=point_color, marker="o"))] if hue is None else list(hue_styles.items())
    for p, k in zip(pos, order):
        sub = pts.loc[pts[x] == k]
        for lev, st in groups:
            d = (sub if lev is None else sub.loc[sub[hue] == lev])[y].dropna().to_numpy(float)
            sc = ax.scatter(p + rng.uniform(-0.18, 0.18, len(d)), d, s=3, color=st["color"],
                            marker=st.get("marker", "o"), alpha=0.5, linewidths=0, zorder=3)
            sc.set_rasterized(True)
    ax.set_xticks(pos, list(order))
    ax.set_xlim(-0.6, len(order) - 0.4)
    ax._anchor_medians = [float(np.median(d)) if len(d) else np.nan for d in data]
    return ax


def ecdf(ax, values, **kw):
    """Empirical CDF as a post-step line (colour from the axes cycle unless ``color=`` is given)."""
    v = np.asarray(values, float)
    v = np.sort(v[np.isfinite(v)])
    if not len(v):
        raise ValueError("ecdf needs at least one finite value")
    p = np.arange(1, len(v) + 1) / len(v)
    kw.setdefault("linewidth", 0.9)
    ax.step(v, p, where="post", **kw)
    ax.set_ylim(0, 1.02)
    ax._anchor_ecdf = (v, p)
    return ax


def hdr_contour(ax, xy, color=None, levels=(0.5, 0.9), grid=120, pad_sd=3.0, linewidth=0.8):
    """Highest-density-region contours of a gaussian KDE (Scott bandwidth); 50% solid, 90% dashed.

    ``levels`` are probability masses (``levels=(0.5,)`` draws the 50% HDR only; use that for small
    samples and say "indicative" in the caption). The density threshold for mass m is the standard
    sample estimator ``quantile(kde(xy), 1 - m)`` -- taken from the sample densities, never the grid.
    The evaluation grid spans the data range padded by ``pad_sd`` (>= 3) kernel SDs
    (sqrt(diag(kde.covariance))) per axis, so contours close inside the grid.
    ``ax._anchor_levels`` holds the thresholds (higher mass -> lower threshold); ``ax._anchor_grid``
    holds (gx, gy)."""
    if pad_sd < 3:
        raise ValueError(f"pad_sd must be >= 3 kernel SDs so HDR contours close (got {pad_sd})")
    color = color or style.DATA_CYCLE[0]
    xy = np.asarray(xy, float)
    if xy.ndim != 2 or xy.shape[1] != 2 or not np.isfinite(xy).all():
        raise ValueError("hdr_contour needs a finite (n, 2) array")
    kde = gaussian_kde(xy.T)
    sd = np.sqrt(np.diag(kde.covariance))
    lo, hi = xy.min(0) - pad_sd * sd, xy.max(0) + pad_sd * sd
    gx = np.linspace(lo[0], hi[0], grid)
    gy = np.linspace(lo[1], hi[1], grid)
    X, Y = np.meshgrid(gx, gy)
    Z = kde(np.vstack([X.ravel(), Y.ravel()])).reshape(X.shape)
    dens = kde(xy.T)
    thr = [float(np.quantile(dens, 1 - m)) for m in levels]
    styles = ["-", "--", ":", "-."]
    # contour needs increasing levels -> draw each separately to keep the style mapping explicit
    for t, ls in zip(thr, styles):
        ax.contour(X, Y, Z, levels=[t], colors=[color], linestyles=[ls], linewidths=linewidth)
    ax._anchor_levels = thr
    ax._anchor_grid = (gx, gy)
    return ax
