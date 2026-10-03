"""Shared fixtures: a tiny synthetic figkit project built in tmp_path (no real study data)."""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib as mpl  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pytest  # noqa: E402

LIB = Path(__file__).resolve().parents[1] / "lib"
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))

from figkit import config  # noqa: E402

SCIPILOT = Path(config.DEFAULT_SCIPILOT).expanduser()
needs_scipilot = pytest.mark.skipif(
    not (SCIPILOT / "setup_style.py").is_file(),
    reason="scipilot-medimg-figure-skill scripts not installed")

TOML = """\
project_root = "."
data_root = "data"
out_dir = "out"
external_dirs = ["delta"]
journal = "nature"
scipilot_scripts = "{sp}"

[palettes.cohort.site_a]
color = "#0072B2"
marker = "o"
label = "Site A"

[palettes.cohort.site_b]
color = "#F0E442"
marker = "s"
label = "Site B"
edge = "#8C7A00"

[palettes.class.healthy]
color = "#4D4D4D"
marker = "o"

[palettes.class.disease]
color = "#D55E00"
marker = "^"
"""


@pytest.fixture(autouse=True)
def _clean_mpl_state():
    """Every test starts from matplotlib defaults and no active figkit config."""
    mpl.rcdefaults()
    # figkit figures are always drawn at the 6 pt base; matplotlib's 10 pt default makes y tick labels
    # of a 3x2 in figure genuinely stick out of the canvas, which the audit correctly reports.
    from figkit import style
    mpl.rcParams.update(style.RC)
    config.use(None)
    yield
    plt.close("all")
    mpl.rcdefaults()
    config.use(None)


@pytest.fixture
def project(tmp_path):
    """Tiny synthetic project: figkit.toml + data/ (csv, json, jsonl, npz) + delta/ (external)."""
    root = tmp_path / "proj"
    data = root / "data"
    (data / "ledger").mkdir(parents=True)
    (root / "delta").mkdir()
    (data / "scores.csv").write_text("id,score\n1,0.1\n2,0.4\n3,0.9\n", encoding="utf-8")
    (data / "summary.json").write_text(json.dumps({"runs": [1, 2, 3, 4]}), encoding="utf-8")
    recs = [{"key": "a", "v": 1}, {"key": "b", "v": 2}, {"key": "a", "v": 3}]
    (data / "ledger" / "runs.jsonl").write_text(
        "\n".join(json.dumps(r) for r in recs) + "\n\n", encoding="utf-8")
    np.savez(data / "arrays.npz", x=np.arange(3), y=np.ones(2))
    (data / "notes.txt").write_text("line one\nline two\n", encoding="utf-8")
    (root / "delta" / "extra.csv").write_text("k,v\nx,1\ny,2\n", encoding="utf-8")
    (tmp_path / "outside.csv").write_text("a\n1\n", encoding="utf-8")
    (root / "data2").mkdir()
    (root / "data2" / "sibling.csv").write_text("a\n1\n", encoding="utf-8")
    toml = root / "figkit.toml"
    toml.write_text(TOML.format(sp=SCIPILOT.as_posix()), encoding="utf-8")
    return config.load(toml)
