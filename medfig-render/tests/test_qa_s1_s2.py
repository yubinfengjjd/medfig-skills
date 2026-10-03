"""S1 whitespace audit, S2 text-only panel check, layout.image_width_ratios (synthetic figures only)."""
import matplotlib.pyplot as plt
import numpy as np
import pytest

from test_core import _fake_tools
from figkit import export, layout, panel, qa
from figkit.provenance import Provenance


def _img(h, w):
    return np.random.default_rng(0).random((h, w))


def _letterboxed():
    # portrait image in a square cell: aspect='equal' leaves blank bars left and right
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.imshow(_img(300, 100)); ax.set_axis_off()
    return fig


def _mixed_equal_columns(ratios=None):
    fig, axes = plt.subplots(1, 2, figsize=(4, 1.5), gridspec_kw={"width_ratios": ratios})
    for ax, shp in zip(axes, [(300, 100), (100, 300)]):
        ax.imshow(_img(*shp)); ax.set_axis_off()
    return fig


def _text_only():
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.text(0.5, 0.5, "n = 12", ha="center"); ax.set_axis_off()
    return fig


def _line():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1, 2], [0, 1, 0]); ax.set_xlabel("x"); ax.set_ylabel("y")
    return fig


def test_image_width_ratios_proportional_to_w_over_h():
    assert layout.image_width_ratios([(300, 100), (100, 300), (50, 50)]) == pytest.approx([1 / 3, 3, 1])
    with pytest.raises(ValueError):
        layout.image_width_ratios([(0, 10)])


def test_whitespace_flags_letterboxed_image():
    msgs = qa.whitespace_audit(_letterboxed())
    assert len(msgs) == 1 and "left+right blank" in msgs[0] and "> 15%" in msgs[0]


def test_whitespace_flags_equal_columns_with_mixed_aspect():
    msgs = qa.whitespace_audit(_mixed_equal_columns())
    assert len(msgs) == 1 and msgs[0].startswith("whitespace ax0")


def test_whitespace_clean_with_image_width_ratios():
    fig = _mixed_equal_columns(layout.image_width_ratios([(300, 100), (100, 300)]))
    assert qa.whitespace_audit(fig) == []


def test_whitespace_clean_line_plot_and_skips_colorbar_and_aux():
    assert qa.whitespace_audit(_line()) == []
    fig, ax = plt.subplots(figsize=(3, 2))
    im = ax.imshow(_img(100, 150), aspect="auto"); fig.colorbar(im, ax=ax)
    assert qa.whitespace_audit(fig) == []
    fig = _letterboxed(); fig.axes[0]._figkit_aux = True
    assert qa.whitespace_audit(fig) == []


def test_text_only_panel_flagged_and_clean_cases():
    assert qa.text_only_panel(_text_only()) == ["text-only panel ax0"]
    assert qa.text_only_panel(_line()) == []
    assert qa.text_only_panel(_letterboxed()) == []
    fig, ax = plt.subplots(figsize=(2, 2)); ax.bar([0, 1], [1, 2]); ax.set_title("bars")
    assert qa.text_only_panel(fig) == []
    fig, ax = plt.subplots(figsize=(2, 2)); ax.scatter([0, 1], [0, 1]); ax.text(0, 0, "a")
    assert qa.text_only_panel(fig) == []
    fig, ax = plt.subplots(figsize=(2, 2)); ax.plot([0], [0]); ax.text(0, 0, "a")
    assert qa.text_only_panel(fig) == ["text-only panel ax0"]  # a single-point line is not data
    fig, ax = plt.subplots(figsize=(2, 2)); ax.set_axis_off()  # empty, no text: not text-only
    assert qa.text_only_panel(fig) == []
    fig = _text_only(); fig.axes[0]._figkit_aux = True
    assert qa.text_only_panel(fig) == []


@pytest.mark.parametrize("make,key", [(_letterboxed, "whitespace"), (_mixed_equal_columns, "whitespace"),
                                      (_text_only, "text_only")])
def test_save_raises_before_export(project, monkeypatch, make, key):
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig = make()
    with pytest.raises(RuntimeError, match=f"QA failed[\s\S]*{key}="):
        export.save(fig, "t", Provenance("t"), cfg=project)
    assert "export_kw" not in seen
    assert not (project.out_dir / "figures").exists()


def test_save_passes_with_width_ratios(project, monkeypatch):
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig = _mixed_equal_columns(layout.image_width_ratios([(300, 100), (100, 300)]))
    for pid, ax in zip("ab", fig.axes):
        panel.mark_panel(ax, pid)
    res = export.save(fig, "t", Provenance("t"), cfg=project)
    assert res["qa"]["whitespace"] == [] and res["qa"]["text_only"] == []


def _constrained(ratios):
    fig, axes = plt.subplots(1, 2, figsize=(4, 1.5), layout="constrained", gridspec_kw={"width_ratios": ratios})
    for ax, shp in zip(axes, [(300, 100), (100, 300)]):
        ax.imshow(_img(*shp)); ax.set_axis_off()
    return fig


def test_whitespace_constrained_layout_clean_with_ratios():
    assert qa.whitespace_audit(_constrained(layout.image_width_ratios([(300, 100), (100, 300)]))) == []


def test_whitespace_constrained_layout_flags_letterboxed():
    msgs = qa.whitespace_audit(_constrained([1, 1]))
    assert msgs and all("left+right blank" in m for m in msgs)
