"""S4: every marked panel is also exported standalone (PDF + SVG, composite size, no panel label)."""
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import pytest

from conftest import needs_scipilot
from figkit import export, panel, style
from figkit.provenance import Provenance

SIZE = (style.DOUBLE, 2.4)


def _pdf_size_in(path):
    try:
        from pypdf import PdfReader
        box = PdfReader(str(path)).pages[0].mediabox
        return float(box.width) / 72, float(box.height) / 72
    except ImportError:
        m = re.search(rb"/MediaBox\s*\[\s*([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s*\]",
                      Path(path).read_bytes())
        x0, y0, x1, y1 = map(float, m.groups())
        return (x1 - x0) / 72, (y1 - y0) / 72


def _svg_text(path):
    return re.findall(r"<text[^>]*>([^<]*)</text>", Path(path).read_text(encoding="utf-8"))


def _fig(cfg, mark=True):
    style.apply(cfg)
    fig, axes = plt.subplots(1, 2, figsize=SIZE, layout="constrained")
    for k, ax in enumerate(axes):
        ax.plot([0, 1, 2], [0, 1 + k, 0])
        ax.set_xlabel("time (h)"); ax.set_ylabel("signal")
        if mark:
            panel.mark_panel(ax, "ab"[k])
    fig.canvas.draw()
    labs = panel.label_panels(fig, axes, ["a", "b"], cfg=cfg)
    return fig, axes, labs


@needs_scipilot
def test_s4_panels_exported_without_labels(project):
    fig, axes, labs = _fig(project)
    assert all(panel.is_panel_label(t) for t in labs)
    res = export.save(fig, "f1", Provenance("f1"), size=SIZE, cfg=project)
    d = project.out_dir / "panels" / "f1"
    recs = res["panels"]
    assert [r["id"] for r in recs] == ["a", "b"]
    for r in recs:
        pdf, svg = Path(r["pdf"]), Path(r["svg"])
        assert pdf == d / f"f1_{r['id']}.pdf" and svg == d / f"f1_{r['id']}.svg"
        assert pdf.stat().st_size > 0 and svg.stat().st_size > 0
        w, h = _pdf_size_in(pdf)
        assert abs(w - r["size_in"][0]) < 0.02 and abs(h - r["size_in"][1]) < 0.02
        assert r["size_in"][0] < SIZE[0] * 0.75  # one panel, not the whole composite
        texts = [t.strip() for t in _svg_text(svg)]
        assert "a" not in texts and "b" not in texts
        assert "signal" in texts  # svg.fonttype none -> text kept as text
        assert b"/FontFile2" in pdf.read_bytes()  # TrueType (fonttype 42) embedded
    comp = [t.strip() for t in _svg_text(project.out_dir / "figures" / "main" / "f1.svg")]
    assert "a" in comp and "b" in comp
    assert all(t.get_visible() for t in labs) and all(a.get_visible() for a in axes)
    src = json.loads((project.out_dir / "figures" / "main" / "f1.source.json").read_text("utf-8"))
    assert [p["id"] for p in src["values"]["panels"]] == ["a", "b"]


def test_s4_unmarked_multi_axes_raises_before_export(project, monkeypatch):
    from test_core import _fake_tools
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig, _axes, _labs = _fig(project, mark=False)
    with pytest.raises(RuntimeError, match="none marked with panel.mark_panel"):
        export.save(fig, "f2", Provenance("f2"), size=SIZE, cfg=project)
    assert "export_kw" not in seen
    assert not (project.out_dir / "figures").exists() and not (project.out_dir / "panels").exists()


def test_s4_unmarked_add_axes_raises(project, monkeypatch):
    from test_core import _fake_tools
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig = plt.figure(figsize=(3, 2))
    ax = fig.add_axes([0.2, 0.2, 0.7, 0.7]); ax.plot([0, 1, 2], [0, 1, 0])
    with pytest.raises(RuntimeError, match="S4 FAIL"):
        export.save(fig, "f5", Provenance("f5"), cfg=project)
    assert "export_kw" not in seen


def test_s4_panels_none_rejected_for_multi_axes(project, monkeypatch):
    from test_core import _fake_tools
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig, _axes, _labs = _fig(project, mark=False)
    with pytest.raises(RuntimeError, match="only for single-panel"):
        export.save(fig, "f6", Provenance("f6"), size=SIZE, cfg=project, panels="none")
    with pytest.raises(ValueError, match="panels must be"):
        export.save(fig, "f6", Provenance("f6"), size=SIZE, cfg=project, panels="all")
    assert "export_kw" not in seen


def test_s4_panels_none_with_marked_axes_rejected(project, monkeypatch):
    from test_core import _fake_tools
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig, ax = plt.subplots(figsize=(3, 2)); ax.plot([0, 1, 2], [0, 1, 0])
    panel.mark_panel(ax, "a")
    with pytest.raises(RuntimeError, match="panels='none' but"):
        export.save(fig, "f7", Provenance("f7"), cfg=project, panels="none")


