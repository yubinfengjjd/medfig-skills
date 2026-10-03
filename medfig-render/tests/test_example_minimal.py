"""End-to-end: the synthetic example project (examples/minimal) builds its data, one mixed figure and one
table in a temporary copy; composite + per-panel exports, provenance and QA are checked."""
import hashlib
import json
import re
import runpy
import shutil
import sys
from pathlib import Path

import pytest

from conftest import needs_scipilot

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "minimal"
PANELS = ["a", "b", "c", "d"]


def _assert_portable(source_json, proj):
    """No absolute path, drive letter, user home or project location anywhere in a source.json."""
    text = Path(source_json).read_text(encoding="utf-8")
    home = str(Path.home())
    for needle in (home, home.replace("\\", "/"), home.replace("\\", "\\\\"),
                   str(proj.parent), proj.parent.as_posix()):
        assert needle not in text, needle
    assert not re.search(r"[A-Za-z]:[/\\]", text), "drive-letter path in source.json"
    assert not re.search(r'"/(?:Users|home|tmp)/', text)


def _run(path):
    """Run an example script as __main__-free module and return its main() result."""
    ns = runpy.run_path(str(path), run_name="example")
    return ns["main"]()


@pytest.fixture
def built(tmp_path, monkeypatch):
    proj = tmp_path / "minimal"
    shutil.copytree(EXAMPLE, proj, ignore=shutil.ignore_patterns("out", "data", "__pycache__"))
    monkeypatch.chdir(tmp_path)  # scripts must not depend on the working directory
    lib = str(EXAMPLE.parents[1] / "lib")
    if lib not in sys.path:
        monkeypatch.syspath_prepend(lib)
    data = _run(proj / "make_data.py")
    fig = _run(proj / "figures" / "fig_demo.py")
    tab = _run(proj / "tables" / "table_demo.py")
    return proj, data, fig, tab


def test_example_has_no_absolute_paths():
    for p in EXAMPLE.rglob("*"):
        if p.suffix in (".py", ".toml") and "out" not in p.parts:
            src = p.read_text(encoding="utf-8")
            assert not re.search(r"\b[A-Za-z]:[/\\]", src), p
            assert "/Users/" not in src and "\\Users\\" not in src and "/home/" not in src, p


def test_make_data_is_deterministic(tmp_path):
    ns = runpy.run_path(str(EXAMPLE / "make_data.py"), run_name="example")
    a, b = ns["main"](tmp_path / "a"), ns["main"](tmp_path / "b")
    for f in sorted(a.iterdir()):
        if f.suffix == ".csv":  # npz embeds zip timestamps; compare arrays below
            assert f.read_bytes() == (b / f.name).read_bytes(), f.name
    import numpy as np
    za, zb = np.load(a / "bscan.npz"), np.load(b / "bscan.npz")
    assert all(np.array_equal(za[k], zb[k]) for k in za.files)


@needs_scipilot
def test_example_minimal_end_to_end(built):
    proj, data, fig, tab = built
    out = proj / "out"
    main = out / "figures" / "main"
    for ext in ("pdf", "svg", "png"):
        f = main / f"fig_demo.{ext}"
        assert f.is_file() and f.stat().st_size > 0, f
    # S4: every panel standalone, PDF + SVG, no panel label
    pdir = out / "panels" / "fig_demo"
    for pid in PANELS:
        for ext in ("pdf", "svg"):
            f = pdir / f"fig_demo_{pid}.{ext}"
            assert f.is_file() and f.stat().st_size > 0, f
        texts = [t.strip() for t in re.findall(r"<text[^>]*>([^<]*)</text>",
                                               (pdir / f"fig_demo_{pid}.svg").read_text(encoding="utf-8"))]
        assert not set(PANELS) & set(texts), f"panel label left in panel {pid}: {texts}"
    comp = [t.strip() for t in re.findall(r"<text[^>]*>([^<]*)</text>",
                                          (main / "fig_demo.svg").read_text(encoding="utf-8"))]
    assert set(PANELS) <= set(comp)

    src = json.loads((main / "fig_demo.source.json").read_text(encoding="utf-8"))
    assert [p["id"] for p in src["values"]["panels"]] == PANELS
    assert src["root"] == proj.name
    names = sorted(i["path"] for i in src["inputs"])
    assert names == ["data/bscan.npz", "data/confusion.csv", "data/intervals.csv", "data/roc_runs.csv"]
    for i in src["inputs"]:
        assert i["sha256"] == hashlib.sha256((proj / i["path"]).read_bytes()).hexdigest()
    for r in src["values"]["panels"]:
        assert r["pdf"] == f"out/panels/fig_demo/fig_demo_{r['id']}.pdf"
        assert (proj / r["svg"]).is_file()
    _assert_portable(main / "fig_demo.source.json", proj)
    _assert_portable(tab["source"], proj)
    qa_res = src["values"]["qa"]
    for k in ("colour", "whitespace", "text_only", "geometry", "banned", "min_font", "true_minus"):
        assert qa_res[k] == [], (k, qa_res[k])
    v = src["values"]
    assert v["c_absent"] == ["Gamma"] and v["c_n_per_row"]["Gamma"] == 0
    assert v["b_n_runs"] == 5 and v["b_auc_mean_sd"][1] > 0

    # table: CSV + MD + provenance with hashed inputs
    assert tab["csv"].is_file() and tab["md"].is_file()
    md = tab["md"].read_text(encoding="utf-8")
    assert "| Subgroup |" in md and "Gamma" in md
    tsrc = json.loads(tab["source"].read_text(encoding="utf-8"))
    assert tsrc["values"]["absent_classes"] == ["Gamma"]
    assert {i["path"] for i in tsrc["inputs"]} == {"data/intervals.csv", "data/confusion.csv"}
    assert all(len(i["sha256"]) == 64 for i in tsrc["inputs"])
