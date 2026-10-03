"""Create or verify the git worktree + branch for task N (idempotent).

Usage:
  python new_worktree.py --repo <main checkout> --task N [--wt-root DIR]
                         [--base master] [--prefix task]

Prints one JSON object: status (created | attached | exists), branch, path,
base_sha, head_sha. Exit 0 on success; nonzero with a message on stderr when the
base ref is missing or the target path is occupied by something else.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def git(repo, *args, check=True):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {p.stderr.strip()}")
    return p


def worktrees(repo):
    """Map branch name -> resolved worktree path from `git worktree list`."""
    out, cur = {}, None
    for line in git(repo, "worktree", "list", "--porcelain").stdout.splitlines():
        if line.startswith("worktree "):
            cur = Path(line[len("worktree "):]).resolve()
        elif line.startswith("branch refs/heads/") and cur is not None:
            out[line[len("branch refs/heads/"):]] = cur
    return out


def fail(msg):
    print(msg, file=sys.stderr)
    raise SystemExit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--task", required=True)
    ap.add_argument("--wt-root", type=Path, help="default: <repo>/../wt")
    ap.add_argument("--base", default="master")
    ap.add_argument("--prefix", default="task")
    a = ap.parse_args(argv)

    repo = a.repo.resolve()
    branch = f"{a.prefix}{a.task}"
    wt_root = (a.wt_root or repo.parent / "wt").resolve()
    path = wt_root / branch

    base = git(repo, "rev-parse", "--verify", "--quiet", f"{a.base}^{{commit}}", check=False)
    if base.returncode != 0:
        fail(f"base ref not found: {a.base}")
    base_sha = base.stdout.strip()

    wts = worktrees(repo)
    if branch in wts:
        # Idempotent path: branch already checked out in a worktree -> report it.
        status, path = "exists", wts[branch]
    else:
        if path.exists() and any(path.iterdir()):
            fail(f"target path is occupied and is not a worktree of {branch}: {path}")
        has_branch = git(repo, "show-ref", "--verify", "--quiet",
                         f"refs/heads/{branch}", check=False).returncode == 0
        path.parent.mkdir(parents=True, exist_ok=True)
        if has_branch:
            git(repo, "worktree", "add", str(path), branch)
            status = "attached"
        else:
            git(repo, "worktree", "add", "-b", branch, str(path), base_sha)
            status = "created"

    head_sha = git(path, "rev-parse", "HEAD").stdout.strip()
    print(json.dumps({"status": status, "branch": branch, "path": str(path),
                      "base_sha": base_sha, "head_sha": head_sha}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
