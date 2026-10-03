"""Regression tests for the recurring figure defects B1-B23 and the panel rules S1-S5 (synthetic data only).

Each automatable defect has at least one test named ``test_B<nn>_<slug>`` that shows the defect is
caught (a QA check reports it / a function raises) or prevented (the library cannot produce it).

B-id  status
----  ------------------------------------------------------------------------------------------------
B01   tested by test_B01_image_aspect_equal_never_stretched, test_B01_native_shape_kept
B02   tested by test_B02_cam_requires_shared_scale, test_B02_noise_level_cam_not_painted
B03   tested by test_B03_negative_map_transparent_with_negative_shared_vmin
B04   tested by test_B04_hdr_contours_closed, test_B04_hdr_threshold_from_samples_and_padding
B05   tested by test_B05_5pt_body_text_flagged, test_B05_library_font_defaults_meet_floor
B06   tested by test_B06_qa_runs_at_final_size
B07   tested by test_B07_legend_covering_scatter_flagged, test_B07_legend_box_joins_text_overlap
B08   tested by test_B08_waterfall_nan_raises, test_B08_waterfall_open_raises
B09   tested by test_B09_zero_count_confusion_row_absent
B10   tested by test_B10_n_derived_from_data (partial: the library exposes data-derived n;
      whether a caption still types n by hand is a review item)
B11   not automatable: blanket statements over sets of tests live in project caption code; figkit has
      no helper to test (rule "gate on the falsifying extreme" goes to lessons / review checklist)
B12   tested by test_B12_ascii_hyphen_minus_flagged, test_B12_style_apply_true_minus_ticks,
      test_B12_heat_cells_true_minus
B13   tested by test_B13_masked_cells_hatched_not_zero (partial: hatching of not-estimable /
      structural cells; asserting "zero by construction" needs the project's run record)
B14   not automatable: methods claims in captions must be traced to the current run config (semantic)
B15   not automatable: overlap between cohorts is a study fact computed in the project's figure script
B16   not automatable: keeping analysis families apart is a planning / wording rule
B17   tested by test_B17_classes_present_derived_from_data
B18   not automatable in figkit: reconciling n of one cohort across figures needs the project ledger.
      Automatable later (orchestrate review script): over all *.source.json, the same input path +
      sha256 must give the same rows, and differing values.n_* for one cohort are flagged
B19   not automatable: brief vs spec conflicts are a review process rule
B20   not automatable: reserving palettes per semantic is a planning decision; the grey half of the
      old rule is superseded by S3 (see test_S3_*). Automatable later: grayscale luminance contrast
      between the hatch colour and the cmap colour under absent / n/a cells (confusion, heat.annotated)
B21   tested by test_B21_hexbin_not_false_positive, test_B21_identity_pseudo_offsets_skipped,
      test_B21_clipped_points_ignored, test_B21_hidden_text_ignored, test_B21_panel_labels_clear_ticks
B22   tested by test_B22_axis_off_ticks_not_audited, test_B22_inset_fonts_still_checked
B23   not automatable: process defects (gitignored outputs, lost briefs, silent agents) are handled
      by the orchestration workflow, not by figure code
S1    tested by test_S1_letterbox_whitespace_flagged, test_S1_width_ratios_clean
S2    tested by test_S2_text_only_panel_flagged
S3    tested by test_S3_black_grey_data_flagged, test_S3_grey_cmap_refused
S4    tested by test_S4_per_panel_export_written
S5    tested by test_S5_roc_mean_sd
"""
import inspect
import re

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from conftest import needs_scipilot
from test_core import _fake_tools
from figkit import export, layout, panel, qa, style
from figkit.panels import confusion, curves, dist, heat, imaging
from figkit.provenance import Provenance

CLASSES = ["Alpha", "Beta", "Gamma"]


def _bscan(H=64, W=256, seed=0):
    rng = np.random.default_rng(seed)
    return np.clip(rng.normal(0.4, 0.1, (H, W)) + np.linspace(0, 0.3, H)[:, None], 0, 1)


def _counts(zero_class=None, seed=0):
    rng = np.random.default_rng(seed)
    rows = [(t, p, 0 if t == zero_class else int(rng.integers(1, 50))) for t in CLASSES for p in CLASSES]
    return pd.DataFrame(rows, columns=["truth", "prediction", "count"])


