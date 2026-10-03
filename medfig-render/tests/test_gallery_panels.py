"""New gallery panel functions: numbers vs reference formulas, S1-S3 audits clean. Synthetic data only."""
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from figkit import layout, qa, stats, style
from figkit.panels import bars, curves, intervals, scatter


def _clean(fig):
    assert qa.colour_audit(fig) == []
    assert qa.text_only_panel(fig) == []


def _data(seed=0, n=600):
    rng = np.random.default_rng(seed)
    y = rng.integers(0, 2, n)
    p = np.clip(0.3 * y + rng.uniform(0, 0.7, n), 0, 1)
    return y, p


# ---------------------------------------------------------------- calibration
def test_calibration_bins_match_hand_formula():
    y, p = _data()
    mp, fo, cnt, brier = curves.calibration_bins(y, p, n_bins=5)
    edges = np.linspace(0, 1, 6)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, 4)
    for k, (m, f, c) in enumerate(zip(mp, fo, cnt)):
        sel = idx == np.unique(idx)[k]
        assert c == sel.sum() and m == pytest.approx(p[sel].mean()) and f == pytest.approx(y[sel].mean())
    assert brier == pytest.approx(np.mean((p - y) ** 2))
    assert cnt.sum() == len(y)


def test_calibration_quantile_and_errors():
    y, p = _data(1)
    _, _, cnt, _ = curves.calibration_bins(y, p, n_bins=4, strategy="quantile")
    assert abs(cnt.max() - cnt.min()) <= 2
    with pytest.raises(ValueError):
        curves.calibration_bins(y, p + 2)
    with pytest.raises(ValueError):
        curves.calibration_bins(y, p, strategy="x")
    fig, ax = plt.subplots()
    curves.calibration(ax, y, p, label="A")
    curves.calibration(ax, *_data(2), label="B")
    assert set(ax._anchor_calibration) == {"A", "B"}
    _clean(fig)


# ---------------------------------------------------------------- decision curve
def test_net_benefit_matches_loop_formula():
    y, p = _data(3)
    t = np.array([0.1, 0.3, 0.5, 0.7])
    nb, nb_all = curves.net_benefit(y, p, t)
    n, prev = len(y), y.mean()
    for i, th in enumerate(t):
        pred = p > th
        tp, fp = int((pred & (y == 1)).sum()), int((pred & (y == 0)).sum())
        assert nb[i] == pytest.approx(tp / n - fp / n * th / (1 - th))
        assert nb_all[i] == pytest.approx(prev - (1 - prev) * th / (1 - th))
    with pytest.raises(ValueError):
        curves.net_benefit(y, p, [0.0, 0.5])


def test_decision_records_clip_and_aux_treat_none():
    fig, ax = plt.subplots()
    curves.decision(ax, *_data(4), label="A", ylim=(-0.05, 0.6))
    curves.decision(ax, *_data(5), label="B", treat_all_color="aux", ylim=(-0.05, 0.6))
    d = ax._anchor_dca
    assert d["A"]["clipped_from"] is not None  # treat all falls below -0.05 at high thresholds
    assert sum(getattr(ln, "_figkit_aux", False) for ln in ax.get_lines()) == 2  # treat none + aux treat all
    _clean(fig)


# ---------------------------------------------------------------- PR / risk-coverage / ROC inset
def test_pr_points_ap_matches_sklearn():
    skm = pytest.importorskip("sklearn.metrics")
    for seed in range(3):
        y, p = _data(seed)
        _, _, ap = curves.pr_points(y, p)
        assert ap == pytest.approx(skm.average_precision_score(y, p), abs=1e-12)


def test_pr_mean_sd_runs_and_single():
    fig, ax = plt.subplots()
    curves.pr_mean_sd(ax, [_data(s) for s in range(3)], label="A")
    curves.pr_mean_sd(ax, [_data(9)], label="B")
    a, b = ax._anchor_pr["A"], ax._anchor_pr["B"]
    assert np.isfinite(a["sd_ap"]) and np.isnan(b["sd_ap"])
    assert (np.diff(a["mean_prec"]) <= 1e-12).all()  # envelope is non-increasing in recall
    _clean(fig)


def test_risk_coverage_hand_formula():
    rng = np.random.default_rng(0)
    conf = rng.permutation(200) / 200.0  # no ties
    correct = (rng.uniform(size=200) < conf).astype(int)
    cov, risk, aurc = curves.risk_coverage_points(correct, conf)
    o = np.argsort(-conf)
    err = 1 - correct[o]
    assert np.allclose(risk, np.cumsum(err) / np.arange(1, 201))
    assert risk[-1] == pytest.approx(1 - correct.mean())
    assert aurc == pytest.approx(np.sum(risk) / 200)
    fig, ax = plt.subplots()
    curves.risk_coverage(ax, correct, conf, label="A")
    _clean(fig)


