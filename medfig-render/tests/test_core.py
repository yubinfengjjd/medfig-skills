"""figkit core tests: config, io.Reader, provenance, style, qa, export. Synthetic data only."""
import hashlib
import json
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

from conftest import LIB, SCIPILOT, TOML, needs_scipilot
from figkit import config, export, io, qa, style
from figkit.provenance import Provenance


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _write_toml(tmp_path, body):
    (tmp_path / "data").mkdir(exist_ok=True)
    p = tmp_path / "figkit.toml"
    p.write_text(body, encoding="utf-8")
    return p


# ---------------------------------------------------------------- config
def test_config_load_resolves_paths(project):
    root = project.project_root
    assert project.data_root == (root / "data").resolve()
    assert project.out_dir == (root / "out").resolve()
    assert project.external_dirs == [(root / "delta").resolve()]
    assert project.journal == "nature"
    assert project.scipilot_scripts == SCIPILOT.resolve()
    assert set(project.palettes["cohort"]) == {"site_a", "site_b"}
    assert project.palettes["cohort"]["site_b"]["edge"] == "#8C7A00"
    assert set(project.palettes["class"]) == {"healthy", "disease"}


def test_config_defaults(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\n'))
    assert cfg.project_root == tmp_path.resolve()
    assert cfg.out_dir == (tmp_path / "out").resolve()
    assert cfg.external_dirs == [] and cfg.journal == "nature"
    assert cfg.palettes == {"cohort": {}, "class": {}}
    assert cfg.scipilot_scripts == Path(config.DEFAULT_SCIPILOT).expanduser().resolve()
    assert "scipilot-medimg-figure-skill" in config.DEFAULT_SCIPILOT


def test_config_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        config.load(tmp_path / "nope.toml")


def test_config_requires_data_root(tmp_path):
    with pytest.raises(ValueError, match="data_root"):
        config.load(_write_toml(tmp_path, 'journal = "nature"\n'))


def test_config_missing_scipilot_dir_clear_error(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\nscipilot_scripts = "no_such_dir"\n'))
    with pytest.raises(FileNotFoundError, match="scipilot-medimg-figure-skill"):
        cfg.ensure_scipilot()


def test_config_active_requires_load_or_use(project):
    config.use(None)
    with pytest.raises(RuntimeError, match="figkit.toml"):
        config.active()
    config.use(project)
    assert config.active() is project


def test_config_bad_palette_type(tmp_path):
    with pytest.raises(ValueError, match="palettes"):
        config.load(_write_toml(tmp_path, 'data_root = "data"\npalettes = 3\n'))


def test_no_hard_coded_paths_in_lib():
    src = "\n".join(p.read_text(encoding="utf-8") for p in (LIB / "figkit").glob("*.py"))
    assert not re.search(r"\b[A-Za-z]:[/\\]", src), "drive-letter path in figkit source"
    assert "/Users/" not in src and "\\Users\\" not in src


# ---------------------------------------------------------------- io.Reader
def test_reader_csv_records_hash_and_rows(project, tmp_path):
    prov = Provenance("t")
    df = io.Reader(prov, project).csv("scores.csv")
    assert len(df) == 3
    rec = prov.inputs[0]
    p = project.data_root / "scores.csv"
    assert rec["rows"] == 3 and rec["sha256"] == _sha(p) and rec["path"] == "data/scores.csv"
    out = prov.write(tmp_path / "o")
    assert json.loads(out.read_text(encoding="utf-8"))["inputs"][0]["rows"] == 3


def test_reader_uses_active_config(project):
    config.use(project)
    prov = Provenance("t")
    io.Reader(prov).csv("scores.csv")
    assert prov.inputs[0]["rows"] == 3


def test_reader_json_rows(project):
    prov = Provenance("t")
    rd = io.Reader(prov, project)
    obj = rd.json("summary.json")
    assert obj == {"runs": [1, 2, 3, 4]} and prov.inputs[0]["rows"] == 1
    rd.json("summary.json", rows=lambda o: len(o["runs"]))
    assert prov.inputs[1]["rows"] == 4


def test_reader_ledger_filters_key_and_skips_blank_lines(project):
    prov = Provenance("t")
    recs = io.Reader(prov, project).ledger("runs.jsonl", "a")
    assert [r["v"] for r in recs] == [1, 3] and prov.inputs[0]["rows"] == 2


def test_reader_npz_and_text(project):
    prov = Provenance("t")
    rd = io.Reader(prov, project)
    z = rd.npz("arrays.npz")
    assert sorted(z.files) == ["x", "y"] and prov.inputs[0]["rows"] == 2
    txt = rd.text("notes.txt")
    assert txt.startswith("line one") and prov.inputs[1]["rows"] == 2


def test_reader_parquet(project):
    pytest.importorskip("pyarrow")
    pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_parquet(project.data_root / "t.parquet")
    prov = Provenance("t")
    df = io.Reader(prov, project).parquet("t.parquet", columns=["a"])
    assert list(df.columns) == ["a"] and prov.inputs[0]["rows"] == 2


@pytest.mark.parametrize("rel", ["../outside.csv", "../../outside.csv", "../data2/sibling.csv"])
def test_reader_refuses_escape_before_reading(project, rel, monkeypatch):
    called = []
    monkeypatch.setattr(io.pd, "read_csv", lambda *a, **k: called.append(a))
    prov = Provenance("t")
    with pytest.raises(ValueError, match="escapes"):
        io.Reader(prov, project).csv(rel)
    assert called == [] and prov.inputs == []


def test_reader_refuses_absolute_path_outside(project, tmp_path):
    with pytest.raises(ValueError):
        io.Reader(Provenance("t"), project).csv(str(tmp_path / "outside.csv"))


def test_reader_json_escape(project):
    with pytest.raises(ValueError):
        io.Reader(Provenance("t"), project).json("../../outside.json")


def test_external_whitelist(project, tmp_path):
    prov = Provenance("t")
    rd = io.Reader(prov, project)
    df = rd.external(project.external_dirs[0] / "extra.csv")
    assert len(df) == 2 and prov.inputs[0]["rows"] == 2
    assert len(rd.external("extra.csv")) == 2  # relative -> first whitelisted dir
    with pytest.raises(ValueError, match="external"):
        rd.external(tmp_path / "outside.csv")
    with pytest.raises(ValueError, match="external"):
        rd.external("../data/scores.csv")
    assert len(prov.inputs) == 2


def test_external_without_whitelist_refuses(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\n'))
    (tmp_path / "x.csv").write_text("a\n1\n", encoding="utf-8")
    with pytest.raises(ValueError):
        io.Reader(Provenance("t"), cfg).external(tmp_path / "x.csv")


def test_external_npz(project):
    np.savez(project.external_dirs[0] / "case.npz", raw=np.zeros((2, 3)), heat=np.ones(4))
    prov = Provenance("t")
    z = io.Reader(prov, project).external("case.npz")
    assert z["raw"].shape == (2, 3) and prov.inputs[0]["rows"] == 2


def test_external_unsupported_suffix(project):
    (project.external_dirs[0] / "x.bin").write_bytes(b"\x00")
    with pytest.raises(ValueError, match="unsupported"):
        io.Reader(Provenance("t"), project).external("x.bin")


# ---------------------------------------------------------------- provenance
def test_provenance_write(tmp_path):
    prov = Provenance("figX")
    prov.add_input("a.csv", "0" * 64, 5)
    prov.add_transform("mean over seeds")
    prov.set("n", np.int64(7))
    prov.set("err", np.float64(0.5))
    out = prov.write(tmp_path / "sub")
    assert out.name == "figX.source.json"
    d = json.loads(out.read_text(encoding="utf-8"))
    assert set(d) == {"figure", "root", "created", "inputs", "transforms", "values"}
    assert d["root"] is None and d["inputs"][0]["path"] == "a.csv"  # unbound: relative paths only
    assert d["values"] == {"n": 7, "err": 0.5} and d["transforms"] == ["mean over seeds"]


# ---------------------------------------------------------------- style
@needs_scipilot
def test_style_apply_true_minus_and_font_floor(project):
    style.apply(project)
    import matplotlib as mpl
    assert mpl.rcParams["axes.unicode_minus"] is True
    for k in ("font.size", "xtick.labelsize", "ytick.labelsize", "legend.fontsize",
              "axes.labelsize", "axes.titlesize"):
        assert float(mpl.rcParams[k]) >= style.MIN_FONT_PT
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.plot([-4, 4], [-3, 3])
    fig.canvas.draw()
    labs = [t.get_text() for t in ax.get_xticklabels() + ax.get_yticklabels()]
    assert any(s.startswith("−") for s in labs) and not any("-" in s for s in labs)
    assert qa.true_minus(fig) == []


@needs_scipilot
def test_style_palettes_from_config(project):
    style.apply(project)
    assert style.palette("cohort")["site_a"]["label"] == "Site A"
    assert set(style.palette("class")) == {"healthy", "disease"}
    assert abs(style.mm(180) - 7.087) < 0.01
    assert (style.DOUBLE, style.SINGLE) == (7.09, 3.46)
    assert len(style.OKABE_ITO) == 8


def test_style_missing_scipilot_clear_error(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\nscipilot_scripts = "gone"\n'))
    with pytest.raises(FileNotFoundError, match="install"):
        style.apply(cfg)


# ---------------------------------------------------------------- qa
def test_banned_words_single_list():
    for w in ("diagnostic", "clinically proven", "validated", "deployment"):
        assert w in qa.BANNED
    assert len(qa.BANNED) == len(set(w.lower() for w in qa.BANNED))
    fig, ax = plt.subplots()
    ax.set_title("A Diagnostic view")
    ax.text(0.1, 0.1, "clinically proven")
    ax.set_xlabel("invalidated")  # word boundary: not a hit
    assert sorted(qa.banned_words(fig)) == ["clinically proven", "diagnostic"]


def test_banned_words_text_helper():
    assert qa.banned_in_text("ready for deployment") == ["deployment"]
    assert qa.banned_in_text("fine") == []


def test_geometry_audit_catches_overlap():
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.text(0.5, 0.5, "AAAA", transform=ax.transAxes)
    ax.text(0.5, 0.5, "BBBB", transform=ax.transAxes)
    assert any("overlap" in m for m in qa.geometry_audit(fig))


def test_geometry_audit_ignores_offscreen_ticks():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0.5, 1.02], [0, 1])
    ax.set_xlim(0.5, 1.02)
    assert qa.geometry_audit(fig) == []


def test_geometry_audit_ignores_hidden_and_empty_text():
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.text(0.5, 0.5, "AAAA", transform=ax.transAxes)
    ax.text(0.5, 0.5, "BBBB", transform=ax.transAxes).set_visible(False)
    ax.text(0.5, 0.5, "", transform=ax.transAxes)
    assert qa.geometry_audit(fig) == []


def test_geometry_audit_legend_covers_scatter():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1], [0, 1], label="line")  # line without markers: not data points
    ax.scatter([0.02], [0.98], label="pt")
    ax.legend(loc="upper left")
    assert any("legend covers data" in m for m in qa.geometry_audit(fig))