# ---------------------------------------------------------------- B1 stretched images
def test_B01_image_aspect_equal_never_stretched():
    # a wide, short axes cell: aspect="auto" would stretch the B-scan to fill it
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.set_aspect("auto")
    imaging.bscan_with_boundaries(ax, _bscan(), np.full((2, 16), 0.5))
    fig.canvas.draw()
    assert ax.get_aspect() == 1.0
    ext = ax.images[0].get_window_extent(fig.canvas.get_renderer())
    assert ext.width / ext.height == pytest.approx(256 / 64, rel=0.02)  # displayed at native aspect


def test_B01_native_shape_kept():
    raw = _bscan(50, 130)
    fig, ax = plt.subplots()
    imaging.concept_map(ax, raw, np.ones((5, 13)), vmin=0, vmax=1)
    assert ax.images[0].get_array().shape == raw.shape
    assert ax._anchor_upsampled.shape == raw.shape
    assert ax._anchor_resampled == ((5, 13), (50, 130), "bilinear")  # resampling recorded for the caption


# ---------------------------------------------------------------- B2 CAM noise normalised as signal
def test_B02_cam_requires_shared_scale():
    raw, cam = _bscan(), np.random.default_rng(0).random((8, 32)) * 1e-12
    for vmin, vmax in [(None, None), (0, None), (1e-12, 1e-12), (0, np.nan)]:
        with pytest.raises(ValueError, match="shared scale"):
            imaging.concept_map(plt.subplots()[1], raw, cam, vmin=vmin, vmax=vmax)


def test_B02_noise_level_cam_not_painted():
    raw = _bscan()
    signal = np.random.default_rng(1).random((8, 32))
    noise = np.random.default_rng(2).random((8, 32)) * 1e-12
    vmin, vmax = 0.0, float(max(signal.max(), noise.max()))  # one scale over every case shown
    fig, (a, b) = plt.subplots(1, 2)
    imaging.concept_map(a, raw, signal, vmin, vmax)
    imaging.concept_map(b, raw, noise, vmin, vmax)
    assert (a._anchor_alpha > 0).any()
    assert (b._anchor_alpha == 0).all()  # per-image min-max would have painted this noise fully
    assert (a._anchor_mappable.norm.vmin, a._anchor_mappable.norm.vmax) == \
           (b._anchor_mappable.norm.vmin, b._anchor_mappable.norm.vmax)


# ---------------------------------------------------------------- B3 negative values as evidence
def test_B03_negative_map_transparent_with_negative_shared_vmin():
    # -0.2 on the shared [-0.5, 1] scale normalises to 0.2 >= MAP_THRESHOLD (0.15): the threshold alone
    # would paint it; only the "value <= 0 is transparent" rule keeps the negative map off the image
    vmin, vmax, v = -0.5, 1.0, -0.2
    assert (v - vmin) / (vmax - vmin) >= imaging.MAP_THRESHOLD
    fig, ax = plt.subplots()
    imaging.concept_map(ax, _bscan(), np.full((8, 32), v), vmin=vmin, vmax=vmax)
    assert (ax._anchor_alpha == 0).all()
    assert ax._anchor_threshold == imaging.MAP_THRESHOLD  # recorded for provenance


# ---------------------------------------------------------------- B4 HDR contours
def _hdr_polys(ax):
    return [poly for c in ax.collections for p in c.get_paths() for poly in p.to_polygons(closed_only=False)]


def test_B04_hdr_contours_closed():
    xy = np.random.default_rng(3).normal(size=(1500, 2)) * [1.0, 3.0]
    fig, ax = plt.subplots()
    dist.hdr_contour(ax, xy)
    gx, gy = ax._anchor_grid
    polys = _hdr_polys(ax)
    assert polys
    for poly in polys:
        assert np.allclose(poly[0], poly[-1]), "HDR contour opened at the grid edge"
        assert gx[0] < poly[:, 0].min() and poly[:, 0].max() < gx[-1]
        assert gy[0] < poly[:, 1].min() and poly[:, 1].max() < gy[-1]


