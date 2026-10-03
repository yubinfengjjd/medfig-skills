"""Soft-look comparison panels (compare) and per-sample evidence panels (evidence): QA gates stay empty,
numbers are stored on the axes and checked. Synthetic data only."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from figkit import qa, stats, style
from figkit.panels import compare, evidence, heat

M = ["a", "b", "c", "ours"]


def _df(seed=0, base=(0.70, 0.74, 0.78, 0.86), n=3):
    rng = np.random.default_rng(seed)
    return pd.DataFrame([(m, r, b + rng.normal(0, 0.01)) for m, b in zip(M, base) for r in range(n)],
                        columns=["method", "run", "value"])


@pytest.fixture
def soft():
    """Soft theme active for the gates (style.current_theme), restored afterwards."""
    old = style._THEME["name"]
    style._THEME["name"] = "soft"
    yield
    style._THEME["name"] = old


def _gates(fig):
    return dict(colour=qa.colour_audit(fig), palette=qa.palette_clash(fig), text_only=qa.text_only_panel(fig),
                figure_text=qa.figure_text_audit(fig), bar_baseline=qa.bar_baseline_audit(fig))


def test_metric_bars_flat_emphasis_values_and_legend(soft):
    df = _df(base=(0.20, 0.45, 0.62, 0.81))
    fig, (ax, lax) = plt.subplots(1, 2, figsize=(4, 2))
    compare.metric_bars(ax, df, "AUROC", M, emphasis="ours")
    compare.legend_panel(lax, M, emphasis="ours")
    assert ax._anchor_ylim[0] == 0 and not ax._anchor_truncated  # lowest mean < 40% of top -> from 0
    b = ax._anchor_bars
    for m in M:
        v = df.loc[df.method == m, "value"]
        assert b[m]["mean"] == pytest.approx(v.mean()) and b[m]["n"] == 3
        assert (b[m]["lo"], b[m]["hi"]) == pytest.approx((v.min(), v.max()))  # n <= 5: min-max whisker
    assert ax._anchor_whisker == "min–max over runs"
    assert ax.get_ylabel() == "AUROC ↑"
    assert ax._anchor_colours["ours"] == style.SOFT_EMPHASIS
    assert all(p.get_linewidth() == 0 and not p.get_hatch() for p in ax.patches)  # flat bars
    assert not ax.collections or all(len(c.get_offsets()) == 0 for c in ax.collections if hasattr(c, "get_offsets")
                                     and type(c).__name__ == "PathCollection")  # no run points by default
    texts = [t.get_text() for t in ax.texts]
    assert f"{b['ours']['mean']:.3f}" in texts and len(texts) == 4  # value labels
    assert all(not v for v in _gates(fig).values()), _gates(fig)


def test_metric_bars_truncate_with_break_mark(soft):
    df = _df(base=(0.80, 0.84, 0.86, 0.92))
    fig, ax = plt.subplots()
    compare.metric_bars(ax, df, "AUROC", M, emphasis="ours")
    y0, y1 = ax._anchor_ylim
    assert ax._anchor_truncated and 0 < y0 < min(s["lo"] for s in ax._anchor_bars.values())
    assert ax._figkit_axis_break == "y"
    for p, m in zip(ax.patches, M):  # bars drawn from the axis floor, heights still the means
        assert p.get_y() == pytest.approx(y0) and p.get_y() + p.get_height() == pytest.approx(ax._anchor_bars[m]["mean"])
    assert all(not v for v in _gates(fig).values()), _gates(fig)


def test_bar_baseline_gate_needs_break_mark(soft):
    fig, ax = plt.subplots()
    ax.bar([0, 1], [0.8, 0.9], color=style.SOFT_EMPHASIS)
    ax.set_ylim(0.7, 1.0)  # truncated, no break mark
    assert qa.bar_baseline_audit(fig)
    style.axis_break(ax, "y")
    assert qa.bar_baseline_audit(fig) == []


def test_bar_baseline_gate_off_in_default_theme():
    fig, ax = plt.subplots()
    ax.bar([0, 1], [0.8, 0.9], color="#0072B2")
    ax.set_ylim(0.7, 1.0)
    assert qa.bar_baseline_audit(fig) == []


def test_controls_group_tolerance_soft_only(soft):
    g = style.soft_controls(4, kind="gradient")
    assert min(style.delta_e(a, b) for a, b in zip(g, g[1:])) < qa.PALETTE_MIN_DE  # alike on purpose
    fig, ax = plt.subplots()
    for i, c in enumerate(g + [style.SOFT_EMPHASIS]):
        ax.bar([i], [1.0], color=c, edgecolor="none")
    assert qa.palette_clash(fig)  # undeclared group -> flagged
    style.mark_controls(ax, g)
    assert qa.palette_clash(fig) == [] and qa.colour_audit(fig) == []
    style._THEME["name"] = "default"
    assert qa.palette_clash(fig)  # tolerance is a soft-theme rule only


def test_gradient_controls_capped_and_spaced():
    g = style.soft_controls(4, kind="gradient")
    assert all(style.delta_e(a, b) >= style.CONTROL_MIN_DE for a, b in zip(g, g[1:]))
    assert min(style.delta_e(c, style.SOFT_EMPHASIS) for c in g) >= qa.PALETTE_MIN_DE
    with pytest.raises(ValueError, match="at most 4"):
        style.soft_controls(5, kind="gradient")


def test_pastel_controls_distinct_and_far_from_emphasis():
    c = style.soft_controls(6)
    import itertools
    assert min(style.delta_e(a, b) for a, b in itertools.combinations(c, 2)) >= qa.PALETTE_MIN_DE
    assert min(style.delta_e(a, style.SOFT_EMPHASIS) for a in c) >= 30
    assert min(style.delta_e(a, "#ffffff") for a in c) >= 11  # visible on white without an edge


def test_metric_bars_many_runs_use_sd_and_value_label_cap(soft):
    df = _df(n=8)
    fig, ax = plt.subplots()
    compare.metric_bars(ax, df, "AUPRC", M, higher_is_better=False)
    v = df.loc[df.method == "a", "value"]
    assert ax._anchor_bars["a"]["hi"] - ax._anchor_bars["a"]["mean"] == pytest.approx(v.std(ddof=1))
    assert ax.get_ylabel() == "AUPRC ↓" and ax._anchor_whisker == "mean ± SD"
    six = [f"m{i}" for i in range(6)]
    d6 = pd.DataFrame([(m, r, 0.5 + 0.05 * i) for i, m in enumerate(six) for r in range(3)],
                      columns=["method", "run", "value"])
    fig, ax = plt.subplots(figsize=(1.6, 1.8))  # narrow axes: labels must rotate to fit
    compare.metric_bars(ax, d6, "AUROC", six, emphasis="m5")
    assert len(ax.texts) == 6 and {t.get_fontsize() for t in ax.texts} == {5.0}  # dense -> 5 pt, still shown
    assert {t.get_rotation() for t in ax.texts} == {90.0}
    assert qa.min_font(fig) == []  # 5 pt allowed for value labels only
    fig.canvas.draw()
    top = ax.bbox.y1
    assert all(t.get_window_extent().y1 <= top + 1 for t in ax.texts)  # head room recomputed
    fig, ax = plt.subplots()
    ax.text(0.5, 0.5, "note", fontsize=5)
    assert qa.min_font(fig)  # ordinary 5 pt text still fails


def test_ordinal_bars_gradient_flat_and_gates(soft):
    rows = pd.DataFrame(dict(label=["base", "+A", "+A+B", "+A+B+C"], value=[0.70, 0.75, 0.79, 0.82],
                             lo=[0.68, 0.73, 0.77, 0.80], hi=[0.72, 0.77, 0.81, 0.84]))
    for key in style.SOFT_KEYS + [style.SOFT_EMPHASIS]:
        style.ordinal_gradient(key, 3, *style.ORDINAL_SOFT)  # every soft key supports 3 levels
    for key in style.SOFT_KEYS:
        style.ordinal_gradient(key, 4, *style.ORDINAL_SOFT)  # ... and SOFT_KEYS 4
    fig, ax = plt.subplots()
    compare.ordinal_bars(ax, rows, color="#009E73", lo_col="lo", hi_col="hi", xlabel="BACC")
    assert ax._anchor_ordinal["+A+B+C"] == pytest.approx(0.82) and len(ax._figkit_ordinal) == 4
    assert ax._anchor_xlim[0] > 0 and ax._figkit_axis_break == "x"
    assert all(p.get_linewidth() == 0 and not p.get_hatch() for p in ax.patches)
    assert [t.get_text() for t in ax.texts] == ["0.700", "0.750", "0.790", "0.820"]
    assert all(not v for v in _gates(fig).values()), _gates(fig)
    with pytest.raises(ValueError, match="levels"):
        compare.ordinal_bars(ax, pd.DataFrame(dict(label=list("abcdefg"), value=np.arange(7.0))))


def test_area_trend_events_legend_and_p_bracket(soft):
    x = np.arange(12)
    fig, ax = plt.subplots()
    compare.area_trend(ax, x, {"Group 1": np.full(12, 2.0), "Group 2": np.full(12, 1.0)}, cumulative=True,
                       hatches={"Group 2": "////"}, events=[(6, "Launch")])
    np.testing.assert_allclose(ax._anchor_area["Group 1"], np.cumsum(np.full(12, 2.0)))
    leg = ax.get_legend()
    assert [t.get_text() for t in leg.get_texts()] == ["Group 1", "Group 2"]
    assert any(t.get_text() == "Launch" for t in ax.texts)
    assert all(not v for v in _gates(fig).values()), _gates(fig)
    fig, ax = plt.subplots()
    df = _df(base=(0.40, 0.55, 0.62, 0.81))
    compare.metric_bars(ax, df, "AUROC", M, values=False)
    t = compare.p_bracket(ax, 0, 3, 0.86, 0.0123)
    assert t.get_text() == "P = 0.012"
    assert all(not v for v in _gates(fig).values()), _gates(fig)


def test_evidence_panels_numbers_and_gates():
    rng = np.random.default_rng(5)
    a = rng.gamma(2, 1, 500); b = a * 0.8 + rng.normal(0, 0.1, 500)
    fig, axes = plt.subplots(1, 4, figsize=(8, 2))
    evidence.exceedance(axes[0], a, color=style.DATA_CYCLE[0], label="A")
    evidence.exceedance(axes[0], b, color=style.DATA_CYCLE[1], label="B")
    xs, f = axes[0]._anchor_exceedance["A"]
    assert f[0] == pytest.approx(1 - 1 / 500) and f[-1] == 0
    evidence.paired_cloud(axes[1], a, b)
    assert axes[1]._anchor_paired["below_diagonal"] == pytest.approx(np.mean(b < a))
    evidence.binned_median(axes[2], a, b, nbins=6)
    assert len(axes[2]._anchor_binned["center"]) == 6
    evidence.bland_altman(axes[3], b, a, units="µm")
    ref = stats.bland_altman(b, a)
    assert axes[3]._anchor_ba["bias"] == pytest.approx(ref["bias"])
    texts = [t.get_text() for t in axes[3].texts]
    assert any(t.startswith("Bias ") for t in texts) and all("-" not in t for t in texts)
    g = _gates(fig)
    assert all(not v for v in g.values()), g
    assert qa.true_minus(fig) == []


def test_heat_gridlines_option():
    M2 = pd.DataFrame([[1, 2], [3, 4]], index=["r1", "r2"], columns=["c1", "c2"])
    fig, ax = plt.subplots()
    heat.annotated(ax, M2, "Reds", fmt="{:.0f}", gridlines=True)
    fig.canvas.draw()
    minor = [t.gridline for t in ax.xaxis.get_minor_ticks()]
    assert minor and all(g.get_visible() for g in minor) and minor[0].get_color() == "white"
    assert qa.colour_audit(fig) == []
