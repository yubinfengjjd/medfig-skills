"""Cross-stage consistency check for a medpaper-pipeline project.

Reads 口径表.md and scans the markdown under 03_outline/ and 04_manuscript/ for:
  errors   - forbidden aliases from 口径表 §术语 (negation and label cross-references are skipped)
  warnings - key counts that do not match 口径表 §关键计数, either in the cited source file or in the
             manuscript (number + unit within a sentence naming the row's dataset), and number tokens
             that look like a lost decimal point (bare 0ddd… outside DOIs)
Exit code: 0 = no error, 1 = at least one error. Warnings do not fail the run; report them at the
stage gate. Usage: python -X utf8 consistency_check.py <project_root> [--json]
"""
import json
import re
import sys
from pathlib import Path
from citation_stats import collect as collect_citations, format_report as citation_report

# narrative files only: the outline itself and the manuscript. Per-section evidence copies under
# 03_outline/<section>/ (captions, tables, code) are upstream records and are fixed at their source.
SCAN_GLOBS = ("03_outline/*.md", "04_manuscript/**/*.md")
SKIP_NAMES = ("核查说明", "作者决定", "审查")  # audit files may quote the old wording on purpose
# a hit is ignored when the alias sits in a negation or in an explicit label cross-reference
NEGATION = re.compile(r"(不是|并非|不称|不写|不用|禁用|not an?|rather than|instead of|nor a)\W{0,3}[^。.;；]{0,40}$", re.I)
LABEL_REF = re.compile(r"(“|\"|')[^“”\"']{0,30}$")

# 关键计数：单位的中英写法（含常见同义写法）；用于在稿件中定位“数字 + 单位”的计数表述
COUNT_UNITS = [("临床组", r"临床组", r"(?:clinical[- ])?groups?"),
               ("重复组件", r"重复(?:组件|成分)", r"(?:duplicate )?components?"),
               ("组件", r"组件|成分", r"components?"),
               ("受试者簇", r"受试者(?:簇|聚类)", r"subject clusters?"),
               ("扫描", r"扫描(?![-–—对])", r"scans?(?![-–])"),
               ("图像", r"图像", r"images?")]
NAME_STOP = {"S", "Table", "Fig", "panel"}
ATTR_WINDOW = 80  # 数字与数据集名的最大距离（字符）
LOST_DECIMAL = re.compile(r"(?<![\w./-])0\d{3,}(?![\w./-])")


def _table_rows(text, heading):
    m = re.search(rf"^##\s*\d*\.?\s*{heading}.*?$(.*?)(?=^##\s|\Z)", text, re.M | re.S)
    if not m:
        return []
    rows = [l for l in m.group(1).splitlines() if l.strip().startswith("|")]
    out = []
    for l in rows[2:]:  # skip header + separator
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        out.append(cells)
    return out


def load_rules(root):
    p = Path(root) / "口径表.md"
    if not p.is_file():
        sys.exit(f"missing {p}")
    text = p.read_text(encoding="utf-8")
    terms = []
    for c in _table_rows(text, "术语"):
        if len(c) < 3:
            continue
        aliases = [a.strip() for a in re.split(r"[;；]", c[2]) if a.strip() and a.strip() != "—"]
        terms.append({"canonical": c[0], "canonical_zh": c[1], "aliases": aliases})
    return terms


def scan(root):
    root = Path(root)
    terms = load_rules(root)
    hits = []
    files = sorted({f for g in SCAN_GLOBS for f in root.glob(g)})
    for f in files:
            if any(s in f.name for s in SKIP_NAMES):
                continue
            text = f.read_text(encoding="utf-8", errors="replace")
            for t in terms:
                for a in t["aliases"]:
                    # Latin aliases need word boundaries; they are case-insensitive unless they are
                    # case variants of an acronym ("BAcc" must not match "BACC")
                    if re.search(r"[一-鿿]", a):
                        pat = re.compile(re.escape(a))
                    else:
                        flags = 0 if any(ch.isupper() for ch in a[1:]) else re.I
                        pat = re.compile(r"(?<![\w-])" + re.escape(a) + r"(?![\w-])", flags)
                    for m in pat.finditer(text):
                        before = text[max(0, m.start() - 60):m.start()]
                        if NEGATION.search(before) or LABEL_REF.search(before):
                            continue
                        line = text.count("\n", 0, m.start()) + 1
                        ctx = text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
                        hits.append({"file": f.relative_to(root).as_posix(), "line": line, "alias": a,
                                     "use": t["canonical"] or t["canonical_zh"], "context": ctx})
    return hits