def test_B04_hdr_threshold_from_samples_and_padding():
    from scipy.stats import gaussian_kde
    xy = np.random.default_rng(4).normal(size=(600, 2))
    fig, ax = plt.subplots()
    lv = dist.hdr_contour(ax, xy, levels=(0.5, 0.9))._anchor_levels
    dens = gaussian_kde(xy.T)(xy.T)
    assert np.allclose(lv, [np.quantile(dens, 0.5), np.quantile(dens, 0.1)])
    with pytest.raises(ValueError, match="pad_sd"):
        dist.hdr_contour(plt.subplots()[1], xy, pad_sd=0.15)


# ---------------------------------------------------------------- B5 fonts below the floor
def test_B05_5pt_body_text_flagged():
    fig, ax = plt.subplots(figsize=(2.5, 2))
    ax.plot([0, 1, 2], [0, 1, 0])
    assert qa.min_font(fig) == []
    ax.text(1, 0.5, "no cases", fontsize=5)
    msgs = qa.min_font(fig)
    assert len(msgs) == 1 and "5 pt" in msgs[0] and "no cases" in msgs[0]


def test_B05_library_font_defaults_meet_floor():
    for fn in (confusion.matrix, confusion.colourbar, heat.annotated):
        default = inspect.signature(fn).parameters["fontsize"].default
        assert default >= style.MIN_FONT_PT, fn.__name__
    for k in ("font.size", "xtick.labelsize", "ytick.labelsize", "legend.fontsize"):
        assert float(style.RC[k]) >= style.MIN_FONT_PT
    fig, ax = plt.subplots(figsize=(2.2, 2.2), layout="constrained")
    confusion.matrix(ax, _counts("Gamma"), CLASSES, tick_labels=["A", "B", "G"])
    assert qa.min_font(fig) == []


# ---------------------------------------------------------------- B6 QA at the wrong size
def test_B06_qa_runs_at_final_size(project, monkeypatch):
    seen = {}
    _fake_tools(monkeypatch, seen)
    # two labels far apart on a big canvas; they collide once the figure is shrunk to its final size
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    ax.tick_params(labelsize=6)
    ax.text(0.05, 0.5, "Left label text", transform=ax.transAxes, fontsize=6)
    ax.text(0.30, 0.5, "Right label text", transform=ax.transAxes, fontsize=6)
    assert not any("overlap" in m for m in qa.geometry_audit(fig))  # clean at the drawing size
    with pytest.raises(RuntimeError, match="overlap"):
        export.save(fig, "t", Provenance("t"), size=(1.6, 1.2), cfg=project)
    assert "export_kw" not in seen


# ---------------------------------------------------------------- B7 legend covers data
def test_B07_legend_covering_scatter_flagged():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.scatter([0.05, 0.5], [0.95, 0.5], color=style.DATA_CYCLE[0], label="cases")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(loc="upper left")
    assert any("legend covers data" in m for m in qa.geometry_audit(fig))


def test_B07_legend_box_joins_text_overlap():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1], [0, 1], label="trend")
    ax.legend(loc="upper right")
    ax.text(0.97, 0.93, "NOTE", transform=ax.transAxes, ha="right")
    assert any("overlap" in m and "<legend>" in m for m in qa.geometry_audit(fig))


# ---------------------------------------------------------------- B8 NaN passes closure checks
@pytest.mark.parametrize("start,contribs,end", [
    (0.0, {"a": 1.0, "b": np.nan}, 1.0),  # Series.sum() would skip the NaN and "close"
    (np.nan, {"a": 1.0}, 1.0),
    (0.0, {"a": 1.0}, np.nan)])
def test_B08_waterfall_nan_raises(start, contribs, end):
    with pytest.raises(ValueError, match="non-finite"):
        heat.waterfall(plt.subplots()[1], start, pd.Series(contribs), end)


def test_B08_waterfall_open_raises():
    with pytest.raises(ValueError, match="does not close"):
        heat.waterfall(plt.subplots()[1], 0.0, pd.Series({"a": 0.5, "b": 0.4}), 1.0)
    ax = heat.waterfall(plt.subplots()[1], 0.1, pd.Series({"a": 0.5, "b": 0.4}), 1.0)
    assert abs(ax._anchor_closure_error) < 1e-12  # recorded for provenance


