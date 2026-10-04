"""Check a medfig-outline ``outline.yaml`` against the finished figure set.

Checks: every registered number matches its source (``source.json`` key path or table cell, rounded to the
written decimals); every number written in a Results paragraph is registered; every cited Fig panel / Table
exists; every main figure is covered by a Results section; Methods ``focus`` has no result numbers; Results
titles are one-sentence findings without numbers; banned words, development history and project code
patterns (``figkit.toml [qa] forbidden_patterns``; allowed only inside "（内部代号 …）") never appear.

Usage: python outline_check.py outline.yaml --project <root> [--figkit-toml <toml>]
Exit 1 when any issue is found. Only reads.
"""
import argparse
import csv
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
LIB = HERE.parents[1] / "medfig-render" / "lib"   # source checkout and installed skills share this layout
if str(LIB) not in sys.path:
    sys.path.insert(0, str(LIB))
from figkit import qa  # noqa: E402

# Chinese development-history words (qa.DEV_HISTORY covers English)
DEV_ZH = {"预注册": r"预注册", "早期版本": r"早期(?:版本|模型)", "修复": r"修复(?:后|前)?的?(?:模型|版本|主线|三分类|决策头)|(?:修复前|修复后)",
          "重拟合": r"重拟合", "口径裁决": r"口径裁决", "开发阶段": r"开发(?:阶段|日志|日记)"}
NUM = re.compile(r"(?<![\w./])[+−-]?\d[\d,]*(?:\.\d+)?(?:/\d+)?%?")
REF = re.compile(r"^(Fig|S)(\d+)([a-z](?:-[a-z])?)?$|^(T\d+|ST\d+)$")
CODE_NOTE = re.compile(r"（内部代号[^）]*）")
VAGUE_TITLE = re.compile(r"^(?:results? of|overview of|analysis of|performance of|.* results?)\b", re.I)


def _texts(sec, results):
    """Yield (where, text) for every prose field of a section."""
    sid = sec["id"]
    if results:
        yield f"Results {sid} title", sec.get("title", "")
        yield f"Results {sid} subtitle", sec.get("subtitle", "")
        for p in sec.get("paragraphs", []):
            yield f"Results {sid} {p.get('label', '')} claim", p.get("claim", "")
            for t in p.get("points", []):
                yield f"Results {sid} {p.get('label', '')}", t
        for it in sec.get("items", []):
            yield f"Results {sid} item {it.get('ref')}", it.get("what", "")
        for t in sec.get("boundaries", []):
            yield f"Results {sid} boundary", t
    else:
        yield f"Methods {sid} title", sec.get("title", "")
        for blk in sec.get("focus", []):
            yield f"Methods {sid} focus", blk.get("topic", "")
            for t in blk.get("points", []):
                yield f"Methods {sid} focus", t
        for t in sec.get("foreshadow", []):
            yield f"Methods {sid} foreshadow", t


def _nodes(secs):
    """Every section and subsection, depth-first (``subsections:`` nest one level or more)."""
    for sec in secs or []:
        yield sec
        yield from _nodes(sec.get("subsections"))


def _tree(secs, depth=0, parents=()):
    """(section, depth, parent chain) depth-first, for rendering and folder paths."""
    for sec in secs or []:
        yield sec, depth, parents
        yield from _tree(sec.get("subsections"), depth + 1, (*parents, sec))


def _main_figs_in(sec, main):
    figs = set()
    for s in _nodes([sec]):
        refs = [i["ref"] for i in s.get("items", []) if isinstance(i, dict)]
        for p in s.get("paragraphs", []):
            refs += p.get("cites", [])
        for r in refs:
            figs |= {n for n, _ in (_expand(r) or []) if n in main}
    return figs


