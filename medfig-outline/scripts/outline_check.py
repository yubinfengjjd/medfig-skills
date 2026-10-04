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
    for sec in o.get("results", []):
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
    for results, secs in ((False, o.get("methods", [])), (True, o.get("results", []))):
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
    for sec in o.get("methods", []):
        allow = set(sec.get("allow_numbers", [])) | set(o.get("allow_numbers", []))
        for where, text in _texts(sec, False):
            if not where.endswith("focus"):
                continue
            for m in NUM.findall(_strip_refs(text)):
                if m in allow or (m.isdigit() and len(m) <= 1):
                    continue
                out.append(f"{where}: result-like number {m!r} (Methods describe structure; allow_numbers if not a result)")
    # ---- Results titles
    for sec in o.get("results", []):
        t = sec.get("title", "")
        if VAGUE_TITLE.match(t) or len(t.split()) < 5:
            out.append(f"Results {sec['id']} title {t!r}: write a one-sentence finding, not a topic")
        if NUM.search(t):
            out.append(f"Results {sec['id']} title {t!r}: no number in the title (numbers go in the paragraphs)")
    # ---- wording
    for results, secs in ((False, o.get("methods", [])), (True, o.get("results", []))):
        for sec in secs:
            for where, text in _texts(sec, results):
                bare = CODE_NOTE.sub("", text)
                out += [f"{where}: banned word {w!r}" for w in qa.banned_in_text(bare, cfg)]
                out += [f"{where}: development history {w!r} (mainline_rules.md)" for w in qa.dev_history_in_text(bare, cfg)]
                out += [f"{where}: development history {k!r} (mainline_rules.md)" for k, p in DEV_ZH.items()
                        if re.search(p, bare)]
                if cfg is not None:
                    out += [f"{where}: project code pattern {p!r}" for p in qa.forbidden_in_text(bare, cfg)]
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
