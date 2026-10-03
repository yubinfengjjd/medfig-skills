"""The shipped figure-script template runs end to end on a synthetic project (it must pass its own QA)."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from conftest import SCIPILOT, needs_scipilot

REPO_RENDER = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_RENDER / "templates" / "figure_script.py"
TEMPLATE_TOML = REPO_RENDER / "templates" / "figkit.toml"
LIB = REPO_RENDER / "lib"


def _synthetic_inputs(res):
    rng = np.random.default_rng(7)
    (res / "images").mkdir(parents=True)
    (res / "scores").mkdir()
    (res / "tables").mkdir()
    yy, xx = np.mgrid[0:96, 0:256]
    img = (0.5 + 0.4 * np.sin(yy / 9.0) * np.cos(xx / 23.0) + 0.05 * rng.standard_normal((96, 256)))
    prob = np.clip(np.exp(-((np.mgrid[0:12, 0:32][0] - 6) ** 2 + (np.mgrid[0:12, 0:32][1] - 16) ** 2) / 30.0),
                   0, 1)
    np.savez(res / "images" / "case01.npz", image=img.astype("float32"), prob=prob.astype("float32"))
    rows = []
    for run in range(5):
        y = rng.integers(0, 2, 80)
        s = np.clip(0.35 * y + 0.65 * rng.random(80), 0, 1)
        rows += [{"model": "model_a", "run": run, "y_true": int(a), "y_score": float(b)} for a, b in zip(y, s)]
    pd.DataFrame(rows).to_csv(res / "scores" / "roc_runs.csv", index=False)
    cls = ["normal", "lesion_a", "lesion_b"]
    counts = [[40, 3, 2], [4, 30, 5], [0, 0, 0]]  # lesion_b absent -> hatched row
    pd.DataFrame([{"truth": t, "prediction": p, "count": counts[i][j]}
                  for i, t in enumerate(cls) for j, p in enumerate(cls)]).to_csv(
        res / "tables" / "confusion.csv", index=False)


@needs_scipilot
def test_template_runs_end_to_end(tmp_path):
    proj = tmp_path / "proj"
    (proj / "scripts").mkdir(parents=True)
    shutil.copy2(TEMPLATE, proj / "scripts" / "fig1.py")
    toml = TEMPLATE_TOML.read_text(encoding="utf-8")
    toml = toml.replace('scipilot_scripts = "~/.claude/skills/scipilot-medimg-figure-skill/scripts"',
                        f'scipilot_scripts = "{SCIPILOT.as_posix()}"')
    (proj / "figkit.toml").write_text(toml, encoding="utf-8")
    _synthetic_inputs(proj / "results")  # data_root = "results" in the template toml

    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "FIGKIT_TOML")}
    env["FIGKIT_LIB"] = str(LIB)
    env["MPLBACKEND"] = "Agg"
    r = subprocess.run([sys.executable, str(proj / "scripts" / "fig1.py")], cwd=tmp_path, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    assert r.returncode == 0, f"template failed:\n{r.stdout}\n{r.stderr}"

    out = proj / "out"
    for ext in ("pdf", "svg", "png"):
        f = out / "figures" / "main" / f"fig1.{ext}"
        assert f.is_file() and f.stat().st_size > 0, f
    for pid in "abc":
        for ext in ("pdf", "svg"):
            f = out / "panels" / "fig1" / f"fig1_{pid}.{ext}"
            assert f.is_file() and f.stat().st_size > 0, f
    src = json.loads((out / "figures" / "main" / "fig1.source.json").read_text(encoding="utf-8"))
    assert [p["id"] for p in src["values"]["panels"]] == ["a", "b", "c"]
    assert src["values"]["c_absent"] == ["lesion_b"]
    assert (out / "figures" / "main" / "fig1.caption.md").is_file()
