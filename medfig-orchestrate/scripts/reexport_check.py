"""Re-export figure scripts on the main checkout and verify expected outputs.

Usage:
  python reexport_check.py --root <main checkout> --python <interpreter>
                           [--allow-stale] SCRIPT=OUT1,OUT2 [SCRIPT=OUT ...]

Each script runs with cwd=<root>. Afterwards every expected output (relative to
<root>) must exist and must have been rewritten by this run; an output that
existed before and was not touched is "stale". Prints one JSON summary
(ran, failed, missing, stale). Exit 0 = clean; 1 = failed script (nonzero
exit or --timeout exceeded), missing output, or stale output (unless
--allow-stale); 2 = usage error, including a script/output path outside root
and a root that is a linked worktree (re-export must happen on the main
checkout). A root that is not a git repo skips the worktree check.
Per-panel exports (out/panels/<fig>/<fig>_<panel>.pdf/.svg) are listed as
outputs like any other file.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def usage(msg):
    print(msg, file=sys.stderr)
    raise SystemExit(2)


def is_linked_worktree(root):
    """True when root is a linked worktree (git-dir differs from common dir)."""
    def rev(flag):
        p = subprocess.run(["git", "-C", str(root), "rev-parse", flag],
                           capture_output=True, text=True)
        return (root / p.stdout.strip()).resolve() if p.returncode == 0 else None
    gd, cd = rev("--git-dir"), rev("--git-common-dir")
    return gd is not None and cd is not None and gd != cd


def parse_item(item):
    script, sep, outs = item.partition("=")
    if not sep or not script or not outs:
        usage(f"expected SCRIPT=OUT1,OUT2 but got: {item}")
    return script, [o for o in outs.split(",") if o]


def snapshot(path):
    st = path.stat() if path.exists() else None
    return (st.st_mtime_ns, st.st_size) if st else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--allow-stale", action="store_true")
    ap.add_argument("--timeout", type=float, default=1800)
    ap.add_argument("items", nargs="+", metavar="SCRIPT=OUT1,OUT2")
    a = ap.parse_args(argv)

    root = a.root.resolve()
    if not root.is_dir():
        usage(f"root not found: {root}")
    if is_linked_worktree(root):
        usage(f"root is a linked git worktree, not the main checkout: {root}")

    items = list(map(parse_item, a.items))
    for script, outs in items:
        for rel in [script, *outs]:
            p = (root / rel).resolve()
            if p != root and root not in p.parents:
                usage(f"path outside root: {rel}")

    summary = {"root": str(root), "ran": [], "failed": [], "missing": [], "stale": []}
    for script, outs in items:
        if not (root / script).is_file():
            summary["failed"].append({"script": script, "returncode": None,
                                      "error": "script not found"})
            summary["missing"].extend(outs)
            continue
        before = {o: snapshot(root / o) for o in outs}
        summary["ran"].append(script)
        try:
            p = subprocess.run([a.python, script], cwd=root, capture_output=True,
                               text=True, timeout=a.timeout)
        except subprocess.TimeoutExpired:
            summary["failed"].append({"script": script, "returncode": None,
                                      "error": "timeout", "timeout_s": a.timeout})
            p = None
        if p is not None and p.returncode != 0:
            summary["failed"].append({"script": script, "returncode": p.returncode,
                                      "stderr_tail": p.stderr[-2000:]})
        for o in outs:
            now = snapshot(root / o)
            if now is None:
                summary["missing"].append(o)
            elif before[o] is not None and now == before[o]:
                summary["stale"].append(o)

    bad = summary["failed"] or summary["missing"] or (
        summary["stale"] and not a.allow_stale)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
