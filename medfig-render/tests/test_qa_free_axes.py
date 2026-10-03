"""S1-S3 on axes outside a GridSpec: fig.add_axes, inset / child axes, subfigures; colorbar / aux skipped."""
import matplotlib.pyplot as plt
import numpy as np

from figkit import qa, style


def _free(rect=(0.15, 0.15, 0.75, 0.75)):
    fig = plt.figure(figsize=(3, 2))
    return fig, fig.add_axes(list(rect))


def test_add_axes_black_line_flagged():
    fig, ax = _free()
    ax.plot([0, 1, 2], [0, 1, 0], color="k")
    assert qa.colour_audit(fig) == ["colour ax0: achromatic data artist Line2D"]


def test_add_axes_only_figure_coloured_clean():
    fig, ax = _free()
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    assert qa.colour_audit(fig) == [] and qa.text_only_panel(fig) == []


def test_add_axes_text_only_flagged():
    fig, ax = _free()
    ax.axis("off")
    ax.text(0.5, 0.5, "n = 120 cases", transform=ax.transAxes)
    assert qa.text_only_panel(fig) == ["text-only panel ax0"]


def test_inset_black_line_flagged():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    ins = ax.inset_axes([0.6, 0.6, 0.35, 0.35])
    ins.plot([0, 1], [1, 0], color="k")
    assert ins not in fig.axes  # child axes are only reachable via ax.child_axes
    assert qa.colour_audit(fig) == ["colour ax0.inset0: achromatic data artist Line2D"]


def test_inset_text_only_flagged():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    ins = ax.inset_axes([0.6, 0.6, 0.35, 0.35])
    ins.axis("off")
    ins.text(0.5, 0.5, "AUC 0.9", transform=ins.transAxes)
    assert qa.text_only_panel(fig) == ["text-only panel ax0.inset0"]


def test_subfigure_axes_audited():
    fig = plt.figure(figsize=(4, 2))
    left, right = fig.subfigures(1, 2)
    left.subplots().plot([0, 1, 2], [0, 1, 0], color="0.5")
    right.subplots().plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    assert qa.colour_audit(fig) == ["colour ax0: achromatic data artist Line2D"]


def test_add_axes_inset_marked_allows_5pt_ticks():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    ins = fig.add_axes([0.6, 0.6, 0.25, 0.25])
    ins.plot([0, 1], [1, 0], color=style.DATA_CYCLE[1])
    ins.tick_params(labelsize=5)
    assert any("5 pt" in m for m in qa.min_font(fig))  # unmarked add_axes: normal 6 pt floor
    ins._figkit_inset = True
    assert qa.min_font(fig) == []
    ins.set_xlabel("x", fontsize=5)  # the 5 pt allowance is for tick labels only
    assert qa.min_font(fig) == ["font 5 pt < 6 pt at ax1.text: 'x'"]


def test_child_inset_allows_5pt_ticks():
    fig, ax = plt.subplots(figsize=(3, 2))
    ins = ax.inset_axes([0.6, 0.6, 0.35, 0.35])
    ins.plot([0, 1], [1, 0], color=style.DATA_CYCLE[1])
    ins.tick_params(labelsize=5)
    assert qa.min_font(fig) == []


def test_colorbar_and_aux_axes_skipped():
    fig = plt.figure(figsize=(3, 2))
    ax = fig.add_axes([0.1, 0.15, 0.6, 0.75])
    im = ax.imshow(np.random.default_rng(0).random((8, 8)), cmap="viridis")
    cb = fig.colorbar(im, cax=fig.add_axes([0.75, 0.15, 0.04, 0.75]))
    cb.set_label("Probability")
    helper = fig.add_axes([0.85, 0.4, 0.1, 0.2])
    helper.axis("off")
    helper.text(0, 0.5, "legend")
    style.aux(helper)
    labels = [lab for lab, _ in qa._data_axes(fig)]
    assert labels == ["ax0"]
    assert qa.colour_audit(fig) == [] and qa.text_only_panel(fig) == []


def test_add_axes_whitespace_uses_own_rect():
    fig, ax = _free()
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    assert qa.whitespace_audit(fig) == []
    fig = plt.figure(figsize=(4, 2))
    ax = fig.add_axes([0.05, 0.05, 0.9, 0.9])
    ax.imshow(np.random.default_rng(0).random((300, 100)), cmap="viridis")  # tall image: letterboxed
    ax.set_axis_off()
    assert qa.whitespace_audit(fig) and "left+right blank" in qa.whitespace_audit(fig)[0]


def test_insets_not_audited_for_whitespace():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    ins = ax.inset_axes([0.6, 0.6, 0.35, 0.35])
    ins.imshow(np.random.default_rng(0).random((300, 30)), cmap="viridis")
    ins.set_axis_off()
    free = fig.add_axes([0.1, 0.6, 0.3, 0.3])
    free._figkit_inset = True
    free.imshow(np.random.default_rng(1).random((300, 30)), cmap="viridis")
    free.set_axis_off()
    assert qa.whitespace_audit(fig) == []


# ---------------------------------------------------------------- M1: reference / aux artists are not data
def test_reference_line_plus_text_is_text_only():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.axhline(0.5, color="0.6")
    ax.text(0.5, 0.7, "chance")
    assert qa.text_only_panel(fig) == ["text-only panel ax0"]


def test_aux_band_plus_text_is_text_only():
    fig, ax = plt.subplots(figsize=(3, 2))
    style.aux(ax.axvspan(0.2, 0.4, color="0.9"))
    ax.text(0.5, 0.7, "note")
    assert qa.text_only_panel(fig) == ["text-only panel ax0"]


def test_single_marker_plus_text_is_data():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0.5], [0.5], "o", color=style.DATA_CYCLE[0])
    ax.text(0.5, 0.7, "case 1")
    assert qa.text_only_panel(fig) == []


# ---------------------------------------------------------------- secondary axes are part of their parent
def _secondary():
    fig, ax = plt.subplots(figsize=(3, 2), layout="constrained")
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    ax.set_xlabel("time (h)"); ax.set_ylabel("signal")
    sx = ax.secondary_xaxis("top", functions=(lambda x: x * 60, lambda x: x / 60))
    sx.set_xlabel("time (min)")
    sy = ax.secondary_yaxis("right")
    sy.set_ylabel("signal (a.u.)")
    return fig, ax


def test_secondary_axes_not_audited():
    fig, _ax = _secondary()
    assert [lab for lab, _ in qa._data_axes(fig)] == ["ax0"]
    assert qa.text_only_panel(fig) == [] and qa.colour_audit(fig) == [] and qa.whitespace_audit(fig) == []


def test_secondary_axes_save_passes(project, monkeypatch):
    from figkit import export, panel
    from figkit.provenance import Provenance
    from test_core import _fake_tools
    _fake_tools(monkeypatch, {})
    fig, ax = _secondary()
    panel.mark_panel(ax, "a")
    res = export.save(fig, "sec", Provenance("sec"), size=(3, 2), cfg=project)
    assert all(not res["qa"][k] for k in ("text_only", "colour", "whitespace"))


def test_secondary_axis_ticks_keep_6pt_floor():
    fig, ax = _secondary()
    ax.child_axes[0].tick_params(labelsize=5)  # a second scale is main-axes text, not an inset
    assert any("5 pt < 6 pt" in m for m in qa.min_font(fig))


def test_right_side_tick_labels_checked():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    ax.yaxis.tick_right()
    ax.tick_params(labelsize=5)
    assert any("5 pt < 6 pt at ax0.tick" in m for m in qa.min_font(fig))
