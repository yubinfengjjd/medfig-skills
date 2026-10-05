"""PDF raster images are 8-bit DeviceRGB, never indexed palettes (Adobe Illustrator mis-renders palette images
when a PDF is embedded: heatmap cells wash out and white cell labels vanish)."""
import matplotlib.pyplot as plt
import numpy as np
import pytest

from conftest import needs_scipilot
from figkit import export, panel, style
from figkit.provenance import Provenance

SIZE = (2.4, 2.2)


def _heatmap_fig(cfg):
    style.apply(cfg)
    fig, ax = plt.subplots(figsize=SIZE, layout="constrained")
    m = np.array([[0.98, 0.01, 0.01], [0.04, 0.93, 0.03], [0.02, 0.01, 0.97]])  # few colours -> palette candidate
    ax.imshow(m, cmap="Blues", vmin=0, vmax=1)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{m[i, j]:.0%}", ha="center", va="center", color="white" if m[i, j] > 0.5 else "black")
    ax.set_xticks(range(3), ["N", "E", "D"]); ax.set_yticks(range(3), ["N", "E", "D"])
    ax.set_xlabel("Predicted"); ax.set_ylabel("True")
    return fig, ax


def test_plain_matplotlib_writes_palette_images(tmp_path):
    """Documents the backend behaviour the patch guards against (if this ever fails, matplotlib changed)."""
    fig, ax = plt.subplots()
    ax.imshow(np.eye(3), cmap="Blues")
    p = tmp_path / "plain.pdf"
    fig.savefig(p)
    assert any("/Indexed" in m for m in export.pdf_image_issues(p))


def test_pdf_rgb_images_patch(tmp_path):
    fig, ax = plt.subplots()
    ax.imshow(np.eye(3), cmap="Blues")
    ax.imshow(np.ones((3, 3, 4)) * [0.2, 0.4, 0.8, 0.5], extent=(0, 1, 0, 1))  # with alpha -> SMask path
    p = tmp_path / "rgb.pdf"
    with export.pdf_rgb_images():
        fig.savefig(p)
    assert export.pdf_image_issues(p) == []
    q = tmp_path / "after.pdf"
    fig.savefig(q)  # patch is scoped to the block
    assert export.pdf_image_issues(q)


def test_pdf_rgb_images_keep_pixels(tmp_path):
    """The RGB path writes the same pixels the palette path encoded."""
    from pypdf import PdfReader

    fig = plt.figure(figsize=(1, 1), dpi=10)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
    ax.imshow(np.array([[0.0, 1.0], [0.5, 0.25]]), cmap="Blues", vmin=0, vmax=1, interpolation="nearest")
    p = tmp_path / "px.pdf"
    with export.pdf_rgb_images():
        fig.savefig(p, dpi=10)
    x = PdfReader(str(p)).pages[0]["/Resources"]["/XObject"]
    img = next(v.get_object() for v in x.values())
    assert img["/ColorSpace"] == "/DeviceRGB" and int(img["/BitsPerComponent"]) == 8
    px = np.asarray(img.decode_as_image().convert("RGB"))  # pypdf undoes the PNG predictor
    cm = plt.get_cmap("Blues")
    want = (np.array(cm(0.0)[:3]) * 255).round()
    assert np.abs(px[0, 0].astype(int) - want).max() <= 1


@needs_scipilot
def test_save_exports_rgb_only_pdfs(project):
    fig, ax = _heatmap_fig(project)
    panel.mark_panel(ax, "a")
    res = export.save(fig, "hm", Provenance("hm"), size=SIZE, cfg=project, panels="marked")
    pdfs = [f for f in res["files"] if f.endswith(".pdf")] + [r["pdf"] for r in res["panels"]]
    assert pdfs
    for f in pdfs:
        assert export.pdf_image_issues(f) == [], f


def test_pdf_image_issues_reports_palette(tmp_path):
    fig, ax = plt.subplots()
    ax.imshow(np.eye(3), cmap="Blues")
    p = tmp_path / "x.pdf"
    fig.savefig(p)
    issues = export.pdf_image_issues(p)
    assert issues and "Illustrator" in issues[0]