# ---------------------------------------------------------------- B9 zero-count confusion rows
def test_B09_zero_count_confusion_row_absent():
    fig, ax = plt.subplots()
    confusion.matrix(ax, _counts("Beta"), CLASSES)  # no absent_rows passed: detected from the counts
    assert ax._anchor_absent == ["Beta"]
    assert np.isnan(ax._anchor_matrix[1]).all()
    assert [t.get_text() for t in ax.texts].count("absent") == 1
    assert len(ax.patches) == 1 and ax.patches[0].get_hatch() == "////"
    assert not any(t.get_text().startswith("0.0%") for t in ax.texts)  # never reads as 0 %


# ---------------------------------------------------------------- B10 hard-coded n
def test_B10_n_derived_from_data(project):
    from figkit import io
    df = _counts(seed=5)
    df.to_csv(project.data_root / "cc.csv", index=False)
    prov = Provenance("t")
    loaded = io.Reader(prov, project).csv("cc.csv")
    fig, ax = plt.subplots()
    confusion.matrix(ax, loaded, CLASSES)
    n = dict(zip(CLASSES, ax._anchor_counts.sum(1).astype(int)))
    independent = pd.read_csv(project.data_root / "cc.csv").groupby("truth")["count"].sum()
    assert n == {k: int(independent[k]) for k in CLASSES}
    assert prov.inputs[0]["rows"] == len(df)


# ---------------------------------------------------------------- B12 ASCII hyphen as minus
def test_B12_ascii_hyphen_minus_flagged():
    mpl.rcParams["axes.unicode_minus"] = False  # what the upstream style used to force
    fig, ax = plt.subplots(figsize=(2.5, 2))
    ax.plot([-10, 10], [-1.5, 1.5])
    assert qa.true_minus(fig)
    mpl.rcParams["axes.unicode_minus"] = True
    fig2, ax2 = plt.subplots(figsize=(2.5, 2))
    ax2.plot([-10, 10], [-1.5, 1.5]); ax2.set_xlabel("post-treatment change")
    assert qa.true_minus(fig2) == []


@needs_scipilot
def test_B12_style_apply_true_minus_ticks(project, tmp_path):
    style.apply(project)
    assert mpl.rcParams["axes.unicode_minus"] is True
    fig, ax = plt.subplots(figsize=(2.5, 2))
    ax.plot([-10, 10], [-1.5, 1.5])
    svg = tmp_path / "m.svg"
    fig.savefig(svg)
    text = svg.read_text(encoding="utf-8")
    assert "−" in text  # checked on the exported file, not on the script source
    assert not re.search(r">\s*-\d", text)


def test_B12_heat_cells_true_minus():
    fig, ax = plt.subplots()
    heat.annotated(ax, pd.DataFrame([[-0.25, 0.5]], columns=["x", "y"]), "RdBu_r", center=0)
    txt = [t.get_text() for t in ax.texts]
    assert "−0.25" in txt and not any(t.startswith("-") for t in txt)


# ---------------------------------------------------------------- B13 structural zeros
def test_B13_masked_cells_hatched_not_zero():
    M = pd.DataFrame([[0.0, 0.3], [0.2, 0.0]], index=["r1", "r2"], columns=["c1", "c2"])
    mask = pd.DataFrame([[True, False], [False, False]], index=M.index, columns=M.columns)
    fig, ax = plt.subplots()
    heat.annotated(ax, M, "viridis", hatch_mask=mask)
    assert np.isnan(ax._anchor_matrix[0, 0]) and ax._anchor_matrix[1, 1] == 0.0
    assert [p.get_hatch() for p in ax.patches] == ["////"]
    txt = [t.get_text() for t in ax.texts]
    assert txt.count("n/a") == 1 and txt.count("0.00") == 1  # the measured zero keeps its number


# ---------------------------------------------------------------- B17 classes present from data
def test_B17_classes_present_derived_from_data():
    counts = _counts("Gamma")
    fig, ax = plt.subplots()
    confusion.matrix(ax, counts, CLASSES)
    present = [c for c in CLASSES if c not in ax._anchor_absent]
    assert present == ["Alpha", "Beta"]  # a "3-class" claim would be contradicted by the data
    expected_absent = ["Gamma"]
    assert ax._anchor_absent == expected_absent
    with pytest.raises(ValueError, match="absent_rows"):
        confusion.matrix(plt.subplots()[1], counts, CLASSES, absent_rows=("Delta",))