def _structure(o, lim):
    """Plan the outline by argument, not one section per figure (outline_format.md section 6)."""
    out = []
    M, R = o.get("methods", []), o.get("results", [])
    main = set(o.get("main_figures", []))
    if len(R) > lim["results_max_sections"]:
        out.append(f"structure: {len(R)} top-level Results sections (max {lim['results_max_sections']}); group them "
                   "by the argument and use subsections")
    if R and len(R) < lim["results_min_sections"] and not str(o.get("results_fewer_sections_reason", "")).strip():
        out.append(f"structure: only {len(R)} top-level Results sections (aim for {lim['results_min_sections']}-"
                   f"{lim['results_max_sections']}); split over-merged sections, or state why the study's argument "
                   "needs fewer in results_fewer_sections_reason")
    if len(M) == len(R) and len(R) >= 4 and all(len(_main_figs_in(s, main)) == 1 for s in R):
        out.append("structure: Methods and Results have the same number of sections and every Results section is "
                   "one figure -- plan Results by the argument (one section may use several figures)")
    for kind, secs in (("Methods", M), ("Results", R)):
        for sec, depth, parents in _tree(secs):
            subs = sec.get("subsections") or []
            if parents and not str(sec["id"]).startswith(str(parents[-1]["id"]) + "."):
                out.append(f"structure: {kind} {sec['id']} is not numbered under {parents[-1]['id']}")
            if len(subs) == 1:
                out.append(f"structure: {kind} {sec['id']} has a single subsection; merge it into the parent")
            if not subs:
                n = (sum(len(b.get("points", [])) for b in sec.get("focus", [])) if kind == "Methods"
                     else sum(len(p.get("points", [])) for p in sec.get("paragraphs", [])))
                if n < 2:
                    out.append(f"structure: {kind} {sec['id']} has {n} point(s); a section needs at least 2 "
                               "(otherwise merge it)")
    return out


def _expand(ref):
    """'Fig2a-c' -> [('fig2', 'a'), ('fig2', 'b'), ('fig2', 'c')]; 'S5' -> [('s05', None)]; 'T1' -> table."""
    m = REF.match(ref)
    if not m:
        return None
    if m.group(4):
        return [("table", m.group(4))]
    name = f"fig{int(m.group(2))}" if m.group(1) == "Fig" else f"s{int(m.group(2)):02d}"
    letters = m.group(3)
    if not letters:
        return [(name, None)]
    if "-" in letters:
        a, b = letters.split("-")
        return [(name, chr(c)) for c in range(ord(a), ord(b) + 1)]
    return [(name, letters)]


def _source_json(root, figures_root, name):
    hits = list((root / figures_root).glob(f"*/{name}.source.json")) + list((root / figures_root).glob(f"{name}.source.json"))
    return hits[0] if hits else None


def _panel_ids(src):
    v = json.loads(src.read_text(encoding="utf-8")).get("values", {})
    ids = {str(p.get("id")) for p in v.get("panels", []) if isinstance(p, dict)}
    return ids


def _get(obj, path):
    for part in re.findall(r"[^.\[\]]+|\[\d+\]", path):
        if part.startswith("["):
            obj = obj[int(part[1:-1])]
        else:
            obj = obj[part]
    return obj


def _value(root, o, source):
    if source.startswith("table:"):
        _, rest = source.split(":", 1)
        fname, spec = rest.split(":", 1)
        col, _, filt = spec.partition("@")
        rows = list(csv.DictReader((root / o["tables_root"] / fname).open(encoding="utf-8")))
        conds = [c.split("=", 1) for c in filt.split("&")] if filt else []
        hit = [r for r in rows if all(r.get(k) == v for k, v in conds)]
        if len(hit) != 1:
            raise KeyError(f"{len(hit)} rows match {filt!r} in {fname}")
        return float(hit[0][col])
    fname, path = source.split(":", 1)
    src = _source_json(root, o["figures_root"], fname.replace(".source.json", ""))
    if src is None:
        raise KeyError(f"{fname} not found")
    return _get(json.loads(src.read_text(encoding="utf-8")), path)


def _num(text):
    """(value, decimals, is_percent) of a written number; '1/3' -> exact fraction, compared at 6 dp."""
    t = text.replace("−", "-").replace(",", "").lstrip("+")
    pct = t.endswith("%")
    t = t.rstrip("%")
    if "/" in t:
        a, b = t.split("/")
        return float(a) / float(b), 6, pct
    dec = len(t.split(".")[1]) if "." in t else 0
    return float(t), dec, pct


def _matches(written, value, tol=None, magnitude=False):
    """``magnitude``: the text states the size of a signed source value (e.g. "低约 0.047" for −0.0472)."""
    x, dec, pct = _num(written)
    v = float(value) * (100 if pct else 1)
    if magnitude:
        v = abs(v)
    if written.startswith("+") and v < 0 or written.startswith(("−", "-")) and v > 0:
        return False  # sign written explicitly must agree
    if tol is not None:
        return abs(x - v) <= float(tol)
    return abs(round(v, dec) - x) < 10 ** (-dec) / 2 + 1e-12


