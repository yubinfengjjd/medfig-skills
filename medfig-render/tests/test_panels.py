"""figkit.panels behaviour + S1-S3/S5 checks. Synthetic data only."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from figkit import qa, style
from figkit.panels import confusion, curves, dist, heat, imaging, intervals

CLASSES = ["Alpha", "Beta", "Gamma"]


def _clean(fig):
    """The three S1-S3 panel audits must all be clean."""
    assert qa.colour_audit(fig) == []
    assert qa.text_only_panel(fig) == []
    assert qa.whitespace_audit(fig) == []


def _cc3(seed=1):
    rng = np.random.default_rng(seed)
    return pd.DataFrame([(t, p, int(rng.integers(1, 9000))) for t in CLASSES for p in CLASSES],
                        columns=["truth", "prediction", "count"])


# ---------------------------------------------------------------- confusion
def test_confusion_rows_sum_to_one():
    df = pd.DataFrame({"truth": ["A", "A", "B", "B"], "prediction": ["A", "B", "A", "B"], "count": [8, 2, 1, 9]})
    fig, ax = plt.subplots()
    M = confusion.matrix(ax, df, ["A", "B"])._anchor_matrix
    assert np.allclose(M.sum(1), 1.0)


def test_confusion_absent_row_is_nan():
    df = pd.DataFrame({"truth": ["A", "A"], "prediction": ["A", "B"], "count": [3, 1]})
    fig, ax = plt.subplots()
    M = confusion.matrix(ax, df, ["A", "B"], absent_rows=("B",))._anchor_matrix
    assert np.isnan(M[1]).all()


def test_confusion_absent_rows_unknown_class_raises():
    df = pd.DataFrame({"truth": ["A"], "prediction": ["A"], "count": [3]})
    fig, ax = plt.subplots()
    with pytest.raises(ValueError, match="absent_rows"):
        confusion.matrix(ax, df, ["A", "B"], absent_rows=("Z",))


def test_confusion_zero_count_row_is_absent():
    df = pd.DataFrame({"truth": ["A", "A", "B"], "prediction": ["A", "B", "A"], "count": [3, 1, 0]})
    fig, ax = plt.subplots()
    confusion.matrix(ax, df, ["A", "B", "C"])
    assert ax._anchor_absent == ["B", "C"]
    assert [t.get_text() for t in ax.texts].count("absent") == 2
    assert len(ax.patches) == 2 and all(p.get_hatch() == "////" for p in ax.patches)
    assert np.isnan(ax._anchor_matrix[1:]).all()


def test_confusion_fits_cells_at_final_size():
    fig, ax = plt.subplots(figsize=(style.SINGLE / 2, style.SINGLE / 2), layout="constrained")
    confusion.matrix(ax, _cc3(), CLASSES, absent_rows=("Gamma",), tick_labels=["A", "B", "G"])
    assert qa.geometry_audit(fig) == []
    assert ax._anchor_mappable is not None and not hasattr(ax, "_anchor_colorbar")


def test_confusion_default_labels_clean_at_min_size():
    fig, ax = plt.subplots(figsize=(2.0, 2.0), layout="constrained")
    confusion.matrix(ax, _cc3(), CLASSES)
    assert [t.get_text() for t in ax.get_xticklabels()] == CLASSES
    assert qa.geometry_audit(fig) == []


def test_confusion_tick_labels():
    fig, ax = plt.subplots()
    confusion.matrix(ax, _cc3(), CLASSES, tick_labels=["A", "B", "G"])
    assert [t.get_text() for t in ax.get_yticklabels()] == ["A", "B", "G"]
    with pytest.raises(ValueError, match="tick_labels"):
        confusion.matrix(ax, _cc3(), CLASSES, tick_labels=["A", "B"])


def test_confusion_count_fmt():
    df = pd.DataFrame({"truth": ["A", "A", "B"], "prediction": ["A", "B", "B"], "count": [12345, 4, 1200]})
    fig, ax = plt.subplots()
    confusion.matrix(ax, df, ["A", "B"])
    texts = [t.get_text() for t in ax.texts]
    assert "100.0%\n(12345)" in texts and "99.98%\n(12345)" not in texts
    fig, ax = plt.subplots()
    confusion.matrix(ax, df, ["A", "B"], count_fmt="{:,}")
    texts = [t.get_text() for t in ax.texts]
    assert "100.0%\n(12,345)" in texts and "100.0%\n(1,200)" in texts


def test_confusion_shared_colourbar():
    fig, (a, b, cax) = plt.subplots(1, 3, figsize=(4, 1.8), gridspec_kw={"width_ratios": [1, 1, 0.06]})
    confusion.matrix(a, _cc3(1), CLASSES, tick_labels=["A", "B", "G"])
    confusion.matrix(b, _cc3(2), CLASSES, tick_labels=["A", "B", "G"])
    cb = confusion.colourbar(a, cax)
    assert cb.ax is cax and list(cb.get_ticks()) == [0, 0.5, 1.0]
    assert cb.ax.yaxis.label.get_fontsize() >= style.MIN_FONT_PT
    fig, ax = plt.subplots()
    confusion.matrix(ax, _cc3(), CLASSES, cbar=True)
    assert ax._anchor_colorbar.mappable is ax._anchor_mappable


def test_confusion_colour_audit_clean():
    fig, ax = plt.subplots(figsize=(2.0, 2.0), layout="constrained")
    confusion.matrix(ax, _cc3(), CLASSES, absent_rows=("Gamma",))
    _clean(fig)


# ---------------------------------------------------------------- intervals
def _forest_rows():
    return pd.DataFrame({"label": ["r0", "r1", "r2"], "est": [.5, .6, .7], "lo": [.4, .5, .6],
                         "hi": [.6, .7, .8]})


def test_forest_row_order_top_to_bottom_and_band():
    fig, ax = plt.subplots()
    intervals.forest(ax, _forest_rows(), ref=0.5, band_rows=[1])
    assert ax._anchor_y["r0"] > ax._anchor_y["r1"] > ax._anchor_y["r2"]
    ticks = {t.get_text(): loc for t, loc in zip(ax.get_yticklabels(), ax.get_yticks())}
    assert ticks["r0"] > ticks["r1"] > ticks["r2"]
    assert len(ax.patches) == 1 and ax.patches[0]._figkit_aux


def test_forest_empty_band_rows_list():
    fig, ax = plt.subplots()
    intervals.forest(ax, _forest_rows().iloc[:1], ref=None, band_rows=[])
    assert len(ax.patches) == 0


def test_forest_per_row_style_columns():
    rows = _forest_rows().assign(color=["#0072B2", "#D55E00", "#009E73"], marker=["o", "s", "D"])
    fig, ax = plt.subplots()
    intervals.forest(ax, rows, ref=0.5)
    marks = [ln.get_marker() for ln in ax.get_lines() if ln.get_marker() not in ("None", "")]
    assert marks == ["o", "s", "D"]


def test_forest_colour_audit_clean():
    fig, ax = plt.subplots(figsize=(2.4, 1.6), layout="constrained")
    intervals.forest(ax, _forest_rows(), ref=0.5, band_rows=[1])
    ax.set_xlabel("Estimate (95% CI)")
    _clean(fig)


def test_dumbbell_delta_and_colour_audit_clean():
    rows = pd.DataFrame({"label": ["x", "y", "z"], "a": [.2, .4, .5], "b": [.3, .35, .9]})
    fig, ax = plt.subplots(figsize=(2.4, 1.6), layout="constrained")
    intervals.dumbbell(ax, rows, a_kw=dict(label="before"), b_kw=dict(label="after"))
    assert np.allclose(ax._anchor_delta, [.1, -.05, .4])
    _clean(fig)


def test_estimation_panels():
    paired = pd.DataFrame({"seed": [0, 1, 2], "a": [.9, .91, .92], "b": [.95, .94, .96]})
    deltas = pd.DataFrame({"label": ["d"], "est": [.04], "lo": [.02], "hi": [.06]})
    fig, (l, r) = plt.subplots(1, 2)
    intervals.estimation(l, r, paired, deltas)
    assert len(l.get_lines()) == 3 and np.allclose(l._anchor_paired_delta, [.05, .03, .04])


def test_estimation_optional_columns_and_extra_axes():
    paired = pd.DataFrame({"a": [.6, .9], "b": [.95, .96], "xa": [0, 2], "xb": [0.8, 2.8],
                           "a_kw": [dict(mfc="none"), dict(fillstyle="left")]})
    deltas = pd.DataFrame({"label": ["x", "y"], "est": [.3, .01], "lo": [.28, .0], "hi": [.32, .02],
                           "x": [0.0, 1.5], "kw": [dict(mfc="none"), None]})
    fig, (l, r, r2) = plt.subplots(1, 3)
    intervals.estimation(l, r, paired, deltas, extra_right=[r2], ticks=False)
    assert np.allclose(l._anchor_paired_delta, [.35, .06])
    assert l.get_lines()[1].get_mfc() == "none" and l.get_lines()[4].get_fillstyle() == "left"
    assert np.allclose(r._anchor_delta_x, [0, 1.5])
    assert len(r2.lines) == len(r.lines) > 0


def test_estimation_colour_audit_clean():
    rng = np.random.default_rng(3)
    a = rng.normal(0.8, 0.02, 6)
    paired = pd.DataFrame({"a": a, "b": a + rng.normal(0.03, 0.01, 6)})
    deltas = pd.DataFrame({"label": ["B − A"], "est": [.03], "lo": [.02], "hi": [.04]})
    fig, (l, r) = plt.subplots(1, 2, figsize=(3.0, 1.6), layout="constrained")
    intervals.estimation(l, r, paired, deltas)
    assert all(ln.get_color() != GREY_HEX for ln in l.get_lines())
    _clean(fig)


GREY_HEX = style.GREY


# ---------------------------------------------------------------- dist
def _dist_df(n=200, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame({"g": np.repeat(["a", "b"], n), "h": np.tile(["u", "v"], n),
                         "v": rng.lognormal(size=2 * n)})


def test_hdr_levels_monotone():
    xy = np.random.default_rng(0).normal(size=(500, 2))
    fig, ax = plt.subplots()
    lv = dist.hdr_contour(ax, xy)._anchor_levels
    assert lv[0] > lv[1] > 0  # 50% HDR threshold density above the 90% one


def test_hdr_contours_closed_and_inside_grid():
    xy = np.random.default_rng(0).normal(size=(2000, 2))
    fig, ax = plt.subplots()
    dist.hdr_contour(ax, xy)
    gx, gy = ax._anchor_grid
    sd = np.sqrt(np.diag(__import__("scipy.stats", fromlist=["gaussian_kde"]).gaussian_kde(xy.T).covariance))
    assert gx[0] <= xy[:, 0].min() - 3 * sd[0] + 1e-9 and gy[-1] >= xy[:, 1].max() + 3 * sd[1] - 1e-9
    segs = [p for c in ax.collections for p in c.get_paths()]
    assert len(segs) >= 2
    for path in segs:
        for poly in path.to_polygons(closed_only=False):
            assert np.allclose(poly[0], poly[-1], atol=1e-9), "open contour path"
            assert (poly[:, 0] > gx[0]).all() and (poly[:, 0] < gx[-1]).all()
            assert (poly[:, 1] > gy[0]).all() and (poly[:, 1] < gy[-1]).all()


def test_hdr_threshold_is_sample_density_quantile():
    from scipy.stats import gaussian_kde
    xy = np.random.default_rng(1).normal(size=(800, 2))
    fig, ax = plt.subplots()
    lv = dist.hdr_contour(ax, xy, "#0072B2", levels=(0.5, 0.9))._anchor_levels
    d = gaussian_kde(xy.T)(xy.T)
    assert np.allclose(lv, [np.quantile(d, 0.5), np.quantile(d, 0.1)])
    assert len(dist.hdr_contour(ax, xy, levels=(0.5,))._anchor_levels) == 1


def test_hdr_rejects_small_padding():
    with pytest.raises(ValueError, match="pad_sd"):
        dist.hdr_contour(plt.subplots()[1], np.zeros((10, 2)) + np.arange(10)[:, None], pad_sd=1)


def test_hdr_colour_audit_clean():
    rng = np.random.default_rng(2)
    fig, ax = plt.subplots(figsize=(2.2, 2.0), layout="constrained")
    dist.hdr_contour(ax, rng.normal(size=(400, 2)))
    dist.hdr_contour(ax, rng.normal(1.5, 1, size=(400, 2)), style.DATA_CYCLE[1])
    _clean(fig)


def test_violin_strip_log_and_existing_collections():
    fig, ax = plt.subplots()
    pre = ax.scatter([0], [1], alpha=1.0)
    df = _dist_df()
    dist.violin_strip(ax, df, "g", "v", "h", ["a", "b"], ["u", "v"], log=True)
    assert ax.get_yscale() == "log" and pre.get_alpha() == 1.0


def test_violin_strip_colour_audit_clean():
    for hue, ho in (("h", ["u", "v"]), (None, None)):
        fig, ax = plt.subplots(figsize=(2.2, 1.8), layout="constrained")
        dist.violin_strip(ax, _dist_df(), "g", "v", hue, ["a", "b"], ho)
        _clean(fig)


def test_box_swarm_rasterised_medians_and_colour_audit_clean():
    df = _dist_df()
    fig, ax = plt.subplots(figsize=(2.2, 1.8), layout="constrained")
    dist.box_swarm(ax, df, "g", "v", ["a", "b"])
    assert all(c.get_rasterized() for c in ax.collections)
    assert np.allclose(ax._anchor_medians, [np.median(df.v[df.g == k]) for k in "ab"])
    _clean(fig)
    fig, ax = plt.subplots(figsize=(2.2, 1.8), layout="constrained")
    dist.box_swarm(ax, df, "g", "v", ["a", "b"], hue="h",
                   hue_styles={"u": dict(color="#D55E00"), "v": dict(color="#009E73", marker="^")})
    _clean(fig)


def test_ecdf_and_colour_audit_clean():
    fig, ax = plt.subplots(figsize=(2.2, 1.8), layout="constrained")
    dist.ecdf(ax, np.r_[np.random.default_rng(0).normal(size=100), np.nan])
    v, p = ax._anchor_ecdf
    assert p[-1] == 1.0 and len(v) == 100
    _clean(fig)
    with pytest.raises(ValueError):
        dist.ecdf(ax, [np.nan])


# ---------------------------------------------------------------- curves
def _ladder():
    return pd.DataFrame({"dataset": ["d1"] * 3 + ["d2"] * 3, "stage": ["s0", "s1", "s2"] * 2,
                         "value": [.8, .85, .9, .7, .78, .8], "probe": [False, False, True] * 2})


def test_step_ladder_probe_hollow_and_colour_audit_clean():
    fig, ax = plt.subplots(figsize=(2.2, 1.8), layout="constrained")
    curves.step_ladder(ax, _ladder(), ["s0", "s1", "s2"])
    assert ax.get_lines()[2].get_markerfacecolor() == "white"
    assert ax.get_lines()[0].get_color() == style.DATA_CYCLE[0]
    _clean(fig)


def test_step_ladder_uses_config_palette(project):
    fig, ax = plt.subplots()
    lad = _ladder().replace({"d1": "site_a", "d2": "site_b"})
    curves.step_ladder(ax, lad, ["s0", "s1", "s2"])
    assert ax.get_lines()[0].get_label() == "Site A"
    assert ax.get_lines()[3].get_color() == "#F0E442" and ax.get_lines()[4].get_mec() == "#8C7A00"


def _iv():
    return pd.DataFrame({"k": [1, 2, 1, 2], "preserved": [.9, .8, .95, .9],
                         "order": ["top", "top", "random", "random"], "action": ["del"] * 4})


def test_capture_colors_kwarg_and_colour_audit_clean():
    cap = pd.DataFrame({"budget": [.1, .2, .1, .2], "capture": [.3, .5, .2, .4],
                        "signal": ["s1", "s1", "s2", "s2"]})
    fig, ax = plt.subplots(figsize=(2.2, 1.8), layout="constrained")
    curves.capture(ax, cap, colors={"s2": "#CC79A7"})
    assert ax.get_lines()[1].get_color() == "#CC79A7"
    assert ax.get_lines()[0].get_color() == style.DATA_CYCLE[0]
    _clean(fig)


def test_intervention_order_by_linestyle_marker_not_grey():
    fig, ax = plt.subplots(figsize=(2.2, 1.8), layout="constrained")
    curves.intervention(ax, _iv())
    lines = ax.get_lines()
    assert [l.get_linestyle() for l in lines] == ["-", "--"]
    assert [l.get_marker() for l in lines] == ["o", "s"]
    assert [l.get_label() for l in lines] == ["del / top", "del / random"]
    assert len({l.get_color() for l in lines}) == 1  # colour = action, style = order
    _clean(fig)


def test_intervention_colors_kwarg():
    fig, ax = plt.subplots()
    curves.intervention(ax, _iv(), colors={"del": "#D55E00"})
    assert {l.get_color() for l in ax.get_lines()} == {"#D55E00"}
    fig, ax = plt.subplots()
    curves.intervention(ax, _iv().assign(action="a / b"), colors={("a / b", "top"): "#009E73"})
    assert [l.get_linestyle() for l in ax.get_lines()] == ["-", "--"]
    assert ax.get_lines()[0].get_color() == "#009E73"


def _runs(n_runs, seed=0, n=300, shift=1.0):
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_runs):
        y = rng.integers(0, 2, n)
        out.append((y, y * shift + rng.normal(size=n)))
    return out


def test_roc_points_match_rank_auc():
    y, s = _runs(1)[0]
    fpr, tpr = curves.roc_points(y, s)
    pos, neg = s[y == 1], s[y == 0]
    rank_auc = ((pos[:, None] > neg[None]).mean() + 0.5 * (pos[:, None] == neg[None]).mean())
    assert np.isclose(curves._auc(fpr, tpr), rank_auc)
    assert fpr[0] == tpr[0] == 0 and fpr[-1] == tpr[-1] == 1


def test_roc_mean_sd_multi_run():
    runs = _runs(5)
    fig, ax = plt.subplots(figsize=(2.4, 2.4), layout="constrained")
    curves.roc_mean_sd(ax, runs, "Model", n_grid=50)
    aucs = [curves._auc(*curves.roc_points(y, s)) for y, s in runs]
    assert np.isclose(ax._anchor_mean_auc, np.mean(aucs))
    assert np.isclose(ax._anchor_sd_auc, np.std(aucs, ddof=1))
    assert len(ax._anchor_fpr_grid) == 50 and ax._anchor_mean_tpr[0] == 0
    assert ax._anchor_mean_tpr[-1] == 1
    txt = ax.get_legend().get_texts()[0].get_text()
    assert txt == f"Model (AUC = {np.mean(aucs):.3f} ± {np.std(aucs, ddof=1):.3f})"
    assert ax.get_legend()._loc == 4  # "lower right"
    assert ax.get_xlabel() == "1 − specificity" and ax.get_ylabel() == "Sensitivity"
    assert ax.get_aspect() == 1.0 and ax.get_xlim() == ax.get_ylim() == (0, 1)
    assert len(ax.collections) == 1  # SD band, coloured
    diag = [l for l in ax.get_lines() if getattr(l, "_figkit_aux", False)]
    assert len(diag) == 1 and diag[0].get_linestyle() == "--"
    _clean(fig)


def test_roc_mean_sd_single_run_no_band():
    fig, ax = plt.subplots(figsize=(2.4, 2.4), layout="constrained")
    curves.roc_mean_sd(ax, _runs(1), label=None)
    assert len(ax.collections) == 0 and np.isnan(ax._anchor_sd_auc)
    assert ax.get_legend().get_texts()[0].get_text() == f"AUC = {ax._anchor_mean_auc:.3f}"
    _clean(fig)


def test_roc_mean_sd_curve_input_two_models():
    fig, ax = plt.subplots(figsize=(2.4, 2.4), layout="constrained")
    curve_runs = [curves.roc_points(y, s) for y, s in _runs(3, seed=4)]
    curves.roc_mean_sd(ax, curve_runs, "A", kind="curve")
    curves.roc_mean_sd(ax, _runs(3, seed=5, shift=0.5), "B")
    assert set(ax._anchor_auc) == {"A", "B"} and ax._anchor_auc["A"][0] > ax._anchor_auc["B"][0]
    cols = [l.get_color() for l in ax.get_lines() if not getattr(l, "_figkit_aux", False)]
    assert cols == style.DATA_CYCLE[:2]
    assert sum(getattr(l, "_figkit_aux", False) for l in ax.get_lines()) == 1  # one diagonal
    assert len(ax.get_legend().get_texts()) == 2
    _clean(fig)


def test_roc_mean_sd_input_errors():
    ax = plt.subplots()[1]
    with pytest.raises(ValueError):
        curves.roc_mean_sd(ax, [])
    with pytest.raises(ValueError, match="both classes"):
        curves.roc_mean_sd(ax, [(np.zeros(5, int), np.arange(5.0))])


# ---------------------------------------------------------------- heat
def test_heat_hatch_cells_center_and_true_minus():
    M = pd.DataFrame([[-1.0, 0.5], [2.0, 0.0]], index=["a", "b"], columns=["x", "y"])
    hm = pd.DataFrame([[False, True], [False, False]], index=M.index, columns=M.columns)
    fig, ax = plt.subplots()
    heat.annotated(ax, M, "RdBu_r", center=0, hatch_mask=hm)
    assert np.isnan(ax._anchor_matrix[0, 1]) and len(ax.patches) == 1 and ax.patches[0]._figkit_aux
    assert sorted(t.get_text() for t in ax.texts) == ["0.00", "2.00", "n/a", "−1.00"]
    n = ax._anchor_mappable.norm
    assert n.vmin == -2 and n.vmax == 2
    assert qa.true_minus(fig) == []


def test_heat_no_text_when_fmt_none():
    fig, ax = plt.subplots()
    heat.annotated(ax, pd.DataFrame(np.eye(3)), "Blues", fmt=None)
    assert len(ax.texts) == 0


def test_heat_grey_cmap_rejected():
    with pytest.raises(ValueError, match="grey"):
        heat.annotated(plt.subplots()[1], pd.DataFrame(np.eye(2)), "Greys")


def test_heat_colour_audit_clean():
    M = pd.DataFrame(np.random.default_rng(0).normal(size=(3, 4)), index=list("abc"), columns=list("wxyz"))
    fig, ax = plt.subplots(figsize=(2.4, 1.8), layout="constrained")
    heat.annotated(ax, M, "RdBu_r", center=0, cbar=True, cbar_label="Δ")
    _clean(fig)


def test_waterfall_closes():
    fig, ax = plt.subplots()
    heat.waterfall(ax, 0.3, pd.Series({"a": 1.0, "b": -0.4, "c": 0.2}), 1.1)
    assert abs(ax._anchor_closure_error) < 1e-9
    assert np.allclose(ax._anchor_cumulative, [1.3, 0.9, 1.1])


def test_waterfall_raises_when_open():
    with pytest.raises(ValueError, match="does not close"):
        heat.waterfall(plt.subplots()[1], 0.0, pd.Series({"a": 1.0}), 2.0)


@pytest.mark.parametrize("start,contribs,end", [
    (0.0, {"a": 1.0, "b": np.nan}, 1.0),  # would "close" if NaN were skipped by .sum()
    (np.nan, {"a": 1.0}, 1.0),
    (0.0, {"a": 1.0}, np.nan),
    (0.0, {"a": np.inf}, np.inf)])
def test_waterfall_nan_raises(start, contribs, end):
    with pytest.raises(ValueError, match="non-finite"):
        heat.waterfall(plt.subplots()[1], start, pd.Series(contribs), end)


@pytest.mark.parametrize("orientation", ["horizontal", "vertical"])
def test_waterfall_colour_audit_clean(orientation):
    fig, ax = plt.subplots(figsize=(2.4, 1.8), layout="constrained")
    heat.waterfall(ax, 0.3, pd.Series({"a": 0.5, "b": -0.2}), 0.6, orientation=orientation)
    _clean(fig)


# ---------------------------------------------------------------- imaging
def _bscan(H=120, W=240, seed=0):
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(0.4, 0.1, (H, W)) + np.linspace(0, 0.3, H)[:, None], 0, 1)


def test_imaging_upsample_shape_and_boundaries():
    raw = np.zeros((124, 128))
    b = np.tile(np.linspace(.2, .8, 4)[:, None], (1, 32))
    fig, ax = plt.subplots()
    imaging.bscan_with_boundaries(ax, raw, b, band_masks=np.random.default_rng(0).random((5, 124, 128)))
    assert ax._anchor_bands.shape == (5, 124, 128)
    assert len(ax.get_lines()) == 4 and np.isclose(ax.get_lines()[0].get_xdata()[-1], 127)
    assert np.isclose(ax._anchor_boundaries_px[3, 0], 0.8 * 124)


def test_imaging_aspect_equal_and_raw_flag():
    fig, (a, b) = plt.subplots(1, 2)
    imaging.bscan_with_boundaries(a, _bscan(), np.full((2, 16), 0.5))
    imaging.concept_map(b, _bscan(), np.ones((8, 4)), vmin=0, vmax=1)
    for ax in (a, b):
        assert ax.get_aspect() == 1.0
        assert ax.images[0]._figkit_raw_image is True
    assert len(b.images) == 2 and not getattr(b.images[1], "_figkit_raw_image", False)
    assert np.isclose(imaging.upsample(np.ones((3, 5)), (7, 11)), 1).all()


def test_concept_map_uses_shared_scale():
    raw = np.zeros((60, 90))
    sp = np.random.default_rng(0).random((16, 8)) * 0.1
    fig, ax = plt.subplots()
    imaging.concept_map(ax, raw, sp, vmin=0, vmax=1)
    im = ax._anchor_mappable
    assert ax._anchor_upsampled.shape == (60, 90)
    assert (im.norm.vmin, im.norm.vmax) == (0, 1)
    assert np.all(np.asarray(im.get_alpha()) == 0)  # all below 15% of the shared scale


def test_concept_map_nonpositive_transparent_with_negative_vmin():
    sp = np.full((8, 4), -0.5)
    sp[:4] = 0.8
    fig, ax = plt.subplots()
    imaging.concept_map(ax, np.zeros((40, 40)), sp, vmin=-1, vmax=1)
    a, up = ax._anchor_alpha, ax._anchor_upsampled
    assert (a[up <= 0] == 0).all() and (a[up >= 0.8 - 1e-9] > 0).any()


def test_concept_map_requires_valid_scale():
    with pytest.raises(ValueError, match="shared scale"):
        imaging.concept_map(plt.subplots()[1], np.zeros((4, 4)), np.ones((2, 2)), vmin=1, vmax=1)


def test_imaging_colour_audit_clean():
    from figkit import layout
    raws = [_bscan(seed=1), _bscan(seed=2)]
    wr = layout.image_width_ratios([r.shape for r in raws])
    fig, (a, b) = plt.subplots(1, 2, figsize=(4.0, 1.0), gridspec_kw={"width_ratios": wr,
                                                                      "wspace": 0.02},
                               layout="constrained")
    fig.get_layout_engine().set(w_pad=0, h_pad=0, wspace=0, hspace=0)
    rng = np.random.default_rng(0)
    imaging.bscan_with_boundaries(a, raws[0], np.vstack([np.full(32, .3), np.full(32, .6)]),
                                  band_masks=rng.random((3,) + raws[0].shape) > 0.7)
    imaging.prob_overlay(b, raws[1], rng.random((16, 8)), vmin=0, vmax=1)
    _clean(fig)


# ---------------------------------------------------------------- fix round 1
def test_roc_scores_never_misread_as_curve():
    # labels / scores that are both non-decreasing with 0 -> 1 endpoints used to be read as a curve
    fig, ax = plt.subplots()
    curves.roc_mean_sd(ax, [(np.array([0, 0, 1, 1]), np.array([0.1, 0.2, 0.3, 1.0]))], "m")
    assert np.isclose(ax._anchor_mean_auc, 1.0)
    with pytest.raises(ValueError, match="kind"):
        curves.roc_mean_sd(ax, _runs(2), kind="auto")


@pytest.mark.parametrize("fpr,tpr", [
    ([0.1, 0.5, 1.0], [0.2, 0.6, 1.0]),      # does not start at 0
    ([0.0, 0.5, 0.9], [0.0, 0.6, 1.0]),      # does not end at 1
    ([0.0, 0.6, 0.4, 1.0], [0.0, .5, .6, 1]),  # fpr not monotone
    ([0.0, 0.5, 1.5], [0.0, 0.6, 1.0]),      # fpr outside [0, 1]
    ([0.0, 0.5, 1.0], [0.0, 0.6])])           # length mismatch
def test_roc_curve_kind_validates(fpr, tpr):
    with pytest.raises(ValueError, match="curve"):
        curves.roc_mean_sd(plt.subplots()[1], [(fpr, tpr)], kind="curve")


def test_band_masks_never_resized():
    with pytest.raises(ValueError, match="never resized"):
        imaging.bscan_with_boundaries(plt.subplots()[1], np.zeros((40, 60)), np.full((1, 8), .5),
                                      band_masks=np.ones((2, 10, 15)))


def test_band_masks_native_shape_kept_exactly():
    m = np.random.default_rng(0).random((2, 40, 60)) > 0.5
    fig, ax = plt.subplots()
    imaging.bscan_with_boundaries(ax, np.zeros((40, 60)), np.full((1, 8), .5), band_masks=m)
    assert np.array_equal(ax._anchor_bands, m.astype(float))


def test_prob_overlay_records_resampling_and_colour_audit_clean():
    fig, ax = plt.subplots(figsize=(2.0, 1.0), layout="constrained")
    fig.get_layout_engine().set(w_pad=0, h_pad=0)
    imaging.prob_overlay(ax, _bscan(), np.random.default_rng(1).random((16, 8)), vmin=0, vmax=1)
    assert ax._anchor_resampled == ((16, 8), (120, 240), "bilinear")
    assert ax._anchor_upsampled.shape == (120, 240) and ax.get_aspect() == 1.0
    assert ax._anchor_mappable.get_label() == "probability map"
    assert (ax._anchor_mappable.norm.vmin, ax._anchor_mappable.norm.vmax) == (0, 1)
    _clean(fig)
    fig, ax = plt.subplots()
    imaging.prob_overlay(ax, np.zeros((16, 8)), np.ones((16, 8)), vmin=0, vmax=1, resample="nearest")
    assert ax._anchor_resampled == ((16, 8), (16, 8), "none")
    with pytest.raises(ValueError, match="resample"):
        imaging.prob_overlay(ax, np.zeros((4, 4)), np.ones((2, 2)), 0, 1, resample="cubic")


def test_step_ladder_column_names():
    lad = _ladder().rename(columns={"stage": "phase", "value": "score", "probe": "held_out"})
    fig, ax = plt.subplots()
    curves.step_ladder(ax, lad, ["s0", "s1", "s2"], stage="phase", value="score", probe="held_out")
    assert ax.get_lines()[2].get_markerfacecolor() == "white"
    assert list(ax.get_lines()[0].get_ydata()) == [.8, .85, .9]


def test_heat_fmt_hyphen_kept_only_minus_converted():
    M = pd.DataFrame([[-1.5, 2.0]], index=["r"], columns=["a", "b"])
    fig, ax = plt.subplots()
    heat.annotated(ax, M, "RdBu_r", center=0, fmt="x-{:.1f}")
    assert sorted(t.get_text() for t in ax.texts) == ["x-2.0", "x-−1.5"]


def test_shared_aux_constants_in_style():
    assert confusion.ABSENT_FILL == heat.NA_FILL == style.NA_FILL
    assert intervals.GREY == curves.GREY == style.GREY