@needs_scipilot
def test_s4_panels_none_single_axes_exports_a(project):
    style.apply(project)
    fig, ax = plt.subplots(figsize=(style.SINGLE, 2.2), layout="constrained")
    ax.plot([0, 1, 2], [0, 1, 0]); ax.set_xlabel("time (h)"); ax.set_ylabel("signal")
    res = export.save(fig, "f2", Provenance("f2"), size=(style.SINGLE, 2.2), cfg=project, panels="none")
    d = project.out_dir / "panels" / "f2"
    assert sorted(p.name for p in d.iterdir()) == ["f2_a.pdf", "f2_a.svg"]
    (rec,) = res["panels"]
    assert rec["id"] == "a" and Path(rec["pdf"]) == d / "f2_a.pdf"
    w, h = _pdf_size_in(d / "f2_a.pdf")
    assert abs(w - style.SINGLE) < 0.02 and abs(h - 2.2) < 0.02
    assert "signal" in [t.strip() for t in _svg_text(d / "f2_a.svg")]
    assert b"/FontFile2" in (d / "f2_a.pdf").read_bytes()
    src = json.loads((project.out_dir / "figures" / "main" / "f2.source.json").read_text("utf-8"))
    assert src["values"]["panels"][0]["pdf"] == "out/panels/f2/f2_a.pdf"


@needs_scipilot
def test_s4_missing_panel_pdf_raises(project, monkeypatch):
    fig, axes, labs = _fig(project)
    real = fig.savefig

    def flaky(path, *a, **k):
        if str(path).endswith("f3_b.pdf"):
            return None  # silently writes nothing
        return real(path, *a, **k)

    monkeypatch.setattr(fig, "savefig", flaky)
    with pytest.raises(RuntimeError, match="panel b not written"):
        export.save(fig, "f3", Provenance("f3"), size=SIZE, cfg=project)
    assert all(t.get_visible() for t in labs) and all(a.get_visible() for a in axes)


def test_hand_placed_bold_labels_recognised():
    fig, axes = plt.subplots(1, 2, figsize=SIZE)
    t1 = axes[0].text(-0.15, 1.05, "a", transform=axes[0].transAxes, fontweight="bold")
    x0, _, _, y1 = axes[1].get_position().extents
    t2 = fig.text(x0 - 0.03, y1 + 0.02, "b2", fontweight="bold")
    ann = axes[1].annotate("c", xy=(0, 1), xycoords=axes[1].transAxes, xytext=(-8, 4),
                           textcoords="offset points", fontweight="bold")
    assert panel.is_panel_label(t1) and panel.is_panel_label(t2) and panel.is_panel_label(ann)
    # not labels: not bold, inside the data area, a word, or a figure text far from any axes corner
    assert not panel.is_panel_label(axes[0].text(-0.15, 1.05, "a", transform=axes[0].transAxes))
    assert not panel.is_panel_label(axes[0].text(0.5, 0.5, "a", transform=axes[0].transAxes, fontweight="bold"))
    assert not panel.is_panel_label(axes[0].text(0.5, 0.5, "a", fontweight="bold"))  # data coords
    assert not panel.is_panel_label(axes[0].text(-0.1, 1.05, "ns", transform=axes[0].transAxes, fontweight="bold"))
    assert not panel.is_panel_label(fig.text(0.5, 0.02, "x", fontweight="bold"))
    assert set(panel.panel_labels(fig)) == {t1, t2, ann}


def test_panel_export_failure_removes_composite(project, monkeypatch):
    from test_core import _fake_tools
    seen = {}
    _fake_tools(monkeypatch, seen)
    written = []

    def fake_export(fig, base, **k):
        files = [base + ext for ext in (".pdf", ".svg", ".png", "_grayscale.png")]
        Path(base).parent.mkdir(parents=True, exist_ok=True)
        for f in files:
            Path(f).write_bytes(b"x")
        written.extend(files)
        return files

    monkeypatch.setattr(export, "export_figure", fake_export)

    def boom(*a, **k):
        raise RuntimeError("panel b not written")

    monkeypatch.setattr(export.panel, "export_panels", boom)
    fig, ax = plt.subplots(figsize=(3, 2)); ax.plot([0, 1, 2], [0, 1, 0])
    panel.mark_panel(ax, "a")
    with pytest.raises(RuntimeError, match="panel b not written"):
        export.save(fig, "f4", Provenance("f4"), cfg=project)
    assert written and not any(Path(f).exists() for f in written)
    assert not (project.out_dir / "figures" / "main" / "f4.source.json").exists()


def test_s4_panels_none_twinx_is_one_panel(project, monkeypatch):
    from test_core import _fake_tools
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig, ax = plt.subplots(figsize=(3, 2), layout="constrained")
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    tw = ax.twinx()
    tw.plot([0, 1, 2], [3, 1, 2], color=style.DATA_CYCLE[1])
    monkeypatch.setattr(export.panel, "export_whole", lambda *a, **k: [])
    export.save(fig, "tw", Provenance("tw"), cfg=project, panels="none")
    assert "export_kw" in seen


def test_s4_panels_none_two_independent_axes_raises(project, monkeypatch):
    from test_core import _fake_tools
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig, (a, b) = plt.subplots(1, 2, figsize=(4, 2), layout="constrained")
    a.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    b.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[1])
    with pytest.raises(RuntimeError, match="only for single-panel"):
        export.save(fig, "ind", Provenance("ind"), cfg=project, panels="none")
    assert "export_kw" not in seen


def test_s4_marked_twinx_exports_twin_with_panel(project, monkeypatch):
    """A marked axes' twin travels with it (no separate mark needed, not hidden in the standalone)."""
    fig, ax = plt.subplots(figsize=(3, 2), layout="constrained")
    ax.plot([0, 1, 2], [0, 1, 0], color=style.DATA_CYCLE[0])
    tw = ax.twinx(); tw.plot([0, 1, 2], [3, 1, 2], color=style.DATA_CYCLE[1])
    panel.mark_panel(ax, "a")
    assert tw in panel._members(ax)
