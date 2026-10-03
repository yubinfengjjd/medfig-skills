"""Tests for medfig-orchestrate/scripts (new_worktree.py, reexport_check.py).

All tests build a throwaway git repo under pytest's tmp_path; no project data.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
NEW_WT = SCRIPTS / "new_worktree.py"
REEXPORT = SCRIPTS / "reexport_check.py"


def git(cwd, *args):
    cmd = ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args]
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    git(root, "init", "-q", "-b", "master")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    git(root, "add", "README.md")
    git(root, "commit", "-q", "-m", "init")
    return root


def run(script, *args):
    return subprocess.run([sys.executable, str(script), *map(str, args)],
                          capture_output=True, text=True)


def new_wt(repo, task, wt_root):
    p = run(NEW_WT, "--repo", repo, "--task", task, "--wt-root", wt_root)
    info = json.loads(p.stdout) if p.stdout.strip() else {}
    return p, info


# ---------------------------------------------------------------- new_worktree
def test_creates_branch_and_worktree_from_master_head(repo, tmp_path):
    wt_root = tmp_path / "wt"
    p, info = new_wt(repo, 3, wt_root)
    assert p.returncode == 0, p.stderr
    assert info["status"] == "created"
    assert info["branch"] == "task3"
    assert Path(info["path"]) == (wt_root / "task3").resolve()
    assert Path(info["path"], "README.md").exists()
    assert info["base_sha"] == git(repo, "rev-parse", "master")
    assert git(repo, "rev-parse", "task3") == info["base_sha"]


def test_second_call_reports_existing_instead_of_failing(repo, tmp_path):
    wt_root = tmp_path / "wt"
    new_wt(repo, 3, wt_root)
    p, info = new_wt(repo, 3, wt_root)
    assert p.returncode == 0, p.stderr
    assert info["status"] == "exists"
    assert Path(info["path"]) == (wt_root / "task3").resolve()
    # still exactly one worktree for task3
    listing = git(repo, "worktree", "list", "--porcelain")
    assert listing.count("refs/heads/task3") == 1


def test_existing_branch_without_worktree_is_attached(repo, tmp_path):
    git(repo, "branch", "task4", "master")
    p, info = new_wt(repo, 4, tmp_path / "wt")
    assert p.returncode == 0, p.stderr
    assert info["status"] == "attached"
    assert Path(info["path"], "README.md").exists()


def test_occupied_non_worktree_path_fails(repo, tmp_path):
    wt_root = tmp_path / "wt"
    (wt_root / "task5").mkdir(parents=True)
    (wt_root / "task5" / "junk.txt").write_text("x", encoding="utf-8")
    p, info = new_wt(repo, 5, wt_root)
    assert p.returncode != 0
    assert "task5" in p.stderr


def test_missing_base_ref_fails(repo, tmp_path):
    p = run(NEW_WT, "--repo", repo, "--task", 6, "--wt-root", tmp_path / "wt",
            "--base", "no-such-branch")
    assert p.returncode != 0
    assert "no-such-branch" in p.stderr


# ------------------------------------------------------------- reexport_check
WRITER = """
import sys
from pathlib import Path
for rel in sys.argv[1:]:
    p = Path(rel); p.parent.mkdir(parents=True, exist_ok=True); p.write_text("ok")
"""


def make_script(root, name, writes, fail=False):
    body = WRITER + ("\nraise SystemExit(3)\n" if fail else "")
    body += f"\n# outputs: {writes}\n"
    # the script writes the given outputs relative to cwd (= project root)
    src = body.replace("sys.argv[1:]", repr(list(writes)))
    p = root / "figures" / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(src, encoding="utf-8")
    return p


def reexport(root, *items, extra=()):
    return run(REEXPORT, "--root", root, "--python", sys.executable,
               *extra, *items)


def test_all_outputs_present_passes(repo):
    make_script(repo, "fig1.py", ["out/fig1.pdf", "out/fig1.source.json"])
    p = reexport(repo, "figures/fig1.py=out/fig1.pdf,out/fig1.source.json")
    assert p.returncode == 0, p.stdout + p.stderr
    assert json.loads(p.stdout)["missing"] == []


def test_missing_output_is_detected(repo):
    make_script(repo, "fig2.py", ["out/fig2.pdf"])
    p = reexport(repo, "figures/fig2.py=out/fig2.pdf,out/fig2.png")
    assert p.returncode == 1
    assert json.loads(p.stdout)["missing"] == ["out/fig2.png"]


def test_failing_script_is_reported(repo):
    make_script(repo, "fig3.py", ["out/fig3.pdf"], fail=True)
    p = reexport(repo, "figures/fig3.py=out/fig3.pdf")
    assert p.returncode == 1
    summary = json.loads(p.stdout)
    assert summary["failed"][0]["script"] == "figures/fig3.py"
    assert summary["failed"][0]["returncode"] == 3


def test_stale_output_counts_as_missing_unless_allowed(repo):
    make_script(repo, "fig4.py", [])  # writes nothing
    (repo / "out").mkdir()
    (repo / "out" / "fig4.pdf").write_text("old", encoding="utf-8")
    p = reexport(repo, "figures/fig4.py=out/fig4.pdf")
    assert p.returncode == 1
    assert json.loads(p.stdout)["stale"] == ["out/fig4.pdf"]
    p = reexport(repo, "figures/fig4.py=out/fig4.pdf", extra=["--allow-stale"])
    assert p.returncode == 0, p.stdout


def test_timeout_is_reported_in_json(repo):
    p = repo / "figures" / "slow.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
    r = reexport(repo, "figures/slow.py=out/slow.pdf", extra=["--timeout", "1"])
    assert r.returncode == 1
    summary = json.loads(r.stdout)
    assert summary["failed"][0]["error"] == "timeout"
    assert summary["missing"] == ["out/slow.pdf"]


def test_output_outside_root_is_usage_error(repo):
    make_script(repo, "fig6.py", ["out/fig6.pdf"])
    p = reexport(repo, "figures/fig6.py=../escape.pdf")
    assert p.returncode == 2
    assert "outside root" in p.stderr


def test_linked_worktree_root_is_refused(repo, tmp_path):
    _, info = new_wt(repo, 7, tmp_path / "wt")
    wt = Path(info["path"])
    make_script(wt, "fig5.py", ["out/fig5.pdf"])
    p = reexport(wt, "figures/fig5.py=out/fig5.pdf")
    assert p.returncode == 2
    assert "worktree" in p.stderr