def test_roc_inset_is_child_axes():
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], color=style.DATA_CYCLE[0])
    fpr, tpr = curves.roc_points(*_data(0))
    ins = curves.roc_inset(ax, [dict(fpr=fpr, tpr=tpr, label="A")])
    assert ins in ax.child_axes and ins.get_aspect() == 1.0
    assert 0.5 < ins._anchor_auc["A"] <= 1.0
    _clean(fig)


def test_capture_style_and_colour_keys():
    df = pd.DataFrame([(s, c, b, b * (0.5 if s == "x" else 0.8)) for s in ("x", "y") for c in ("A", "B")
                       for b in (0.1, 0.5, 1.0)], columns=["signal", "cohort", "budget", "capture"])
    fig, ax = plt.subplots()
    curves.capture(ax, df, group=["signal", "cohort"], colors={"x": "#AA4499", "y": "#44AA99"},
                   color_key=lambda k: k[0], style_key=lambda k: k[1])
    ls = {ln.get_label(): (ln.get_color(), ln.get_linestyle()) for ln in ax.get_lines()}
    assert ls["('x', 'A')"][0] == ls["('x', 'B')"][0] == "#AA4499"
    assert ls["('x', 'A')"][1] == ls["('y', 'A')"][1] != ls["('x', 'B')"][1]
    _clean(fig)


# ---------------------------------------------------------------- odds ratios
def test_odds_ratio_woolf_and_correction():
    r = stats.odds_ratio(30, 70, 10, 90)
    assert r["or_"] == pytest.approx(30 * 90 / (70 * 10))
    se = np.sqrt(1 / 30 + 1 / 70 + 1 / 10 + 1 / 90)
    assert r["lo"] == pytest.approx(np.exp(np.log(r["or_"]) - stats.Z95 * se))
    assert not r["corrected"]
    z = stats.odds_ratio(5, 0, 2, 10)
    assert z["corrected"] and z["or_"] == pytest.approx(5.5 * 10.5 / (0.5 * 2.5))
    with pytest.raises(ValueError):
        stats.odds_ratio(-1, 2, 3, 4)


def test_risk_group_or_and_forest():
    y, p = _data(6, 1000)
    t = stats.risk_group_or(y, p, n_groups=5)
    assert len(t) == 5 and t["n"].sum() == 1000 and t.loc[0, "or_"] == 1.0
    assert np.isnan(t.loc[0, "lo"]) and (t.loc[1:, "lo"] < t.loc[1:, "or_"]).all()
    t3 = stats.risk_group_or(y, p, edges=[0.25, 0.75])
    assert len(t3) == 3
    fig, ax = plt.subplots()
    intervals.or_forest(ax, t.assign(label=[f"Q{i}" for i in t["group"]]))
    assert ax.get_xscale() == "log" and set(ax._anchor_or) == {f"Q{i}" for i in range(1, 6)}
    _clean(fig)


# ---------------------------------------------------------------- slope / scorecard
def test_slope_mean_and_run_alpha():
    rows = [(g, r, x, v + (0.1 if g == "B" else 0) + 0.01 * r)
            for g in ("A", "B") for r in range(3) for x, v in (("R0", 0.8), ("R1", 0.7))]
    df = pd.DataFrame(rows, columns=["group", "run", "rule", "bacc"])
    fig, ax = plt.subplots()
    intervals.slope(ax, df, "rule", "bacc", "group", "run", ["R0", "R1"])
    assert ax._anchor_slope_mean["A"] == pytest.approx([0.81, 0.71])
    thin = [ln for ln in ax.get_lines() if ln.get_alpha() == 0.5]
    assert len(thin) == 6
    _clean(fig)


STATUS = {"supported": dict(color="#009988", marker="^", label="Supported"),
          "inconclusive": dict(color="#004488", marker="o", label="Inconclusive")}


def test_scorecard_legend_lists_present_statuses_only():
    rows = pd.DataFrame(dict(label=["H1", "H2"], est=[0.1, 0.0], lo=[0.0, -0.1], hi=[0.2, 0.1],
                             status=["inconclusive", "inconclusive"]))
    fig, ax = plt.subplots()
    intervals.scorecard(ax, rows, STATUS)
    assert [t.get_text() for t in ax.get_legend().get_texts()] == ["Inconclusive"]
    _clean(fig)
    with pytest.raises(ValueError):
        intervals.scorecard(ax, rows.assign(status="x"), STATUS)