# ---------------------------------------------------------------- B21 auditor false positives
def test_B21_hexbin_not_false_positive():
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.hexbin(rng.uniform(0.6, 1, 300), rng.uniform(0, 0.4, 300), gridsize=10, mincnt=1)
    ax.plot([], [], label="ref"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(loc="upper left")
    assert qa.geometry_audit(fig) == []


def test_B21_identity_pseudo_offsets_skipped():
    from matplotlib.collections import LineCollection
    fig, ax = plt.subplots(figsize=(3, 2))
    # the segment lies in the upper-right corner; its (0, 0) pseudo-offset + transData origin maps to the
    # centre of the view, which the centred legend covers -> an unskipped pseudo-offset is a false positive
    ax.add_collection(LineCollection([[(0.8, 0.8), (1.0, 1.0)]]))
    ax.plot([], [], label="reference"); ax.set_xlim(-1, 1); ax.set_ylim(-1, 1)
    leg = ax.legend(loc="center")
    fig.canvas.draw()
    lb = leg.get_window_extent(fig.canvas.get_renderer())
    x0, y0 = ax.transData.transform((0, 0))
    assert lb.x0 < x0 < lb.x1 and lb.y0 < y0 < lb.y1  # the pseudo-offset point is under the legend
    assert not any("legend covers data" in m for m in qa.geometry_audit(fig))


def test_B21_clipped_points_ignored():
    fig, ax = plt.subplots(figsize=(3, 2))
    # the point sits just right of the view, where the outside legend is drawn; it is clipped (never
    # drawn), so only view clipping keeps it from being reported as covered
    ax.scatter([1.3], [0.5], label="pt"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    leg = ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
    fig.subplots_adjust(right=0.6)
    fig.canvas.draw()
    lb = leg.get_window_extent(fig.canvas.get_renderer())
    px, py = ax.transData.transform((1.3, 0.5))
    assert lb.x0 < px < lb.x1 and lb.y0 < py < lb.y1  # unclipped, it would be inside the legend box
    assert not any("legend covers data" in m for m in qa.geometry_audit(fig))


def test_B21_hidden_text_ignored():
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.text(0.5, 0.5, "SHOWN", transform=ax.transAxes)
    ax.text(0.5, 0.5, "HIDDEN", transform=ax.transAxes).set_visible(False)
    assert qa.geometry_audit(fig) == []


@needs_scipilot
def test_B21_panel_labels_clear_ticks(project):
    style.apply(project)
    fig, axes = plt.subplots(1, 2, figsize=(style.DOUBLE, 2.2), layout="constrained")
    for ax in axes:
        ax.plot([0, 1, 2], [0, 1, 0]); ax.set_ylabel("value")
    fig.canvas.draw()
    panel.label_panels(fig, axes, ["a", "b"], cfg=project, x_offset_pt=-16)
    assert qa.geometry_audit(fig) == []  # tune the offset, keep the audit strict


# ---------------------------------------------------------------- B22 layout-engine traps
def test_B22_axis_off_ticks_not_audited():
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.imshow(_bscan(40, 40))
    ax.text(0.5, -0.02, "caption-like", transform=ax.transAxes, ha="center", va="top")
    fig.canvas.draw()  # populate the tick label texts first
    assert qa._tick_labels(ax), "tick labels must be non-empty before axis off"
    ax.set_axis_off()  # the texts stay populated but are no longer drawn
    assert any(t.label1.get_text() for t in ax.xaxis.get_major_ticks())
    assert qa._tick_labels(ax) == []  # only the axison guard removes them
    assert not any("overlap" in m for m in qa.geometry_audit(fig))


def test_B22_inset_fonts_still_checked():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1], [0, 1])
    ins = ax.inset_axes([0.55, 0.1, 0.4, 0.4])
    ins.plot([0, 1], [1, 0]); ins.tick_params(labelsize=4)
    assert any("inset" in m for m in qa.min_font(fig))


# ---------------------------------------------------------------- S1-S5 panel rules
def test_S1_letterbox_whitespace_flagged():
    fig2, ax2 = plt.subplots(figsize=(3, 3))
    ax2.imshow(_bscan(256, 64), cmap="gray"); ax2.set_axis_off()  # tall image: blank left + right
    assert any("left+right blank" in m for m in qa.whitespace_audit(fig2))


