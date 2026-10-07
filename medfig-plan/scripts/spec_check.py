"""Spec redundancy / completeness check for a medfig-plan design spec (markdown).

Per figure (``### Fig ...`` / ``### S...`` headings) and panel (``- **a ...**`` bullets with ``claim：`` /
``data：`` / ``chart：`` / ``reason：`` / ``caption：`` / ``counterfactual：`` sub-bullets) it reports:
missing or empty fields; two panels of one figure with the same claim; the same data reference drawn with
two different charts in one figure; duplicate panel letters. Two binding rules (medfig-plan S6 / S7):

- S7: a MAIN figure (heading ``Fig`` / ``Figure``, not ``S`` / ``Supp``) with a panel whose claim or chart
  reports discriminative performance (AUC, BACC, accuracy, sensitivity, specificity, recall, F1, 判别, 性能)
  must have a panel whose chart is a ROC or PR curve (exceedance / intervention curves do not count), or a figure-level
  ``- curve_exempt：<reason>`` line directly under the heading.
- S6: an imaging-case panel (chart mentions 影像 / 病例 / B-scan / image grid / case matrix / 病例矩阵) needs a
  ``case_selection：`` field with a seed (``seed = N``), misclassified cases (误判 / 错例 / misclassified) and
  >= 12 cases per group (``每组 N`` / ``N cases per group`` / ``× N``) -- unless it says ``exempt: <reason>``.

Idea after yinliang420/Scientific_Illustration
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
_FIELD = re.compile(r"^\s*-\s+(claim|data|chart|reason|caption|counterfactual|colour|panel_file|case_selection)"
                    r"\s*[：:]\s*(.*)$")
_EXEMPT = re.compile(r"^\s*-\s+curve_exempt\s*[：:]\s*(.*)$")
_MAIN = re.compile(r"^(?:Fig|Figure)\.?\s*\d", re.I)  # "Fig 3" yes, "Fig S3" / "S3" no
_PERF = re.compile(r"(?<![A-Za-z])(?:AUC|AUROC|BACC|accuracy|sensitivity|specificity|recall|F1)(?![A-Za-z])"
                   r"|判别|性能", re.I)
_CURVE = re.compile(r"(?<![A-Za-z])(?:ROC|PR)(?![A-Za-z])|precision[-–‐ ]recall|受试者工作特征")  # discrimination curves only
_IMAGING = re.compile(r"影像|病例|B-scan|image grid|case matrix|病例矩阵", re.I)
_SEED = re.compile(r"seed\s*[=:：]?\s*\d+", re.I)
_ERRCASE = re.compile(r"误判|错例|misclassified", re.I)
_PER_GROUP = re.compile(r"每组\s*(\d+)|(\d+)\s*cases?\s*per\s*group|×\s*(\d+)", re.I)
_CASE_EXEMPT = re.compile(r"exempt\s*[：:]\s*\S", re.I)
MIN_CASES_PER_GROUP = 12


def _norm(s):
    return " ".join(re.sub(r"[`*_，。,.;；:：()（）]", " ", s.lower()).split())


def parse(text, exempt=None):
    """{figure title: {panel letter: {field: value}}}; duplicate letters are kept as 'a#2'. Figure-level
    ``curve_exempt`` lines (before the first panel) go into ``exempt`` {figure title: reason} when given."""
    figs, fig, panel = {}, None, None
    for line in text.splitlines():
        m = _FIG.match(line)
        if m:
            fig = m.group(1).strip(); figs[fig] = {}; panel = None
            continue
        m = _EXEMPT.match(line)
        if m and fig is not None and panel is None:
            if exempt is not None and m.group(1).strip():
                exempt[fig] = m.group(1).strip()
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


def _per_group(text):
    return [int(next(g for g in m.groups() if g)) for m in _PER_GROUP.finditer(text)]


def _case_issues(fig, p, f):
    sel = f.get("case_selection", "")
    if not sel:
        return [f"{fig} {p}: imaging-case panel without case_selection (S6: stratified random, seed, "
                f">= {MIN_CASES_PER_GROUP} cases per group incl. misclassified; or 'exempt: <reason>')"]
    if _CASE_EXEMPT.search(sel):
        return []
    out = []
    if not _SEED.search(sel):
        out.append(f"{fig} {p}: case_selection has no fixed seed ('seed = N')")
    if not _ERRCASE.search(sel):
        out.append(f"{fig} {p}: case_selection does not include misclassified cases (误判 / misclassified)")
    n = _per_group(sel)
    if not n or max(n) < MIN_CASES_PER_GROUP:
        out.append(f"{fig} {p}: case_selection needs >= {MIN_CASES_PER_GROUP} cases per group "
                   f"('每组 N' / 'N cases per group'), got {n or 'none'}")
    return out


def check(text):
    issues = []
    exempt = {}
    for fig, panels in parse(text, exempt).items():
        if _MAIN.match(fig) and fig not in exempt:
            perf = [p for p, f in panels.items() if _PERF.search(f.get("claim", "") + " " + f.get("chart", ""))]
            if perf and not any(_CURVE.search(f.get("chart", "")) for f in panels.values()):
                issues.append(f"{fig}: panels {perf} report discriminative performance but no panel is a ROC / PR "
                              "curve (S7) -- add one, or write '- curve_exempt：<reason>' under the heading")
        for p, f in panels.items():
            if _IMAGING.search(f.get("chart", "")):
                issues += _case_issues(fig, p, f)
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