# ---------------------------------------------------------------- scatter / bars / layout
def test_gated_bubble_hollow_hatch_for_failing():
    rows = pd.DataFrame(dict(label=["a", "b"], x=[0.1, 0.01], est=[0.9, 0.6], lo=[0.85, 0.3],
                             hi=[0.95, 0.9], n=[400, 9], passes=[True, False]))
    fig, ax = plt.subplots()
    ax.set_xscale("log")
    scatter.gated_bubble(ax, rows, ref=0.5)
    cols = ax.collections
    assert cols[1].get_hatch() == "//////" and cols[0].get_hatch() is None
    assert ax._anchor_gate == {"a": True, "b": False}
    assert ax._anchor_area[0] > ax._anchor_area[1]
    _clean(fig)


def test_sized_scatter_symlog_and_aux_key():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(dict(g=rng.choice(["A", "B"], 50), sd=rng.uniform(0, 0.1, 50),
                           agree=rng.uniform(0.3, 1, 50), n=rng.integers(2, 300, 50)))
    fig, ax = plt.subplots()
    scatter.sized(ax, df, "sd", "agree", "g", "n", key_sizes=[10, 100], symlog=True)
    assert ax.get_xscale() == "symlog" and sum(ax._anchor_groups.values()) == 50
    _clean(fig)


def test_stacked_fraction_sums_and_absent():
    rows = pd.DataFrame(dict(label=["X", "Y"], s1=[6, 0], s2=[3, 0], s3=[1, 0]))
    pal = {"s1": dict(color="#DDCC77"), "s2": dict(color="#CC6677"), "s3": dict(color="#882255")}
    fig, ax = plt.subplots()
    bars.stacked_fraction(ax, rows, ["s1", "s2", "s3"], palette=pal)
    assert ax._anchor_frac["X"] == pytest.approx({"s1": 0.6, "s2": 0.3, "s3": 0.1})
    assert ax._anchor_absent == ["Y"]
    _clean(fig)


def test_small_multiples_square_cells():
    fig = plt.figure()
    axes, size = layout.small_multiples(fig, 5, 3)
    assert len(axes) == 5 and all(a.get_box_aspect() == 1 for a in axes)
    assert size[0] > size[1]
    with pytest.raises(ValueError):
        layout.small_multiples(fig, 0, 3)


# ---------------------------------------------------------------- palette clash gate + delta_e
def test_delta_e_matches_reference_values():
    # Sharma et al. 2005 CIEDE2000 test pair 1 is in Lab; check sRGB pairs against skimage when present
    sk = pytest.importorskip("skimage.color")
    from matplotlib.colors import to_rgb
    for a, b in [("#0072B2", "#0077BB"), ("#E69F00", "#F0E442"), ("#000000", "#FFFFFF"), ("#B2182B", "#999933")]:
        la, lb = (sk.rgb2lab(np.array([[to_rgb(c)]]))[0, 0] for c in (a, b))
        assert style.delta_e(a, b) == pytest.approx(float(sk.deltaE_ciede2000(la, lb)), abs=0.02)


@pytest.mark.parametrize("a, b, flagged", [
    ("#0077BB", "#0072B2", True),   # action vs cohort blue, dE 2.0
    ("#44AA99", "#009E73", True),   # component vs cohort green, dE 9.6
    ("#E69F00", "#F0E442", False),  # Okabe-Ito neighbours, dE 21.7
    ("#0072B2", "#0072B2", False),  # identical = same encoding
])
def test_palette_clash_flags_near_identical_hues(a, b, flagged):
    fig, ax = plt.subplots()
    ax.bar([0], [1], color=a)
    ax.bar([1], [1], color=b)
    assert bool(qa.palette_clash(fig, min_de=12)) is flagged


def test_palette_clash_ignores_aux_and_grey_and_uses_config(tmp_path):
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1], color="#0072B2")
    style.aux(ax.plot([0, 1], [1, 0], color="#0077BB")[0])  # aux: exempt
    ax.plot([0, 1], [0.5, 0.5], color="#4D4D4D", marker="o")  # grey: not a hue
    assert qa.palette_clash(fig, min_de=12) == []
    from figkit import config
    (tmp_path / "data").mkdir()
    p = tmp_path / "figkit.toml"
    p.write_text('data_root = "data"\n[qa]\npalette_min_delta_e = 1.0\n', encoding="utf-8")
    cfg = config.load(p)
    fig2, ax2 = plt.subplots()
    ax2.bar([0], [1], color="#0077BB")
    ax2.bar([1], [1], color="#0072B2")
    assert qa.palette_clash(fig2, cfg=cfg) == []  # 2.0 >= project floor 1.0
    p.write_text('data_root = "data"\n[qa]\npalette_min_delta_e = "x"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="palette_min_delta_e"):
        config.load(p)
    config.use(None)
