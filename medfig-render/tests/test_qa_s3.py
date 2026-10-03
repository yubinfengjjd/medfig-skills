"""S3 colour audit: data artists must be coloured; grey only for auxiliary elements (synthetic figures)."""
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest

from test_core import _fake_tools
from figkit import export, qa, style
from figkit.provenance import Provenance


def _fig():
    return plt.subplots(figsize=(3, 2))


def test_data_cycle_starts_saturated_and_excludes_black():
    cyc = [c["color"] for c in style.RC["axes.prop_cycle"]]
    assert cyc[0] == "#0072B2" and "#000000" not in cyc
    assert all(qa._coloured([c]) for c in cyc)
    assert len(style.OKABE_ITO) == 8


def test_aux_marks_and_returns():
    fig, ax = _fig()
    ln = style.aux(ax.axhline(0))
    assert ln._figkit_aux is True
    a, b = style.aux(ax.axvline(0), ax.axvline(1))
    assert a._figkit_aux and b._figkit_aux


def test_black_line_flagged():
    fig, ax = _fig(); ax.plot([0, 1, 2], [0, 1, 0], color="k")
    assert qa.colour_audit(fig) == ["colour ax0: achromatic data artist Line2D"]


def test_default_cycle_line_clean():
    fig, ax = _fig()
    for k in range(3):
        ax.plot([0, 1, 2], [k, k + 1, k])
    assert qa.colour_audit(fig) == []


def test_grey_bars_flagged():
    fig, ax = _fig(); ax.bar([0, 1], [1, 2], color="0.5")
    assert qa.colour_audit(fig) == ["colour ax0: achromatic data artist Rectangle"]


def test_coloured_bars_with_grey_reference_lines_clean():
    fig, ax = _fig(); ax.bar([0, 1], [1, 2], color="#0072B2", edgecolor="k")
    ax.axhline(1.5, color="0.5", ls="--"); ax.axvline(0.5, color="k")
    style.aux(ax.plot([0, 2], [0, 2], color="0.6")[0])  # y = x diagonal via plot must be aux-marked
    ax.axline((0, 0), (1, 1), color="0.5")
    assert qa.colour_audit(fig) == []


def test_grey_band_flagged_unless_aux():
    fig, ax = _fig(); ax.plot([0, 1, 2], [0, 1, 0])
    band = ax.axvspan(0.2, 0.8, color="0.9")
    fill = ax.fill_between([0, 1, 2], [0, 0, 0], [0.2, 0.2, 0.2], color="0.8")
    assert len(qa.colour_audit(fig)) == 2
    style.aux(band, fill)
    assert qa.colour_audit(fig) == []


def test_grey_scatter_flagged_coloured_scatter_clean():
    fig, ax = _fig(); ax.scatter([0, 1], [0, 1], color="0.3")
    assert qa.colour_audit(fig) == ["colour ax0: achromatic data artist PathCollection"]
    fig, ax = _fig(); ax.scatter([0, 1], [0, 1], facecolor="none", edgecolor="#D55E00")
    assert qa.colour_audit(fig) == []


def test_raw_grey_image_marked_clean():
    img = np.random.default_rng(0).random((50, 80))
    fig, ax = _fig(); im = ax.imshow(img, cmap="gray"); im._figkit_raw_image = True
    assert qa.colour_audit(fig) == []
    fig, ax = _fig(); ax.imshow(img, cmap="gray"); ax._figkit_image_axes = True
    assert qa.colour_audit(fig) == []


@pytest.mark.parametrize("cmap", ["gray", "Greys", "binary", "gist_gray", "bone", "Greys_r"])
def test_grey_heatmap_unmarked_flagged(cmap):
    fig, ax = _fig(); ax.imshow(np.arange(12).reshape(3, 4), cmap=cmap)
    msgs = qa.colour_audit(fig)
    assert len(msgs) == 1 and "AxesImage" in msgs[0]


def test_coloured_heatmap_and_colorbar_clean():
    fig, ax = _fig(); im = ax.imshow(np.arange(12).reshape(3, 4), cmap="viridis"); fig.colorbar(im, ax=ax)
    assert qa.colour_audit(fig) == []


def test_transparent_colours_ignored():
    assert qa._coloured([(0, 0, 0, 0), "#0072B2"])
    assert not qa._coloured([(0, 0, 0, 0), "k"])
    assert mcolors.to_rgba("none")[3] == 0


def test_save_raises_for_achromatic_figure(project, monkeypatch):
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig, ax = _fig(); ax.plot([0, 1, 2], [0, 1, 0], color="k")
    with pytest.raises(RuntimeError, match=r"QA failed[\s\S]*colour="):
        export.save(fig, "t", Provenance("t"), cfg=project)
    assert "export_kw" not in seen
    assert not (project.out_dir / "figures").exists()


def test_save_records_clean_colour(project, monkeypatch):
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig, ax = _fig(); ax.plot([0, 1, 2], [0, 1, 0])
    res = export.save(fig, "t", Provenance("t"), cfg=project, panels="none")
    assert res["qa"]["colour"] == []


LINE = ["colour ax0: achromatic data artist Line2D"]


def test_black_forest_ci_flagged():
    fig, ax = _fig()
    ax.errorbar([0.8, 1.1], [0, 1], xerr=[[0.2, 0.3], [0.3, 0.2]], fmt="s", color="k")
    assert "colour ax0: achromatic data artist Line2D" in qa.colour_audit(fig)
    fig, ax = _fig()  # CIs as horizontal 2-point lines + point estimates
    for y, (lo, hi) in enumerate([(0.6, 1.0), (0.9, 1.3)]):
        ax.plot([lo, hi], [y, y], color="k")
    assert qa.colour_audit(fig) == LINE


def test_black_single_point_marker_flagged():
    fig, ax = _fig(); ax.plot([1.0], [0.5], "s", color="k")
    assert qa.colour_audit(fig) == LINE


def test_flat_grey_line_with_markers_flagged():
    fig, ax = _fig(); ax.plot([0, 1, 2], [1, 1, 1], color="0.5", marker="o")
    assert qa.colour_audit(fig) == LINE


def test_grey_data_on_diagonal_flagged_unless_aux():
    fig, ax = _fig(); ln, = ax.plot([0, 1, 2, 3], [0, 1, 2, 3], color="0.4", marker="o")
    assert qa.colour_audit(fig) == LINE
    style.aux(ln)
    assert qa.colour_audit(fig) == []


def test_axhline_and_axline_grey_clean():
    fig, ax = _fig(); ax.plot([0, 1, 2], [0, 1, 0])
    ax.axhline(0.5, color="0.5"); ax.axvline(1, color="k"); ax.axline((0, 0), (1, 1), color="0.5")
    assert qa.colour_audit(fig) == []


def test_coloured_errorbar_clean():
    fig, ax = _fig()
    ax.errorbar([0.8, 1.1], [0, 1], xerr=[[0.2, 0.3], [0.3, 0.2]], fmt="s", color="#0072B2")
    assert qa.colour_audit(fig) == []