def _strip_refs(text):
    """Remove panel / table / section references and ordinal labels before scanning for numbers."""
    t = re.sub(r"\b(?:Fig|S|ST|T)\s?\d+[a-z]?(?:[–-][a-z])?\b", " ", text)
    t = re.sub(r"\b\d+\.\d+\s*节", " ", t)
    t = re.sub(r"\b[0-9]+ ?(?:个|种|类|项|名|张|组|级|段|seed|seeds|折)\b", lambda m: m.group(0), t)
    return t


def check(outline_path, project, figkit_toml=None):
    o = yaml.safe_load(Path(outline_path).read_text(encoding="utf-8"))
    root = Path(project)
    cfg = None
    if figkit_toml:
        from figkit import config
        cfg = config.load(figkit_toml)
    out = []
    # ---- numbers
    registered = {}
    for n in o.get("numbers", []):
        registered.setdefault(n["text"], []).append(n)
        try:
            v = _value(root, o, n["source"])
        except (KeyError, IndexError, ValueError, FileNotFoundError, TypeError) as e:
            out.append(f"number {n['text']!r}: source {n['source']!r} not readable ({e})")
            continue
        if not _matches(n["text"], v, n.get("tol"), n.get("magnitude", False)):
            out.append(f"number {n['text']!r}: source value {v} ({n['source']}) does not round to it")
    allow_all = set(o.get("allow_numbers", []))  # design constants / interval notation (95%, 16 concepts)
    for sec in _nodes(o.get("results", [])):
        for where, text in _texts(sec, True):
            if where.endswith("title") or "boundary" in where:
                continue
            for m in NUM.findall(_strip_refs(text)):
                if m in allow_all:
                    continue
                if m.rstrip("%").replace(",", "").isdigit() and len(m.rstrip("%").replace(",", "")) <= 1:
                    continue  # single digits: counts of panels / seeds / classes
                if m not in registered:
                    out.append(f"{where}: number {m!r} not registered in numbers")
    # ---- references and coverage
    covered = set()
    for results, secs in ((False, _nodes(o.get("methods", []))), (True, _nodes(o.get("results", [])))):
        for sec in secs:
            refs = list(sec.get("items", [])) if not results else [i["ref"] for i in sec.get("items", [])]
            for p in sec.get("paragraphs", []):
                refs += p.get("cites", [])
            for ref in refs:
                ex = _expand(ref)
                if ex is None:
                    out.append(f"{sec['id']}: reference {ref!r} not understood (Fig2a, Fig2a-c, S5, T1, ST05)")
                    continue
                for name, letter in ex:
                    if name == "table":
                        if not (root / o["tables_root"] / f"{letter}.csv").is_file():
                            out.append(f"{sec['id']}: table {ref} not found")
                        continue
                    src = _source_json(root, o["figures_root"], name)
                    if src is None:
                        out.append(f"{sec['id']}: figure {ref} not found")
                        continue
                    if results:
                        covered.add(name)
                    if letter and letter not in _panel_ids(src):
                        out.append(f"{sec['id']}: panel {ref} not found ({name} has {sorted(_panel_ids(src))})")
    for f in o.get("main_figures", []):
        if f not in covered:
            out.append(f"main figure {f} not covered by any Results section")
    # ---- Methods without result numbers
    for sec in _nodes(o.get("methods", [])):
        allow = set(sec.get("allow_numbers", [])) | set(o.get("allow_numbers", []))
        for where, text in _texts(sec, False):
            if not where.endswith("focus"):
                continue
            for m in NUM.findall(_strip_refs(text)):
                if m in allow or (m.isdigit() and len(m) <= 1):
                    continue
                out.append(f"{where}: result-like number {m!r} (Methods describe structure; allow_numbers if not a result)")
    # ---- Results titles: top-level sections state the finding in one sentence; subsections may be short labels
    for sec in o.get("results", []):
        t = sec.get("title", "")
        if VAGUE_TITLE.match(t) or len(t.split()) < 5:
            out.append(f"Results {sec['id']} title {t!r}: write a one-sentence finding, not a topic")
    for sec in _nodes(o.get("results", [])):
        t = sec.get("title", "")
        if NUM.search(t):
            out.append(f"Results {sec['id']} title {t!r}: no number in the title (numbers go in the paragraphs)")
    # ---- wording
    for results, secs in ((False, _nodes(o.get("methods", []))), (True, _nodes(o.get("results", [])))):
        for sec in secs:
            for where, text in _texts(sec, results):
                bare = CODE_NOTE.sub("", text)
                out += [f"{where}: banned word {w!r}" for w in qa.banned_in_text(bare, cfg)]
                out += [f"{where}: development history {w!r} (mainline_rules.md)" for w in qa.dev_history_in_text(bare, cfg)]
                out += [f"{where}: development history {k!r} (mainline_rules.md)" for k, p in DEV_ZH.items()
                        if re.search(p, bare)]
                if cfg is not None:
                    out += [f"{where}: project code pattern {p!r}" for p in qa.forbidden_in_text(bare, cfg)]
    # ---- style: an outline is writing guidance, not a data dump (references/outline_format.md §5)
    out += _style(o)
    out += _structure(o, {**STYLE, **(o.get("style") or {})})
    return out


