"""stats: Bland-Altman limits (vs statsmodels), exact P-value text, structure-strength pre-check
(after taoge946/academic-figure-patterns, MIT), exceedance / binned medians. Synthetic data only."""
import numpy as np
import pytest

from figkit import stats


def test_bland_altman_matches_statsmodels():
    sm = pytest.importorskip("statsmodels.graphics.agreement")
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(1)
    a = rng.normal(300, 40, 200)
    b = a + rng.normal(5, 12, 200)
    r = stats.bland_altman(a, b)
    assert r["n"] == 200
    assert r["bias"] == pytest.approx(np.mean(a - b))
    sd = np.std(a - b, ddof=1)
    assert r["loa_lo"] == pytest.approx(r["bias"] - 1.96 * sd) and r["loa_hi"] == pytest.approx(r["bias"] + 1.96 * sd)
    fig, ax = plt.subplots()
    sm.mean_diff_plot(a, b, ax=ax)  # statsmodels: mean +- 1.96 SD with population SD (ddof = 0)
    ys = sorted(round(l.get_ydata()[0], 9) for l in ax.lines if len(set(l.get_ydata())) == 1)
    r0 = stats.bland_altman(a, b, ddof=0)
    assert ys == pytest.approx(sorted([r0["loa_lo"], r0["bias"], r0["loa_hi"]]))
    assert r["loa_hi"] - r["loa_lo"] > r0["loa_hi"] - r0["loa_lo"]  # sample SD (default) is wider
    plt.close(fig)
    np.testing.assert_allclose(r["mean"], (a + b) / 2)


def test_bland_altman_ci_and_input_checks():
    rng = np.random.default_rng(2)
    a = rng.normal(size=50); b = a + rng.normal(0.1, 0.5, 50)
    r = stats.bland_altman(a, b)
    se_bias = np.std(a - b, ddof=1) / np.sqrt(50)
    from scipy import stats as st
    t = st.t.ppf(0.975, 49)
    assert r["bias_lo"] == pytest.approx(r["bias"] - t * se_bias)
    assert r["bias_hi"] == pytest.approx(r["bias"] + t * se_bias)
    with pytest.raises(ValueError, match="same length"):
        stats.bland_altman([1, 2], [1])
    r2 = stats.bland_altman([1, 2, np.nan, 4], [1.1, 2.2, 3, 3.9])  # pairs with a non-finite value dropped
    assert r2["n"] == 3 and r2["n_dropped"] == 1


@pytest.mark.parametrize("p,text", [
    (0.0123, "P = 0.012"), (0.049, "P = 0.049"), (0.05, "P = 0.050"), (0.2407, "P = 0.24"),
    (0.5625, "P = 0.56"), (0.999, "P > 0.99"), (1.0, "P > 0.99"), (0.00042, "P = 4.2 × 10⁻⁴"),
    (0.0000001, "P < 1 × 10⁻⁶"), (0.001, "P = 0.001"),
])
def test_p_text(p, text):
    assert stats.p_text(p) == text


def test_p_text_rejects_bad_values():
    for bad in (-0.1, 1.2, np.nan):
        with pytest.raises(ValueError):
            stats.p_text(bad)


def test_structure_strength_paired_and_mechanism():
    rng = np.random.default_rng(0)
    x = rng.normal(size=2000)
    out = stats.structure_strength(x, x + rng.normal(0, 0.05, 2000))
    assert out["passes"] and out["corr"] > 0.99 and out["n"] == 2000
    out = stats.structure_strength(x, rng.normal(size=2000))
    assert not out["passes"] and abs(out["corr"]) < 0.1
    # mechanism: monotone but noisy -> binned-median rise beats the median IQR width
    y = np.tanh(x) * 3 + rng.normal(0, 1.0, 2000)
    m = stats.structure_strength(x, y, kind="mechanism")
    assert m["passes"] and m["median_rise"] > m["median_iqr"]
    m0 = stats.structure_strength(x, rng.normal(size=2000), kind="mechanism")
    assert not m0["passes"]


def test_structure_strength_ignores_nonfinite():
    x = np.array([0.0, 1.0, 2.0, 3.0, np.nan, 5.0])
    y = np.array([0.0, 1.0, 2.0, np.inf, 4.0, 5.0])
    assert stats.structure_strength(x, y)["n"] == 4


def test_exceedance_and_binned_median():
    v = np.array([1, 2, 3, 4, 5], float)
    xs, frac = stats.exceedance(v, xs=[0, 2, 5, 6])
    np.testing.assert_allclose(frac, [1.0, 0.6, 0.0, 0.0])  # fraction strictly above x
    rng = np.random.default_rng(3)
    x = rng.uniform(0, 10, 1000); y = x + rng.normal(0, 1, 1000)
    b = stats.binned_median(x, y, nbins=5)
    assert len(b["center"]) == 5 and np.all(np.diff(b["median"]) > 0)
    assert np.all(b["q25"] <= b["median"]) and np.all(b["median"] <= b["q75"])
    assert int(np.sum(b["count"])) == 1000


def _pool(n=20, groups=("A", "B")):
    import pandas as pd
    rng = np.random.default_rng(3)
    return pd.DataFrame(dict(case=[f"{g}{i:02d}" for g in groups for i in range(n)],
                             group=[g for g in groups for _ in range(n)],
                             correct=rng.uniform(size=n * len(groups)) > 0.3))


def test_stratified_cases_counts_seed_and_record():
    df = _pool()
    sel, rec = stats.stratified_cases(df, "group", "correct", n_correct=5, n_error=2, seed=11, order="case",
                                      unique="case", pool="test pool")
    assert len(sel) == 14
    for g in ("A", "B"):
        s = sel[sel.group == g]
        assert (~s.correct).sum() == 2 and s.correct.sum() == 5
    assert rec["seed"] == 11 and rec["per_group"]["A"] == {"misclassified": 2, "correct": 5}
    assert rec["pool"] == "test pool" and "no confidence or visual ranking" in rec["rule"]
    assert sum(v for k, v in rec["pool_counts"].items() if k.startswith("A|")) == 20
    again, _ = stats.stratified_cases(df.sample(frac=1, random_state=0), "group", "correct", 5, 2, 11, order="case")
    assert list(again.case) == list(sel.case)  # input row order does not change the draw
    other, _ = stats.stratified_cases(df, "group", "correct", 5, 2, 12, order="case")
    assert list(other.case) != list(sel.case)


def test_stratified_cases_refuses_small_strata_and_repeats():
    df = _pool(n=6)
    with pytest.raises(ValueError, match="pool has"):
        stats.stratified_cases(df, "group", "correct", n_correct=5, n_error=5, seed=1)
    df2 = _pool()
    df2["eye"] = "same"
    with pytest.raises(ValueError, match="repeat eye"):
        stats.stratified_cases(df2, "group", "correct", 2, 1, seed=1, unique="eye")