def test_geometry_audit_legend_covers_marker_line():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0.08, 0.9], [0.92, 0.1], "o-", label="m")  # first marker well inside the legend frame
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(loc="upper left")
    assert any("legend covers data" in m for m in qa.geometry_audit(fig))


def test_geometry_audit_hexbin_offsets_placed_in_data_space():
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.hexbin(rng.uniform(0.6, 1, 300), rng.uniform(0, 0.4, 300), gridsize=10, mincnt=1)
    ax.plot([], [], label="ref"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(loc="upper left")
    assert qa.geometry_audit(fig) == []
    fig2, ax2 = plt.subplots(figsize=(3, 2))
    ax2.hexbin(rng.uniform(0, 0.3, 300), rng.uniform(0.7, 1, 300), gridsize=10, mincnt=1)
    ax2.plot([], [], label="ref"); ax2.set_xlim(0, 1); ax2.set_ylim(0, 1)
    ax2.legend(loc="upper left")
    assert any("legend covers data" in m for m in qa.geometry_audit(fig2))


def test_geometry_audit_ignores_clipped_points_outside_view():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.scatter([5.0], [5.0], label="pt"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5))
    fig.subplots_adjust(right=0.6)
    assert not any("legend covers data" in m for m in qa.geometry_audit(fig))


