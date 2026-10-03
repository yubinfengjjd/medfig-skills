"""Soft theme (figkit.toml ``theme = "soft"``, idea after senlanke/figures4papers): light tint fill + saturated
same-hue edge per key colour, one emphasised method colour, ordinal single-hue gradients (adjacent
ΔE00 >= 12), white hatch separation. Every QA gate is unchanged. Synthetic data only."""
import itertools

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest

from figkit import config, qa, style

from test_core import _write_toml


def test_default_theme_unchanged(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\n'))
    assert cfg.theme == "default"


def test_theme_parsed_and_validated(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\ntheme = "soft"\n'))
    assert cfg.theme == "soft"
    with pytest.raises(ValueError, match="theme"):
        config.load(_write_toml(tmp_path, 'data_root = "data"\ntheme = "fancy"\n'))


def test_tint_is_lighter_same_hue():
    for c in style.SOFT_KEYS:
        t = style.tint(c)
        assert np.mean(mcolors.to_rgb(t)) > np.mean(mcolors.to_rgb(c))
        assert style.delta_e(c, t) > 12  # fill and edge read as two tones of one hue


def test_soft_palette_passes_s3_and_clash_gates():
    pal = style.soft_palette(len(style.SOFT_KEYS))
    assert len(pal) == 6 and all(set(p) == {"face", "edge"} for p in pal)
    faces, edges = [p["face"] for p in pal], [p["edge"] for p in pal]
    for a, b in itertools.combinations(range(6), 2):  # no two methods' colours clash (face or edge)
        for x, y in itertools.product((faces[a], edges[a]), (faces[b], edges[b])):
            assert style.delta_e(x, y) >= qa.PALETTE_MIN_DE, (a, b, x, y)
    fig, ax = plt.subplots()
    for i, p in enumerate(pal):  # S3: each bar's edge is saturated, so a light face is fine
        ax.bar([i], [1.0], color=p["face"], edgecolor=p["edge"], linewidth=0.8)
    assert qa.colour_audit(fig) == [] and qa.palette_clash(fig) == []


def test_soft_palette_too_many_raises():
    with pytest.raises(ValueError, match="at most 6"):
        style.soft_palette(7)


@pytest.mark.parametrize("n", [2, 3, 4, 5])
def test_ordinal_gradient_adjacent_distinct(n):
    g = style.ordinal_gradient("#0072B2", n)
    assert len(g) == n
    lum = [np.mean(mcolors.to_rgb(c)) for c in g]
    assert all(a > b for a, b in zip(lum, lum[1:]))  # light -> dark
    assert all(style.delta_e(a, b) >= qa.PALETTE_MIN_DE for a, b in zip(g, g[1:]))


def test_ordinal_gradient_too_many_levels_raises():
    with pytest.raises(ValueError, match="levels"):
        style.ordinal_gradient("#0072B2", 9)


def test_ordinal_gradient_marks_axes_and_passes_clash_gate():
    fig, ax = plt.subplots()
    g = style.ordinal_gradient("#009E73", 4)
    for i, c in enumerate(g):  # one shared edge = the darkest level (identical colours are not a clash)
        ax.barh([i], [0.5 + 0.1 * i], color=c, edgecolor=g[-1], linewidth=0.6)
    style.mark_ordinal(ax, levels=g)
    assert ax._figkit_ordinal == g
    assert qa.palette_clash(fig) == []  # adjacent levels are >= 12 apart; non-adjacent further


def test_ordinal_gradient_unmarked_close_levels_flagged():
    fig, ax = plt.subplots()  # an over-fine gradient (unmarked) still trips the clash gate
    r = np.array(mcolors.to_rgb("#0072B2"))
    for i, w in enumerate((0.30, 0.34)):
        ax.bar([i], [1], color=mcolors.to_hex(r + (1 - r) * w), edgecolor="none")
    assert qa.palette_clash(fig)


def test_soft_rc_applied_only_for_soft_theme(tmp_path):
    from conftest import SCIPILOT
    if not SCIPILOT.is_dir():
        pytest.skip("scipilot not installed")
    base = 'data_root = "data"\nscipilot_scripts = "' + SCIPILOT.as_posix() + '"\n'
    import matplotlib as mpl
    style.apply(config.load(_write_toml(tmp_path, base)))
    lw_default = mpl.rcParams["axes.linewidth"]
    style.apply(config.load(_write_toml(tmp_path, base + 'theme = "soft"\n')))
    assert mpl.rcParams["axes.linewidth"] > lw_default
    assert mpl.rcParams["legend.frameon"] is False
    assert mpl.rcParams["axes.labelsize"] == 7 and mpl.rcParams["xtick.labelsize"] == 6.5
    assert mpl.rcParams["axes.spines.top"] is False and mpl.rcParams["axes.spines.right"] is False
    assert mpl.rcParams["pdf.fonttype"] == 42 and mpl.rcParams["text.usetex"] is False
    assert style.current_theme() == "soft"
    style.apply(config.load(_write_toml(tmp_path, base)))
    assert mpl.rcParams["axes.linewidth"] == lw_default and style.current_theme() == "default"