def test_S1_width_ratios_clean():
    shapes = [(64, 256), (64, 64)]
    fig, axes = plt.subplots(1, 2, figsize=(5, 1.0), layout="constrained",
                             gridspec_kw={"width_ratios": layout.image_width_ratios(shapes)})
    fig.get_layout_engine().set(w_pad=0, h_pad=0, wspace=0, hspace=0)
    for ax, (h, w) in zip(axes, shapes):
        imaging.raw_image(ax, _bscan(h, w))
    assert qa.whitespace_audit(fig) == []


def test_S2_text_only_panel_flagged():
    fig, (a, b) = plt.subplots(1, 2, figsize=(4, 2))
    a.plot([0, 1, 2], [0, 1, 0])
    b.text(0.5, 0.5, "AUC 0.81\nn = 120", ha="center"); b.set_axis_off()
    assert qa.text_only_panel(fig) == ["text-only panel ax1"]


@pytest.mark.parametrize("draw", [
    lambda ax: ax.plot([0, 1, 2], [0, 1, 0], color="black"),
    lambda ax: ax.bar([0, 1], [1, 2], color="#808080"),
    lambda ax: ax.scatter([0, 1], [0, 1], color="0.4"),
    lambda ax: ax.errorbar([0.5], [0], xerr=[[0.1], [0.1]], fmt="o", color="k")])
def test_S3_black_grey_data_flagged(draw):
    fig, ax = plt.subplots(figsize=(3, 2))
    draw(ax)
    ax.axhline(0.5, color=style.GREY)  # grey reference lines are fine
    assert any("achromatic data artist" in m for m in qa.colour_audit(fig))


def test_S3_grey_cmap_refused():
    with pytest.raises(ValueError, match="grey colormap"):
        heat.annotated(plt.subplots()[1], pd.DataFrame([[0.1, 0.2]]), "gray")
    fig, ax = plt.subplots()
    ax.imshow(np.random.default_rng(0).random((5, 5)), cmap="Greys")  # unmarked grey heat map
    assert qa.colour_audit(fig)


def test_S4_per_panel_export_written(tmp_path):
    fig, (a, b) = plt.subplots(1, 2, figsize=(5, 2), layout="constrained")
    a.plot([0, 1, 2], [0, 1, 0]); b.bar([0, 1], [1, 2])
    panel.mark_panel(a, "a"); panel.mark_panel(b, "b")
    lab = a.text(-0.2, 1.05, "a", transform=a.transAxes, fontweight="bold")
    recs = panel.export_panels(fig, "demo", tmp_path)
    assert [r["id"] for r in recs] == ["a", "b"]
    for r in recs:
        for k in ("pdf", "svg"):
            p = tmp_path / "panels" / "demo" / f"demo_{r['id']}.{k}"
            assert p.is_file() and p.stat().st_size > 0 and r[k] == str(p)
        assert 0 < r["size_in"][0] < 5
    svg_a = (tmp_path / "panels" / "demo" / "demo_a.svg").read_text(encoding="utf-8")
    assert ">a<" not in svg_a.replace(" ", "")  # panel label hidden in the standalone panel
    assert lab.get_visible()  # and restored in the composite


def test_S5_roc_mean_sd():
    rng = np.random.default_rng(7)
    runs = []
    for _ in range(5):
        y = rng.integers(0, 2, 150)
        runs.append((y, 1.2 * y + rng.normal(size=150)))
    fig, ax = plt.subplots(figsize=(2.4, 2.4), layout="constrained")
    curves.roc_mean_sd(ax, runs, "Model")
    aucs = [curves._auc(*curves.roc_points(y, s)) for y, s in runs]
    txt = ax.get_legend().get_texts()[0].get_text()
    assert txt == f"Model (AUC = {np.mean(aucs):.3f} ± {np.std(aucs, ddof=1):.3f})"
    assert ax.get_legend()._loc == 4 and ax.get_aspect() == 1.0
    assert ax.get_xlabel() == "1 − specificity"
    assert len(ax.collections) == 1  # ±SD band
    assert [l.get_linestyle() for l in ax.get_lines() if getattr(l, "_figkit_aux", False)] == ["--"]
    assert qa.colour_audit(fig) == []
    fig1, ax1 = plt.subplots()
    curves.roc_mean_sd(ax1, runs[:1], "Model")
    assert len(ax1.collections) == 0  # single run: no SD band
