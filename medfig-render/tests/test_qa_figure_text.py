"""qa.figure_text_audit: figure text carries results and reading keys only. Free figure-level text,
caveats / disclaimers, cross-references and project code patterns ([qa] forbidden_patterns) fail export.
Synthetic figures only."""
import matplotlib.pyplot as plt
import pytest

from figkit import config, export, panel, qa, style
from figkit.provenance import Provenance

from test_core import _fake_tools, _write_toml


def _fig():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1], [0, 1], color=style.DATA_CYCLE[0], label="Model")
    ax.set_xlabel("Threshold"); ax.set_ylabel("Net benefit")
    return fig, ax


def test_clean_figure_passes():
    fig, ax = _fig()
    ax.legend(title="Filled = in set")  # reading key: allowed
    ax.text(0.1, 0.9, "n = 1,176", transform=ax.transAxes)
    assert qa.figure_text_audit(fig) == []


def test_free_figure_text_fails():
    fig, ax = _fig()
    fig.text(0.5, 0.01, "Research example only")
    hits = qa.figure_text_audit(fig)
    assert len(hits) == 1 and "figure-level text" in hits[0] and "Research example only" in hits[0]


def test_suptitle_fails_but_sup_axis_labels_and_panel_labels_pass():
    fig, ax = _fig()
    fig.supxlabel("Shared x"); fig.supylabel("Shared y")
    t = fig.text(0.01, 0.98, "a", fontweight="bold"); t._figkit_panel_label = True
    assert panel.is_panel_label(t)
    assert qa.figure_text_audit(fig) == []
    fig.suptitle("Overview of results")
    assert any("figure-level text" in h for h in qa.figure_text_audit(fig))


@pytest.mark.parametrize("text", [
    "Illustrative research example", "not a clinical report", "no treatment recommendation",
    "(not used for Table 6 coverage)", "residual path = 0 by construction", "Descriptive only",
    "band: seed min–max, not a CI", "retrospective", "for research use only", "exploratory analysis",
])
def test_caveats_fail_anywhere_in_axes(text):
    fig, ax = _fig()
    ax.set_title(text)
    assert qa.figure_text_audit(fig), text


@pytest.mark.parametrize("text,hit", [
    ("see Table 6", True), ("cf. Fig. 3b", True), ("Supplementary Fig. S2", True), ("Figure 2", True),
    ("Extended Data Fig. 1", True), ("Table of counts", False), ("Fig tree", False), ("S2 segment", False),
])
def test_cross_references(text, hit):
    fig, ax = _fig()
    ax.set_xlabel(text)
    assert bool(qa.figure_text_audit(fig)) is hit, text


def test_legend_and_tick_text_are_checked():
    fig, ax = _fig()
    ax.legend(["Model (not used for Table 6)"])
    assert any("cross-reference" in h for h in qa.figure_text_audit(fig))
    fig, ax = _fig()
    ax.set_xticks([0, 1], ["Seen", "Illustrative"])
    assert any("caveat" in h for h in qa.figure_text_audit(fig))


def test_project_patterns_word_boundary(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\n[qa]\n'
                                  'forbidden_patterns = ["\\\\bE[12]\\\\b", "\\\\bH[1-5]\\\\b", "fluid_\\\\w+"]\n'))
    assert cfg.forbidden_patterns == [r"\bE[12]\b", r"\bH[1-5]\b", r"fluid_\w+"]
    for text, hit in (("E1 concept AUROC", True), ("H3 IoU", True), ("IRF (fluid_irf)", True),
                      ("E10 grade", False), ("SE1", False), ("HRF", False), ("Edema", False)):
        fig, ax = _fig(); ax.set_title(text)
        assert bool(qa.figure_text_audit(fig, cfg=cfg)) is hit, text
    assert qa.forbidden_in_text("E2 BACC", cfg) == [r"\bE[12]\b"]  # tables / markdown
    assert qa.forbidden_in_text("3-class BACC", cfg) == []
    config.use(cfg)
    try:  # active config used by default
        fig, ax = _fig(); ax.set_title("E2 margin")
        assert qa.figure_text_audit(fig)
    finally:
        config.use(None)


def test_caveat_allow_lifts_default_caveats(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\n[qa]\ncaveat_allow = ["retrospective"]\n'))
    fig, ax = _fig(); ax.set_xlabel("Review budget (retrospective)")
    assert qa.figure_text_audit(fig, cfg=cfg) == []
    ax.set_title("Illustrative")
    assert qa.figure_text_audit(fig, cfg=cfg)


@pytest.mark.parametrize("body,msg", [
    ('[qa]\nforbidden_patterns = ["(unclosed"]\n', "not a valid regular expression"),
    ('[qa]\nforbidden_patterns = "E1"\n', "must be a list"),
    ('[qa]\ncaveat_allow = ["not-a-default"]\n', "not in the default caveat list"),
])
def test_config_rejects_bad_text_rules(tmp_path, body, msg):
    with pytest.raises(ValueError, match=msg):
        config.load(_write_toml(tmp_path, 'data_root = "data"\n' + body))


def test_save_fails_on_figure_text(project, monkeypatch):
    _fake_tools(monkeypatch, {})
    fig, ax = plt.subplots(figsize=(3, 2)); ax.plot([0, 1], [0, 1], color=style.DATA_CYCLE[0])
    ax.tick_params(labelsize=6)
    fig.text(0.5, 0.01, "Illustrative only", fontsize=6)
    with pytest.raises(RuntimeError, match="figure_text="):
        export.save(fig, "t", Provenance("t"), size=(3, 2), cfg=project, panels="none")