def test_geometry_audit_skips_identity_pseudo_offsets():
    from matplotlib.collections import LineCollection, PolyCollection
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.add_collection(LineCollection([[(0, 0.9), (0.2, 1.0)]]))
    ax.add_collection(PolyCollection([[(0, 0.8), (0.2, 0.8), (0.1, 1.0)]]))
    ax.plot([], [], label="ref"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.legend(loc="lower right")
    assert qa.geometry_audit(fig) == []


def test_geometry_audit_legend_overlaps_text():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.plot([0, 1], [0, 1], label="line")
    ax.legend(loc="upper left")
    ax.text(0.03, 0.9, "NOTE", transform=ax.transAxes)
    assert any("overlap" in m and "legend" in m and "NOTE" in m for m in qa.geometry_audit(fig))


def test_geometry_audit_text_outside_canvas():
    fig, ax = plt.subplots(figsize=(2, 2))
    fig.text(1.05, 0.5, "OUT")
    assert any("outside canvas" in m for m in qa.geometry_audit(fig))


def test_min_font_flags_small_text():
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.tick_params(labelsize=6)
    ax.xaxis.label.set_fontsize(6); ax.yaxis.label.set_fontsize(6); ax.title.set_fontsize(6)
    ax.text(0.5, 0.5, "ok", fontsize=6)
    assert qa.min_font(fig) == []
    ax.text(0.2, 0.2, "tiny", fontsize=5)
    msgs = qa.min_font(fig)
    assert len(msgs) == 1 and "tiny" in msgs[0]


def test_min_font_allows_5pt_inset_ticks_only():
    fig, ax = plt.subplots(figsize=(3, 2))
    ax.tick_params(labelsize=6)
    ax.xaxis.label.set_fontsize(6); ax.yaxis.label.set_fontsize(6)
    ins = ax.inset_axes([0.6, 0.6, 0.35, 0.35])
    ins.plot([0, 1], [0, 1]); ins.tick_params(labelsize=5)
    assert qa.min_font(fig) == []
    ins.tick_params(labelsize=4.5)
    assert qa.min_font(fig)
    ins.tick_params(labelsize=5)
    ins.text(0.5, 0.5, "inset note", fontsize=5)
    assert any("inset note" in m for m in qa.min_font(fig))


def test_true_minus_flags_ascii_hyphen_ticks():
    import matplotlib as mpl
    mpl.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.plot([-4, 4], [-3, 3])
    assert qa.true_minus(fig)
    ax.set_xlabel("pre-treatment")  # hyphen between words is fine
    mpl.rcParams["axes.unicode_minus"] = True
    fig2, ax2 = plt.subplots(figsize=(2, 2))
    ax2.plot([-4, 4], [-3, 3]); ax2.set_xlabel("pre-treatment")
    assert qa.true_minus(fig2) == []
    ax2.text(0.5, 0.5, "-1.5")
    assert any("-1.5" in m for m in qa.true_minus(fig2))


# ---------------------------------------------------------------- export
def _fake_tools(monkeypatch, seen, cf_issues=()):
    monkeypatch.setattr(export, "audit_layout", lambda fig: seen.setdefault("audit", []) or [])
    def fake_export(fig, base, **k):
        seen["export_kw"] = k
        seen["export_size"] = tuple(fig.get_size_inches())
        seen["base"] = base
        return [base + ".pdf", base + ".png", base + "_grayscale.png"]
    monkeypatch.setattr(export, "export_figure", fake_export)
    def fake_check(f, **k):
        seen.setdefault("checked", []).append(Path(f).name)
        return list(cf_issues), {}
    monkeypatch.setattr(export, "check_figure", fake_check)


def test_save_runs_qa_at_final_size(project, monkeypatch):
    seen = {}
    _fake_tools(monkeypatch, seen)
    def fake_geo(fig):
        seen["size"] = tuple(fig.get_size_inches()); return []
    monkeypatch.setattr(export.qa, "geometry_audit", fake_geo)
    prov = Provenance("t")
    fig, ax = plt.subplots(figsize=(2, 2)); ax.plot([0, 1], [0, 1])
    res = export.save(fig, "t", prov, kind="supp", size=(3.46, 2.5), cfg=project, panels="none")
    assert seen["size"] == (3.46, 2.5) and seen["export_size"] == (3.46, 2.5)
    assert seen["export_kw"]["size_inches"] is None
    assert Path(seen["base"]) == project.out_dir / "figures" / "supp" / "t"
    assert seen["checked"] == ["t.pdf", "t.png"]  # grayscale preview not checked
    src = project.out_dir / "figures" / "supp" / "t.source.json"
    d = json.loads(src.read_text(encoding="utf-8"))
    assert set(d["values"]["qa"]) >= {"audit_layout", "geometry", "banned", "min_font",
                                      "true_minus", "check_figure"}
    assert res["qa"] is prov.values["qa"]


@pytest.mark.parametrize("bad", ["banned", "font", "overlap", "minus"])
def test_save_raises_before_export_on_qa_fail(project, monkeypatch, bad):
    seen = {}
    _fake_tools(monkeypatch, seen)
    import matplotlib as mpl
    mpl.rcParams["axes.unicode_minus"] = True
    fig, ax = plt.subplots(figsize=(3, 2)); ax.plot([0, 1], [0, 1])
    ax.tick_params(labelsize=6)
    ax.xaxis.label.set_fontsize(6); ax.yaxis.label.set_fontsize(6)
    if bad == "banned":
        ax.set_title("validated model", fontsize=6)
    elif bad == "font":
        ax.text(0.5, 0.5, "small", fontsize=4)
    elif bad == "overlap":
        ax.text(0.5, 0.5, "AAAA", transform=ax.transAxes, fontsize=6)
        ax.text(0.5, 0.5, "BBBB", transform=ax.transAxes, fontsize=6)
    else:
        ax.text(0.5, 0.5, "-2", fontsize=6)
    with pytest.raises(RuntimeError, match="QA failed"):
        export.save(fig, "t", Provenance("t"), size=(3, 2), cfg=project)
    assert "export_kw" not in seen
    assert not (project.out_dir / "figures" / "main" / "t.source.json").exists()


def test_save_raises_on_audit_layout_fail(project, monkeypatch):
    seen = {}
    _fake_tools(monkeypatch, seen)
    monkeypatch.setattr(export, "audit_layout", lambda fig: [("FAIL", "missing glyph")])
    fig, ax = plt.subplots(figsize=(2, 2))
    ax.tick_params(labelsize=6)
    with pytest.raises(RuntimeError, match="missing glyph"):
        export.save(fig, "t", Provenance("t"), cfg=project)
    assert "export_kw" not in seen


def test_save_raises_on_check_figure_fail(project, monkeypatch):
    seen = {}
    _fake_tools(monkeypatch, seen, cf_issues=[("FAIL", "type3 font")])
    fig, ax = plt.subplots(figsize=(2, 2))
    out = project.out_dir / "figures" / "main"
    out.mkdir(parents=True)
    for ext in ("pdf", "png", "_grayscale.png"):  # stand-ins for files the real export writes
        (out / ("t" + ext if ext.startswith("_") else f"t.{ext}")).write_bytes(b"x")
    with pytest.raises(RuntimeError, match="check_figure FAIL"):
        export.save(fig, "t", Provenance("t"), size=(2, 2), cfg=project, panels="none")
    assert not (out / "t.source.json").exists()
    assert list(out.iterdir()) == []  # written pdf/png/grayscale removed before raising


def test_save_missing_scipilot_clear_error(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\nscipilot_scripts = "gone"\n'))
    fig, ax = plt.subplots(figsize=(2, 2))
    with pytest.raises(FileNotFoundError, match="install"):
        export.save(fig, "t", Provenance("t"), size=(2, 2), cfg=cfg)


def _save_small(cfg):
    fig, ax = plt.subplots(figsize=(2, 2)); ax.plot([0, 1], [0, 1])
    ax.set_xlabel("x"); ax.set_ylabel("y")
    return export.save(fig, "t", Provenance("t"), size=(style.SINGLE, 2.2), cfg=cfg, panels="none")


def _missing_cfg(tmp_path):
    d = tmp_path / "missing"
    d.mkdir()
    return config.load(_write_toml(d, 'data_root = "data"\nscipilot_scripts = "gone"\n'))


@needs_scipilot
@pytest.mark.parametrize("missing_first", [False, True])
def test_save_rechecks_scipilot_per_config(project, tmp_path, missing_first):
    """A config with a missing scipilot dir always raises, whether or not tools were cached earlier."""
    missing = _missing_cfg(tmp_path)
    if missing_first:
        with pytest.raises(FileNotFoundError, match="scipilot-medimg-figure-skill scripts not found"):
            _save_small(missing)
    style.apply(project)
    assert _save_small(project)["files"]
    with pytest.raises(FileNotFoundError, match="scipilot-medimg-figure-skill scripts not found"):
        _save_small(missing)


def test_export_has_no_bare_asserts():
    src = (LIB / "figkit" / "export.py").read_text(encoding="utf-8")
    assert not re.search(r"^\s*assert\b", src, flags=re.M)


@needs_scipilot
def test_save_end_to_end_real_scipilot(project):
    style.apply(project)
    prov = Provenance("demo")
    df = io.Reader(prov, project).csv("scores.csv")
    fig, ax = plt.subplots()
    ax.plot(df["id"], df["score"] - 0.5, "o-", color=style.palette("cohort")["site_a"]["color"])
    ax.set_xlabel("Case"); ax.set_ylabel("Centred score")
    res = export.save(fig, "demo", prov, kind="main", size=(style.SINGLE, 2.2), cfg=project, panels="none")
    out = project.out_dir / "figures" / "main"
    for ext in ("pdf", "svg", "png"):
        assert (out / f"demo.{ext}").is_file()
    assert "\u2212" in (out / "demo.svg").read_text(encoding="utf-8")
    d = json.loads(res["source"].read_text(encoding="utf-8"))
    assert d["inputs"][0]["rows"] == 3 and d["values"]["qa"]["geometry"] == []


# ---------------------------------------------------------------- portable provenance paths
def _assert_no_abs(text, *roots):
    home = str(Path.home())
    for needle in (home, home.replace("\\", "/"), home.replace("\\", "\\\\"), *roots):
        assert str(needle) not in text, needle
    assert not re.search(r"[A-Za-z]:[/\\]", text), "drive-letter path"


def test_provenance_paths_relative_to_project_root(project, tmp_path):
    prov = Provenance("t")
    rd = io.Reader(prov, project)
    rd.csv("scores.csv")
    rd.ledger("runs.jsonl", "a")
    rd.external("extra.csv")  # delta/ is inside project_root -> plain relative path
    assert [i["path"] for i in prov.inputs] == ["data/scores.csv", "data/ledger/runs.jsonl",
                                                "delta/extra.csv"]
    assert prov.inputs[0]["sha256"] == _sha(project.data_root / "scores.csv") and prov.inputs[0]["rows"] == 3
    out = prov.write(tmp_path / "o")
    d = json.loads(out.read_text(encoding="utf-8"))
    assert d["root"] == project.project_root.name
    _assert_no_abs(out.read_text(encoding="utf-8"), project.project_root, project.project_root.as_posix())


def test_provenance_external_outside_project_tagged(tmp_path):
    ext = tmp_path / "shared" / "tables"
    ext.mkdir(parents=True)
    (ext / "t.csv").write_text("a\n1\n2\n", encoding="utf-8")
    proj = tmp_path / "proj"
    proj.mkdir()
    cfg = config.load(_write_toml(proj, f'data_root = "data"\nexternal_dirs = ["{ext.as_posix()}"]\n'))
    prov = Provenance("t")
    io.Reader(prov, cfg).external("t.csv")
    assert prov.inputs == [{"path": "external:tables/t.csv", "sha256": _sha(ext / "t.csv"), "rows": 2}]
    _assert_no_abs(json.dumps(prov.inputs), tmp_path, tmp_path.as_posix())


def test_provenance_refuses_unbound_absolute_and_outside_paths(project, tmp_path):
    with pytest.raises(ValueError, match="bound config"):
        Provenance("t").add_input(tmp_path / "x.csv", "0" * 64, 1)
    with pytest.raises(ValueError, match="outside project_root"):
        Provenance("t", project).add_input(tmp_path / "elsewhere.csv", "0" * 64, 1)


@needs_scipilot
def test_save_source_json_has_no_absolute_paths(project):
    from figkit import panel
    style.apply(project)
    prov = Provenance("p")
    df = io.Reader(prov, project).csv("scores.csv")
    fig, ax = plt.subplots(layout="constrained")
    ax.plot(df["id"], df["score"], "o-"); ax.set_xlabel("Case"); ax.set_ylabel("Score")
    panel.mark_panel(ax, "a")
    res = export.save(fig, "p", prov, size=(style.SINGLE, 2.2), cfg=project)
    text = res["source"].read_text(encoding="utf-8")
    d = json.loads(text)
    assert d["inputs"][0]["path"] == "data/scores.csv"
    assert d["values"]["panels"][0]["pdf"] == "out/panels/p/p_a.pdf"
    assert "out/figures/main/p.pdf" in d["values"]["files"]
    assert Path(res["panels"][0]["pdf"]).is_absolute()  # the return value keeps usable paths
    _assert_no_abs(text, project.project_root, project.project_root.as_posix())


# ---------------------------------------------------------------- [qa] banned_extra / banned_allow
def test_banned_default_without_config():
    assert qa.banned_list() == qa.BANNED
    assert qa.banned_in_text("a diagnostic accuracy study") == ["diagnostic"]


def test_banned_extra_adds_words(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\n[qa]\nbanned_extra = ["breakthrough", "UMAP"]\n'))
    assert cfg.banned_extra == ["breakthrough", "UMAP"]
    assert qa.banned_list(cfg) == qa.BANNED + ["breakthrough"]  # UMAP already a default: not duplicated
    assert qa.banned_in_text("A breakthrough", cfg) == ["breakthrough"]
    assert qa.banned_in_text("A breakthrough") == ["breakthrough"]  # active config used by default
    fig, ax = plt.subplots(); ax.set_title("Breakthrough")
    assert qa.banned_words(fig) == ["breakthrough"]


def test_banned_allow_lifts_default_words(tmp_path):
    cfg = config.load(_write_toml(tmp_path, 'data_root = "data"\n[qa]\nbanned_allow = ["diagnostic", "umap"]\n'))
    assert "diagnostic" not in qa.banned_list(cfg) and "UMAP" not in qa.banned_list(cfg)
    assert "validated" in qa.banned_list(cfg)
    assert qa.banned_in_text("UMAP of diagnostic accuracy embeddings", cfg) == []
    assert qa.banned_in_text("a validated model", cfg) == ["validated"]
    config.use(None)
    assert qa.banned_in_text("diagnostic") == ["diagnostic"]  # no config: default list again


@pytest.mark.parametrize("body,msg", [
    ('[qa]\nbanned_allow = ["not-a-default"]\n', "not in the default list"),
    ('[qa]\nbanned_extra = "word"\n', "must be a list"),
    ('[qa]\nbanned = ["x"]\n', "unknown keys"),
])
def test_banned_config_rejects_bad_values(tmp_path, body, msg):
    with pytest.raises(ValueError, match=msg):
        config.load(_write_toml(tmp_path, 'data_root = "data"\n' + body))


def test_save_uses_project_banned_list(project, monkeypatch, tmp_path):
    seen = {}
    _fake_tools(monkeypatch, seen)
    fig, ax = plt.subplots(figsize=(3, 2)); ax.plot([0, 1], [0, 1], color=style.DATA_CYCLE[0])
    ax.set_title("Diagnostic accuracy", fontsize=6); ax.tick_params(labelsize=6)
    with pytest.raises(RuntimeError, match="banned="):
        export.save(fig, "t", Provenance("t"), size=(3, 2), cfg=project, panels="none")
    project.banned_allow = ["diagnostic"]
    res = export.save(fig, "t", Provenance("t"), size=(3, 2), cfg=project, panels="none")
    assert res["qa"]["banned"] == []
    project.banned_extra = ["accuracy"]
    with pytest.raises(RuntimeError, match=r"banned=\['accuracy'\]"):
        export.save(fig, "t2", Provenance("t2"), size=(3, 2), cfg=project, panels="none")
