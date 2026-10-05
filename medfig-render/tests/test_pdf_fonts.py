"""Embedded PDF fonts carry their real PostScript name, no subset tag (Adobe Illustrator opens ``ABCDEF+ArialMT``
as a missing font instead of matching the installed Arial)."""
import matplotlib as mpl
import matplotlib.pyplot as plt
import pytest

from conftest import needs_scipilot
from figkit import export, panel, style
from figkit.provenance import Provenance


def _text_fig():
    fig, ax = plt.subplots(figsize=(2, 1.5))
    ax.plot([0, 1], [0, 1])
    ax.set_xlabel("Time (s)")
    ax.set_title("Bold", fontweight="bold")
    return fig, ax


def _save(fig, p):
    with mpl.rc_context({"pdf.fonttype": 42}):
        fig.savefig(p)


def test_plain_matplotlib_tags_subset_fonts(tmp_path):
    """Documents the backend behaviour the patch guards against (if this ever fails, matplotlib changed)."""
    fig, _ = _text_fig()
    p = tmp_path / "plain.pdf"
    _save(fig, p)
    issues = export.pdf_font_issues(p)
    assert issues and "Illustrator" in issues[0]


def test_pdf_plain_font_names_patch(tmp_path):
    fig, _ = _text_fig()
    p = tmp_path / "plain_names.pdf"
    with export.pdf_plain_font_names():
        _save(fig, p)
    data = p.read_bytes()
    assert export.pdf_font_issues(p) == []
    assert b"/FontFile2" in data  # glyphs still embedded (fonttype 42)
    q = tmp_path / "after.pdf"
    _save(fig, q)  # patch is scoped to the block
    assert export.pdf_font_issues(q)


def test_pdf_plain_font_names_text_extractable(tmp_path):
    from pypdf import PdfReader

    fig, _ = _text_fig()
    p = tmp_path / "t.pdf"
    with export.pdf_illustrator_safe():
        _save(fig, p)
    assert "Time (s)" in PdfReader(str(p)).pages[0].extract_text()


def test_pdf_font_issues_ignores_non_pdf(tmp_path):
    p = tmp_path / "x.pdf"
    p.write_bytes(b"stand-in")
    assert export.pdf_font_issues(p) == []


@needs_scipilot
def test_save_exports_untagged_font_pdfs(project):
    style.apply(project)
    fig, ax = plt.subplots(figsize=(2.4, 2.2), layout="constrained")
    ax.plot([0, 1], [0, 1])
    ax.set_xlabel("Time (s)"); ax.set_ylabel("Signal")
    panel.mark_panel(ax, "a")
    res = export.save(fig, "ln", Provenance("ln"), size=(2.4, 2.2), cfg=project, panels="marked")
    pdfs = [f for f in res["files"] if f.endswith(".pdf")] + [r["pdf"] for r in res["panels"]]
    assert pdfs
    for f in pdfs:
        assert export.pdf_font_issues(f) == [], f


@needs_scipilot
def test_apply_puts_arial_before_helvetica(project):
    from matplotlib import font_manager

    if "Arial" not in {f.name for f in font_manager.fontManager.ttflist}:
        pytest.skip("Arial not installed")
    style.apply(project)
    fams = list(mpl.rcParams["font.sans-serif"])
    if "Helvetica" in fams:
        assert fams.index("Arial") < fams.index("Helvetica")


def _arial():
    from matplotlib import font_manager
    if "Arial" not in {f.name for f in font_manager.fontManager.ttflist}:
        pytest.skip("Arial not installed")
    return {"font.family": "sans-serif", "font.sans-serif": ["Arial"]}


def test_mathtext_uses_body_font(tmp_path):
    """style.RC keeps mathtext ($P_{BH}$, ×10$^{-6}$) in the body sans font: no DejaVu next to Arial."""
    from figkit.style import RC
    with mpl.rc_context({**RC, **_arial()}):
        fig, ax = plt.subplots(figsize=(2, 1))
        ax.text(0.1, 0.5, r"Seed $P_{\mathrm{BH}}$ $P$ ×10$^{" + "−" + r"6}$")
        p = tmp_path / "m.pdf"
        with export.pdf_illustrator_safe():
            fig.savefig(p)
    assert export.pdf_font_issues(p) == []
    assert b"DejaVu" not in p.read_bytes()


def test_pdf_font_issues_flags_fallback_fonts(tmp_path):
    with mpl.rc_context({"pdf.fonttype": 42, "mathtext.fontset": "dejavusans", **_arial()}):
        fig, ax = plt.subplots(figsize=(2, 1))
        ax.text(0.1, 0.5, r"Seed $P_{\mathrm{BH}}$")
        p = tmp_path / "dv.pdf"
        with export.pdf_illustrator_safe():
            fig.savefig(p)
    assert any("fallback font embedded" in i and "DejaVu" in i for i in export.pdf_font_issues(p))
