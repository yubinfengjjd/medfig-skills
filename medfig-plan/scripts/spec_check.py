"""Spec redundancy / completeness check for a medfig-plan design spec (markdown).

Per figure (``### Fig ...`` / ``### S...`` headings) and panel (``- **a ...**`` bullets with ``claim：`` /
``data：`` / ``chart：`` / ``reason：`` / ``caption：`` / ``counterfactual：`` sub-bullets) it reports:
missing or empty fields; two panels of one figure with the same claim; the same data reference drawn with
two different charts in one figure; duplicate panel letters. Idea after yinliang420/Scientific_Illustration
``huitu/review.py check_redundancy`` (MIT licence), re-implemented for the medfig spec format.

Usage: python spec_check.py docs/<date>-figure-set-design.md   (exit 1 when any issue is found)
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

FIELDS = ("claim", "data", "chart", "reason", "caption", "counterfactual")
_FIG = re.compile(r"^#{2,4}\s+((?:Fig|Figure|S|Supp)[^\n]*)")
_PANEL = re.compile(r"^\s*-\s+\*\*([a-z])\b[^*]*\*\*")
_FIELD = re.compile(r"^\s*-\s+(claim|data|chart|reason|caption|counterfactual|colour|panel_file)\s*[：:]\s*(.*)$")


def _norm(s):
    return " ".join(re.sub(r"[`*_，。,.;；:：()（）]", " ", s.lower()).split())


def parse(text):
    """{figure title: {panel letter: {field: value}}}; duplicate letters are kept as 'a#2'."""
    figs, fig, panel = {}, None, None
    for line in text.splitlines():
        m = _FIG.match(line)
        if m:
            fig = m.group(1).strip(); figs[fig] = {}; panel = None
            continue
        m = _PANEL.match(line)
        if m and fig is not None:
            p = m.group(1)
            k, i = p, 2
            while k in figs[fig]:
                k = f"{p}#{i}"; i += 1
            figs[fig][k] = {}; panel = k
            continue
        m = _FIELD.match(line)
        if m and fig is not None and panel is not None:
            figs[fig][panel][m.group(1)] = m.group(2).strip()
    return figs


def check(text):
    issues = []
    for fig, panels in parse(text).items():
        for p, f in panels.items():
            if "#" in p:
                issues.append(f"{fig}: duplicate panel letter {p.split('#')[0]!r}")
            missing = [k for k in FIELDS if not f.get(k)]
            if missing:
                issues.append(f"{fig} {p}: missing / empty {missing}")
        claims, data = defaultdict(list), defaultdict(set)
        for p, f in panels.items():
            if f.get("claim"):
                claims[_norm(f["claim"])].append(p)
            if f.get("data") and f.get("chart"):
                ref = _norm(f["data"].split("·")[0])
                data[ref].add((_norm(f["chart"].split("；")[0].split(";")[0]), p))
        for c, ps in claims.items():
            if len(ps) > 1:
                issues.append(f"{fig}: panels {ps} make the same claim -- keep the clearest encoding or split it")
        for ref, charts in data.items():
            if len({c for c, _ in charts}) > 1:
                ps = sorted(p for _, p in charts)
                issues.append(f"{fig}: panels {ps} draw the same data ({ref!r}) with different charts -- one "
                              "should show a different view (difference, deviation, relationship) or go")
    return issues


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print(__doc__); return 2
    issues = check(Path(argv[0]).read_text(encoding="utf-8"))
    for i in issues:
        print("ISSUE", i)
    print(f"{len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