STYLE = dict(point_max_chars=70, point_max_numbers=2, paragraph_max_points=3, paragraph_max_numbers=4,
             section_max_paragraphs=3, opener_max_repeat=2, results_min_sections=5, results_max_sections=8)
OPENER = re.compile(r"^\s*(引用|根据|如|见)\s*(?:Fig|S|ST|T)\s?\d", re.I)


def _style(o):
    """Length / density / repetition limits; thresholds overridable with a top-level ``style:`` block."""
    lim = {**STYLE, **(o.get("style") or {})}
    out = []
    allow_all = set(o.get("allow_numbers", []))

    def nums(t):
        # a range "0.929–0.938" / "0.917 至 0.941" counts as one number
        t = re.sub(r"(\d)\s*(?:–|—|至|到|~)\s*[+−-]?(?=\d)", r"\1 ", _strip_refs(t))
        t = re.sub(r"(\d[\d.,]*%?) (\d[\d.,]*%?)", r"\1", t)
        return [m for m in NUM.findall(t) if m not in allow_all
                and not (m.rstrip("%").replace(",", "").isdigit() and len(m.rstrip("%").replace(",", "")) <= 1)]

    for kind, secs in (("Methods", _nodes(o.get("methods", []))), ("Results", _nodes(o.get("results", [])))):
        for sec in secs:
            blocks = ([(p.get("label", ""), p.get("points", [])) for p in sec.get("paragraphs", [])] if kind == "Results"
                      else [(b.get("topic", ""), b.get("points", [])) for b in sec.get("focus", [])])
            if kind == "Results" and len(blocks) > lim["section_max_paragraphs"]:
                out.append(f"style: Results {sec['id']} has {len(blocks)} paragraphs (max {lim['section_max_paragraphs']}; "
                           "merge or move detail to the figure caption)")
            openers = {}
            for label, pts in blocks:
                if len(pts) > lim["paragraph_max_points"]:
                    out.append(f"style: {kind} {sec['id']} {label}: {len(pts)} points (max {lim['paragraph_max_points']})")
                if kind == "Results" and sum(len(nums(t)) for t in pts) > lim["paragraph_max_numbers"]:
                    out.append(f"style: {kind} {sec['id']} {label}: {sum(len(nums(t)) for t in pts)} numbers "
                               f"(max {lim['paragraph_max_numbers']}; keep the key ones, point to the table for the rest)")
                for t in pts:
                    if len(t) > lim["point_max_chars"]:
                        out.append(f"style: {kind} {sec['id']} {label}: point is {len(t)} chars (max "
                                   f"{lim['point_max_chars']}; one instruction per point): {t[:30]}…")
                    if kind == "Results" and len(nums(t)) > lim["point_max_numbers"]:
                        out.append(f"style: {kind} {sec['id']} {label}: {len(nums(t))} numbers in one point (max "
                                   f"{lim['point_max_numbers']}): {t[:30]}…")
                    if OPENER.match(t):
                        out.append(f"style: {kind} {sec['id']} {label}: point opens with a citation ({t[:12]}…); "
                                   "start with what to write (说明 / 对比 / 强调 …), put the citation in cites")
                    k = t.strip()[:2]
                    openers[k] = openers.get(k, 0) + 1
            for k, n in openers.items():
                if n > lim["opener_max_repeat"] + 1:
                    out.append(f"style: {kind} {sec['id']}: {n} points start with {k!r}; vary the wording")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("outline")
    ap.add_argument("--project", required=True)
    ap.add_argument("--figkit-toml")
    a = ap.parse_args(argv)
    issues = check(a.outline, a.project, a.figkit_toml)
    for i in issues:
        print(i)
    print(f"{len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