def load_counts(root):
    """关键计数表 → [{obj, numbers, units, source}]；无数字的行跳过。"""
    p = Path(root) / "口径表.md"
    if not p.is_file():
        return []
    out = []
    for c in _table_rows(p.read_text(encoding="utf-8"), "关键计数"):
        if len(c) < 4:
            continue
        obj, value, source, canonical = c[0], c[1], c[2], c[3]
        numbers, units = set(), set()
        for cell in (value, canonical):
            for name, zh_re, en_re in COUNT_UNITS:
                for m in re.finditer(r"(\d[\d,]*)\s*(?:张|个|名|例)?\s*" + zh_re, cell):
                    numbers.add(m.group(1).replace(",", ""))
                    units.add((name, zh_re, en_re))
        if not numbers:
            continue  # 无数值的行（如 panel 字母）不在此检查
        anchors = [t for t in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", obj) if t not in NAME_STOP]
        out.append({"obj": obj, "numbers": numbers, "units": sorted(units), "source": source, "anchors": anchors})
    return out


def _find_source(root, source):
    """按出处单元格的文件名在项目内查文件；非文件型出处（成图、代码等）返回 None。

    同名文件可能有多份（正本在 02_figures/out 或分节证据目录，_process/_archive 里是旧副本）；
    优先取不在 _process/_archive 下、路径最浅的一份。
    """
    name = re.split(r"[（( ]", source)[0].strip()
    if not re.search(r"\.(md|json|csv|txt|tex)$", name):
        return None
    hits = [f for f in Path(root).rglob(name) if ".git" not in f.parts]
    if not hits:
        return None

    def rank(f):
        rel = f.relative_to(root).parts
        return (any(p in ("_archive", "_process") for p in rel), len(rel), f.as_posix())

    return sorted(hits, key=rank)[0]


def check_counts(root):
    """口径表关键计数 ↔ 出处文件、↔ 稿件中的“数字+单位”。返回 warning 列表。

    稿件中的计数按“最近的锚点”归属：数字+单位附近 200 字符内最近的数据集名决定它属于哪一行，
    避免一句话里同时出现两个数据集时的误报。
    """
    root = Path(root)
    warns = []
    counts = load_counts(root)
    files = sorted({f for g in SCAN_GLOBS for f in root.glob(g) if not any(s in f.name for s in SKIP_NAMES)})
    texts = {f: f.read_text(encoding="utf-8-sig", errors="replace") for f in files}
    for row in counts:
        src = _find_source(root, row["source"])
        if src is not None:
            t = src.read_text(encoding="utf-8-sig", errors="replace").replace(",", "")
            # 数字边界匹配：47 不能靠 474 过关、261 不能靠 12610 过关
            missing = sorted(n for n in row["numbers"] if not re.search(rf"(?<![\d.]){re.escape(n)}(?![\d])", t))
            if missing:
                warns.append({"file": src.relative_to(root).as_posix(), "line": 0, "rule": "count-source",
                              "msg": f"口径表“{row['obj']}”的计数 {missing} 未在出处文件中找到"})
    anchored = [(r, a) for r in counts for a in r["anchors"]]
    for f, text in texts.items():
        anchor_pos = [(am.start(), row) for row, a in anchored for am in re.finditer(re.escape(a), text)]
        for row in counts:
            for _, zh, en in row["units"]:
                pat = re.compile(rf"(\d[\d,]*)\s*(?:张|个|名|例)?\s*{zh}|(\d[\d,]*)\s+{en}")
                for m in pat.finditer(text):
                    n = (m.group(1) or m.group(2)).replace(",", "")
                    if n in row["numbers"]:
                        continue
                    # 归属：窗口内离该数字最近的数据集名；同距离时取位置在前的
                    cand = sorted(((abs(pos - m.start()), 0 if pos < m.start() else 1, r2)
                                   for pos, r2 in anchor_pos if abs(pos - m.start()) <= ATTR_WINDOW))
                    if not cand or cand[0][2] is not row:
                        continue
                    line = text.count("\n", 0, m.start()) + 1
                    warns.append({"file": f.relative_to(root).as_posix(), "line": line, "rule": "count-manuscript",
                                  "msg": f"口径表“{row['obj']}”规范计数 {sorted(row['numbers'])}，此处写 {n}",
                                  "context": text[max(0, m.start() - 50):m.end() + 50].replace("\n", " ")})
        for m in LOST_DECIMAL.finditer(text):
            warns.append({"file": f.relative_to(root).as_posix(), "line": text.count("\n", 0, m.start()) + 1,
                          "rule": "lost-decimal", "msg": f"疑似丢失小数点：{m.group(0)}（如 0.0053 写成 00053）",
                          "context": text[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")})
    return warns


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    root = sys.argv[1]
    hits = scan(root)
    warns = check_counts(root)
    citations = collect_citations(root)
    warns.extend(citations["warnings"])
    if "--json" in sys.argv:
        print(json.dumps({"errors": hits, "warnings": warns, "citations": citations}, ensure_ascii=False, indent=1))
    else:
        print(citation_report(citations))
        for h in hits:
            print(f"{h['file']}:{h['line']}  禁用别名 “{h['alias']}” → 用 “{h['use']}”  …{h['context']}…")
        for w in warns:
            loc = f"{w['file']}:{w.get('line', 0)}"
            print(f"{loc}  [警告] {w['msg']}  …{w.get('context', '')}…")
        print(f"{len(hits)} hit(s), {len(warns)} warning(s)")
    sys.exit(1 if hits else 0)


if __name__ == "__main__":
    main()
