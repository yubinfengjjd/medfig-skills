"""Portability: a copy of examples/minimal OUTSIDE the repository runs as plain ``python <script>``
subprocesses, locating figkit through FIGKIT_LIB (no repo-relative lib, no global install needed)."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

from conftest import needs_scipilot

REPO_RENDER = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_RENDER / "examples" / "minimal"
LIB = REPO_RENDER / "lib"
PANELS = ["a", "b", "c", "d"]


def _run(script, cwd, env):
    r = subprocess.run([sys.executable, str(script)], cwd=cwd, env=env,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
    assert r.returncode == 0, f"{script.name} failed:\n{r.stdout}\n{r.stderr}"


@needs_scipilot
def test_example_copy_runs_outside_repo(tmp_path):
    proj = tmp_path / "elsewhere" / "minimal"
    shutil.copytree(EXAMPLE, proj, ignore=shutil.ignore_patterns("out", "data", "__pycache__"))
    assert not (proj.parents[1] / "lib").exists()  # the repo-relative fallback is not available
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["FIGKIT_LIB"] = str(LIB)
    env["MPLBACKEND"] = "Agg"
    _run(proj / "make_data.py", proj, env)
    _run(proj / "figures" / "fig_demo.py", proj / "figures", env)
    _run(proj / "tables" / "table_demo.py", tmp_path, env)

    out = proj / "out"
    for ext in ("pdf", "svg", "png"):
        f = out / "figures" / "main" / f"fig_demo.{ext}"
        assert f.is_file() and f.stat().st_size > 0, f
    for pid in PANELS:
        for ext in ("pdf", "svg"):
            f = out / "panels" / "fig_demo" / f"fig_demo_{pid}.{ext}"
            assert f.is_file() and f.stat().st_size > 0, f
    for name in ("table_demo.csv", "table_demo.md", "table_demo.source.json"):
        assert (out / "tables" / name).is_file(), name
