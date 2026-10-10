"""Check a medfig-outline ``outline.yaml`` against the finished figure set.

Checks: every registered number matches its source (``source.json`` key path or table cell, rounded to the
written decimals); every number written in a Results paragraph is registered; every cited Fig panel / Table
exists; every main figure is covered by a Results section; Methods ``focus`` has no result numbers; Results
titles are one-sentence findings without numbers; banned words, development history and project code
patterns (``figkit.toml [qa] forbidden_patterns``; allowed only inside "（内部代号 …）") never appear.
Citation order (outline_format.md section 7): in reading order (Methods, then Results) main figures, main
tables, supplementary figures and supplementary tables are each first cited 1, 2, 3 ... and the panels of a
figure a, b, c ...; every exported asset and panel is cited (or listed under ``excluded`` with a reason);
Methods cite only ``design_assets``; every asset has a 图 / 表 line saying what it shows scientifically;
no plotting / table-building script is listed as code.

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
# citations written inside point text: "Fig 3a", "Fig S5b–c", "Table 2", "Table S5", "图 S1", "表 2"
TEXT_REF = re.compile(r"(?:Fig\.?|Figure|图)\s?(S?)(\d+)([a-z](?:[–-][a-z])?)?(?![\w])|(?:Table|表)\s?(S?)(\d+)(?!\d)")
DRAW_ROLES = {"绘图", "表格"}
DRAW_PATH = re.compile(r"^(?:figures|tables)/")
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


def _text_refs(text):
    """Canonical refs ('Fig3a', 'S5b-c', 'T2', 'ST05') mentioned inside prose, in order of appearance."""
    out = []
    for m in TEXT_REF.finditer(text or ""):
        if m.group(2):
            letters = (m.group(3) or "").replace("–", "-")
            out.append(("S" if m.group(1) else "Fig") + m.group(2) + letters)
        else:
            out.append((f"ST{int(m.group(5)):02d}" if m.group(4) else f"T{int(m.group(5))}"))
    return out


def _series(name):
    """('main_fig' | 'supp_fig' | 'main_table' | 'supp_table', number) of a canonical asset name."""
    if name.startswith("fig"):
        return "main_fig", int(name[3:])
    if name.startswith("ST"):
        return "supp_table", int(name[2:])
    if name.startswith("T"):
        return "main_table", int(name[1:])
    return "supp_fig", int(name[1:])


def _asset(name, letter):
    """Asset key for an expanded ref: fig2 / s05 for figures, T1 / ST05 for tables."""
    return letter if name == "table" else name


def _pretty(asset):
    kind, n = _series(asset)
    return {"main_fig": f"Fig {n}", "supp_fig": f"Fig S{n}", "main_table": f"Table {n}", "supp_table": f"Table S{n}"}[kind]


def _reading_order(o):
    """(section id, kind, ref) for every citation in reading order: Methods then Results, depth first; inside a
    Results paragraph the claim's cites come first, then refs written in its points; a Methods section cites the
    refs written in its ``focus`` first, then its ``cites`` and ``items`` (Methods have no paragraphs)."""
    for kind, secs in (("Methods", o.get("methods", [])), ("Results", o.get("results", []))):
        for sec in _nodes(secs):
            if kind == "Methods":
                refs = []
                for blk in sec.get("focus", []):
                    for t in blk.get("points", []):
                        refs += _text_refs(t)
                refs += list(sec.get("cites", []))
                refs += [i["ref"] if isinstance(i, dict) else i for i in sec.get("items", [])]
                yield from ((sec["id"], kind, r) for r in refs)
            for p in sec.get("paragraphs", []):
                refs = list(p.get("cites", []))
                refs += _text_refs(p.get("claim", ""))
                for t in p.get("points", []):
                    refs += _text_refs(t)
                yield from ((sec["id"], kind, r) for r in refs)


def _exported(root, o):
    """{asset: [panel ids]} for every figure source.json and table csv in the project."""
    found = {}
    for src in sorted((root / o["figures_root"]).glob("**/*.source.json")):
        name = src.name[: -len(".source.json")]
        if re.fullmatch(r"fig\d+|s\d+", name):
            found[name] = sorted(_panel_ids(src))
    for f in sorted((root / o["tables_root"]).glob("*.csv")):
        if re.fullmatch(r"S?T\d+", f.stem):
            found[f.stem] = []
    return found


def _order(o, root):
    """Citation-order, completeness and Methods-scope gates (outline_format.md section 7)."""
    out = []
    pending = {_asset(n, l) for r in o.get("pending", []) for n, l in (_expand(r) or [])}
    design = {_asset(n, l) for r in o.get("design_assets", []) for n, l in (_expand(r) or [])}
    excluded = {}
    for e in o.get("excluded", []):
        ref = e.get("ref") if isinstance(e, dict) else e
        if not (isinstance(e, dict) and str(e.get("reason", "")).strip()):
            out.append(f"excluded {ref!r}: give a reason (why it is not in the manuscript)")
        excluded.update({_asset(n, l): ref for n, l in (_expand(ref) or [])})
    first, seen_panels, panels_cited = {}, {}, {}
    exported = _exported(root, o)
    for sid, kind, ref in _reading_order(o):
        ex = _expand(ref)
        if not ex:
            continue
        for name, letter in ex:
            asset = _asset(name, letter)
            if kind == "Methods" and asset not in design:
                out.append(f"order: Methods {sid} cites {_pretty(asset)}; Methods may cite only design_assets "
                           f"(dataset table, study-design figure, method-type supp tables) -- results go in Results")
            first.setdefault(asset, (sid, kind))
            if name == "table" or asset in pending or asset not in exported:
                continue
            ids = exported[asset]
            if letter is None:
                seen = seen_panels.setdefault(asset, [])
                seen += [i for i in ids if i not in seen]
                panels_cited.setdefault(asset, set()).update(ids)
                continue
            seen = seen_panels.setdefault(asset, [])
            panels_cited.setdefault(asset, set()).add(letter)
            if letter in seen:
                continue
            expect = next((i for i in ids if i not in seen), None)
            if expect is not None and letter != expect:
                out.append(f"order: {sid} first cites {_pretty(asset)}{letter} before {_pretty(asset)}{expect}; panels "
                           f"are first cited a, b, c ... -- reorder the narrative or relabel the panels")
            seen.append(letter)
    by_series = {}
    for asset in first:
        k, n = _series(asset)
        by_series.setdefault(k, []).append((n, asset))
    for k, seq in by_series.items():
        nums = [n for n, _ in seq]
        if nums != list(range(1, len(nums) + 1)):
            stem = {"main_fig": "Fig ", "supp_fig": "Fig S", "main_table": "Table ", "supp_table": "Table S"}[k]
            plan = ", ".join(f"{_pretty(a)} → {stem}{i}" for i, (n, a) in enumerate(seq, 1) if n != i)
            out.append(f"order: {k.replace('_', ' ')}s are first cited as "
                       f"{', '.join(_pretty(a) for _, a in seq)}; number them in first-citation order "
                       f"(renumber: {plan or 'fill the gaps'})")
    for asset, ids in exported.items():
        if asset in excluded:
            continue
        if asset not in first:
            out.append(f"order: {_pretty(asset)} is exported but never cited; cite it where it belongs or list it "
                       "under excluded with a reason")
            continue
        missing = [i for i in ids if i not in panels_cited.get(asset, set())]
        if missing and asset not in pending:
            out.append(f"order: {_pretty(asset)} panel(s) {', '.join(missing)} never cited")
    for asset in design - set(first):
        out.append(f"order: design asset {_pretty(asset)} is never cited in Methods")
    for asset in pending - set(first) - design:
        out.append(f"order: pending {_pretty(asset)} is never cited; cite it where it belongs")
    for asset, ids in exported.items():
        if not ids and not asset.startswith(("T", "ST")) and asset not in excluded:
            out.append(f"order: {_pretty(asset)} has no panel list in its source.json; panel coverage cannot be "
                       "checked (re-export with figkit, which records values.panels)")
    return out, first


def coverage(o, root):
    """Every manuscript asset in numbering order: (label, panels, first section, all citing sections, status).
    Status is 'cited', 'pending' (drawn outside the pipeline), 'excluded: <reason>' or 'NOT CITED'."""
    root = Path(root)
    exported = _exported(root, o)
    pending = {_asset(n, l) for r in o.get("pending", []) for n, l in (_expand(r) or [])}
    reasons = {}
    for e in o.get("excluded", []):
        ref = e.get("ref") if isinstance(e, dict) else e
        for n, l in _expand(ref) or []:
            reasons[_asset(n, l)] = str(e.get("reason", "")) if isinstance(e, dict) else ""
    secs = {}
    for sid, _, ref in _reading_order(o):
        for n, l in _expand(ref) or []:
            s = secs.setdefault(_asset(n, l), [])
            if sid not in s:
                s.append(sid)
    order = ["main_fig", "main_table", "supp_fig", "supp_table"]
    rows = []
    for a in sorted(set(exported) | set(secs) | pending | set(reasons), key=lambda a: (order.index(_series(a)[0]),
                                                                                         _series(a)[1])):
        status = ("excluded: " + reasons[a] if a in reasons else "cited" if a in secs and a not in pending
                  else "pending" if a in pending else "NOT CITED")
        rows.append((_pretty(a), ",".join(exported.get(a, [])), (secs.get(a) or ["—"])[0], secs.get(a, []), status))
    return rows


def _items_and_code(o, first):
    """Every cited asset gets one 图 / 表 line (what it shows scientifically) in the section that first cites it;
    an item must be cited in its own section; plotting / table scripts are not code to cite."""
    out = []
    listed = {}
    for kind, secs in (("Methods", o.get("methods", [])), ("Results", o.get("results", []))):
        for sec in _nodes(secs):
            cited = set()
            for sid, _, ref in _reading_order({kind.lower(): [dict(sec, subsections=[])]}):
                cited |= {_asset(n, l) for n, l in (_expand(ref) or [])}
            for it in sec.get("items", []):
                if not isinstance(it, dict):
                    continue
                assets = {_asset(n, l) for n, l in (_expand(it.get("ref", "")) or [])}
                for a in assets:
                    listed.setdefault(a, sec["id"])
                    if a not in cited:
                        out.append(f"items: {kind} {sec['id']} lists {_pretty(a)} but its paragraphs do not cite it")
                what = str(it.get("what", ""))
                if not what.strip() or re.search(r"\.py\b|脚本|script", what, re.I):
                    out.append(f"items: {kind} {sec['id']} {it.get('ref')}: say what it shows scientifically, "
                               "not how it was drawn")
            for c in sec.get("code", []):
                if c.get("role") in DRAW_ROLES or DRAW_PATH.match(str(c.get("path", ""))):
                    out.append(f"code: {kind} {sec['id']} lists {c.get('path')} ({c.get('role')}); plotting / "
                               "table scripts are not part of the method -- cite the figure / table instead")
    for asset, (sid, kind) in first.items():
        if asset not in listed:
            out.append(f"items: {_pretty(asset)} has no 图 / 表 line; add one in {kind} {sid} (first citation) "
                       "saying what it shows")
    return out


def code_file(o, root, path):
    """Resolve a ``code`` path against the project root, then each ``code_roots`` entry (absolute or relative to
    the project root). None for TODO / empty / not found."""
    if not path or str(path).strip().upper() == "TODO":
        return None
    for base in [root, *(root / r for r in o.get("code_roots") or [])]:
        f = Path(base) / path
        if f.is_file():
            return f
    return None


def _code_found(o, root):
    """Every listed code path must exist (its source file is copied into the section folder); unknown code is TODO."""
    out = []
    for kind, secs in (("Methods", o.get("methods", [])), ("Results", o.get("results", []))):
        for sec in _nodes(secs):
            for c in sec.get("code", []):
                p = c.get("path")
                if p and str(p).strip().upper() != "TODO" and code_file(o, root, p) is None:
                    out.append(f"code: {kind} {sec['id']} lists {p}, not found under the project root or code_roots "
                               "(add its repository to code_roots, or write TODO)")
    return out


def _source_json(root, figures_root, name):
    hits = list((root / figures_root).glob(f"*/{name}.source.json")) + list((root / figures_root).glob(f"{name}.source.json"))
    return hits[0] if hits else None


def _panel_ids(src):
    v = json.loads(src.read_text(encoding="utf-8")).get("values", {})
    ids = {str(p.get("id")) for p in v.get("panels", []) if isinstance(p, dict)}
    return ids


def _cited_figures(o, root):
    """{figure name: source.json path} for every figure cited anywhere in Methods or Results."""
    out = {}
    for sec in list(_nodes(o.get("methods", []))) + list(_nodes(o.get("results", []))):
        refs = [i["ref"] if isinstance(i, dict) else i for i in sec.get("items", [])] + list(sec.get("cites", []))
        for p in sec.get("paragraphs", []):
            refs += p.get("cites", [])
        for name, _ in (n for r in refs for n in (_expand(r) or [])):
            if name != "table" and name not in out:
                src = _source_json(root, o["figures_root"], name)
                if src is not None:
                    out[name] = src
    return out


def _case_selections(o, root):
    """{figure: values.case_selection} for cited figures whose source.json records a case selection."""
    out = {}
    for name, src in _cited_figures(o, root).items():
        sel = json.loads(src.read_text(encoding="utf-8")).get("values", {}).get("case_selection")
        if isinstance(sel, dict):
            out[name] = sel
    return out


def _case_numbers(sel):
    """Design constants of a case selection (seed, per-group counts) -- allowed in Methods focus."""
    nums = {str(sel.get("seed"))} if sel.get("seed") is not None else set()
    for g in (sel.get("per_group") or {}).values():
        if isinstance(g, dict):
            vals = [int(v) for v in g.values() if isinstance(v, (int, float))]
            nums |= {str(v) for v in vals} | ({str(sum(vals))} if vals else set())
    return nums


RANDOM = re.compile(r"随机|random", re.I)


def _case_selection_stated(o, sels):
    """Every figure with a recorded case selection needs its rule in Methods: the seed and 'random'."""
    texts = [t for sec in _nodes(o.get("methods", [])) for w, t in _texts(sec, False) if w.endswith("focus")]
    out = []
    for name, sel in sels.items():
        seed = sel.get("seed")
        ok = any(RANDOM.search(t) and (seed is None or re.search(rf"(?<!\d){seed}(?!\d)", t)) for t in texts)
        if not ok:
            out.append(f"case selection rule for {_pretty(name)} not stated in Methods (seed {seed}): write the "
                       "stratified random rule, seed, cases per group incl. misclassified and the pool in a "
                       "Methods focus point")
    return out


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
    t = TEXT_REF.sub(" ", text)
    t = re.sub(r"\b(?:Fig|S|ST|T)\s?\d+[a-z]?(?:[–-][a-z])?\b", " ", t)
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
    pending = {_asset(n, l) for r in o.get("pending", []) for n, l in (_expand(r) or [])}
    for results, secs in ((False, _nodes(o.get("methods", []))), (True, _nodes(o.get("results", [])))):
        for sec in secs:
            refs = [i["ref"] if isinstance(i, dict) else i for i in sec.get("items", [])] + list(sec.get("cites", []))
            for p in sec.get("paragraphs", []):
                refs += p.get("cites", [])
            for ref in refs:
                ex = _expand(ref)
                if ex is None:
                    out.append(f"{sec['id']}: reference {ref!r} not understood (Fig2a, Fig2a-c, S5, T1, ST05)")
                    continue
                for name, letter in ex:
                    if _asset(name, letter) in pending:
                        continue  # declared, drawn outside the pipeline (e.g. study-design schematic)
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
    design = {_asset(n, l) for r in o.get("design_assets", []) for n, l in (_expand(r) or [])}
    for f in o.get("main_figures", []):
        if f not in covered and f not in design:
            out.append(f"main figure {f} not covered by any Results section")
    # ---- case selection of imaging-case figures stated once in Methods (medfig-plan S6)
    sels = _case_selections(o, root)
    out += _case_selection_stated(o, sels)
    case_nums = set().union(*(_case_numbers(s) for s in sels.values())) if sels else set()
    # ---- Methods without result numbers
    for sec in _nodes(o.get("methods", [])):
        allow = set(sec.get("allow_numbers", [])) | set(o.get("allow_numbers", [])) | case_nums
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
    order, first = _order(o, root)
    out += order + _items_and_code(o, first) + _code_found(o, root)
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
    rows = coverage(yaml.safe_load(Path(a.outline).read_text(encoding="utf-8")), a.project)
    cited = sum(r[4] in ("cited", "pending") for r in rows)
    print(f"coverage: {cited}/{len(rows)} manuscript assets cited "
          f"({sum(r[4].startswith('excluded') for r in rows)} excluded)")
    print(f"{len(issues)} issue(s)")
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
