"""Smoke tests for scipilot-medimg-figure-skill on synthetic images (no patient data).

Covers what medfig does not exercise: the JSON-spec image panel (render, self-check, export,
provenance), the "masks are never resized" rule, and the style / export / check helpers.
Run:  python -m pytest scipilot-medimg-figure-skill/tests -q -p no:cacheprovider
"""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


@pytest.fixture
def images(tmp_path):
    """A 128 x 192 grey 'B-scan' with a bright band, a label mask on the same grid, a CAM array."""
    h, w = 128, 192
    y = np.arange(h)[:, None]
    img = (40 + 160 * np.exp(-((y - 64) / 10.0) ** 2) * np.ones((1, w))).astype(np.uint8)
    Image.fromarray(img).save(tmp_path / "scan.png")
    mask = np.zeros((h, w), np.uint8)
    mask[58:70, 40:150] = 115
    Image.fromarray(mask).save(tmp_path / "mask.png")
    mask_small = np.zeros((h // 2, w // 2), np.uint8)
    Image.fromarray(mask_small).save(tmp_path / "mask_small.png")
    cam = np.zeros((h, w), np.float32)
    cam[50:80, 80:120] = 1.0
    np.savez(tmp_path / "arrays.npz", cam=cam)
    return tmp_path


def _spec(d, mask="mask.png"):
    return {
        "figure": {"journal": "nature", "width": "single", "name": "panel", "out_dir": str(d / "out"),
                   "panel_label": "a"},
        "grid": {"rows": ["Case 1"], "cols": ["B-scan", "Mask", "CAM"], "gap_mm": 1.0},
        "groups": {"g": {"intensity": {"mode": "percentile", "lo": 0.5, "hi": 99.5}}},
        "label_maps": {"m": {"source": "synthetic test", "ignore": [0],
                             "classes": {"115": {"name": "band", "color": "#F0E442"}}}},
        "cells": [
            {"row": 0, "col": 0, "group": "g", "image": str(d / "scan.png")},
            {"row": 0, "col": 1, "group": "g", "image": str(d / "scan.png"),
             "overlays": [{"type": "label_mask", "path": str(d / mask), "label_map": "m", "show": [115],
                           "draw": "contour"}]},
            {"row": 0, "col": 2, "group": "g", "image": str(d / "scan.png"),
             "overlays": [{"type": "heatmap", "path": str(d / "arrays.npz"), "key": "cam", "cmap": "magma",
                           "normalize": "per_image", "upsample": "bilinear", "alpha": 0.5}]},
        ],
    }


def test_image_panel_renders_and_exports(images):
    import image_panel
    res = image_panel.render(_spec(images))
    assert not [m for s, m in res.issues if s == "FAIL"], res.issues
    out = images / "out"
    for suffix in (".pdf", ".svg", ".png", "_grayscale.png", "_preview.png", ".qa.json",
                   ".provenance.json", ".caption_methods.md"):
        assert (out / f"panel{suffix}").is_file(), suffix
    prov = json.loads((out / "panel.provenance.json").read_text(encoding="utf-8"))
    assert "sha256" in json.dumps(prov)  # inputs are hashed for provenance
    plt.close("all")


def test_unnamed_mask_value_is_refused(images):
    """Class meanings are never guessed: a mask value without a name stops the render."""
    import image_panel
    spec = _spec(images)
    del spec["label_maps"]["m"]["ignore"]
    with pytest.raises(image_panel.SpecError, match="never guessed"):
        image_panel.render(spec, export=False)
    plt.close("all")


def test_mask_on_a_different_grid_is_refused(images):
    """Masks are never resized: a mask on another pixel grid stops the render."""
    import image_panel
    with pytest.raises(Exception, match="(?i)shape|size|grid|match"):
        image_panel.render(_spec(images, mask="mask_small.png"), export=False)
    plt.close("all")


def test_style_export_and_check(tmp_path):
    from check_figure import check_figure
    from export_figure import export_figure
    from setup_style import setup_style
    setup_style(journal="nature", lang="en")
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    ax.plot([0, 1, 2], [0, 1, 0.5], marker="o")
    ax.set_xlabel("x"); ax.set_ylabel("y")
    export_figure(fig, basename=str(tmp_path / "fig1"), formats=["pdf", "png"], size_inches=(3.5, 2.6), dpi=300)
    assert (tmp_path / "fig1.pdf").is_file() and (tmp_path / "fig1.png").is_file()
    issues, info = check_figure(str(tmp_path / "fig1.png"), min_dpi=300)
    assert not [i for i in issues if i[0] == "FAIL"], issues
    assert info["ext"] == "png"
    plt.close("all")


def test_visual_qa_and_profile(tmp_path):
    import pandas as pd
    from profile_data import profile_data
    from visual_qa import audit_layout, render_preview
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    ax.bar(["A", "B"], [1, 2])
    render_preview(fig, str(tmp_path / "p.png"))
    assert (tmp_path / "p.png").is_file()
    assert isinstance(audit_layout(fig), list)
    plt.close("all")
    df = pd.DataFrame({"group": ["a"] * 6 + ["b"] * 6, "value": np.linspace(0, 1, 12)})
    df.to_csv(tmp_path / "d.csv", index=False)
    rep = profile_data(str(tmp_path / "d.csv"), group_cols=["group"])
    assert rep is not None
