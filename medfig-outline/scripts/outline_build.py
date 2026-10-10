"""Render a checked ``outline.yaml`` into 写作大纲.docx + 写作大纲.md and copy each subsection's files into its own
folder (figures / tables / captions / code), outside the project. Refuses to build when outline_check reports
issues. Only copies; never modifies the project.

Usage: python outline_build.py outline.yaml --project <root> --out <dir outside root> [--figkit-toml <toml>]
"""
import argparse
import re
import shutil
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import outline_check  # noqa: E402

FIG_EXT = ("pdf", "png", "svg")
TAB_EXT = ("csv", "md", "tex")
ROLE_ORDER = ["计算", "绘图", "表格"]


# ------------------------------------------------------------------------------------------------ model
def _refs(sec, results):
    refs = [i["ref"] if isinstance(i, dict) else i for i in sec.get("items", [])] + list(sec.get("cites", []))
    for p in sec.get("paragraphs", []):
        refs += p.get("cites", [])
    figs, tabs = [], []
    for r in refs:
        for name, letter in outline_check._expand(r) or []:
            (tabs if name == "table" else figs).append(letter if name == "table" else name)
    return list(dict.fromkeys(figs)), list(dict.fromkeys(tabs))


def _items(sec):
    return [i for i in sec.get("items", []) if isinstance(i, dict)]


def _item_line(i, pending):
    tag = "（外部绘制，待交付）" if outline_check._asset(*(outline_check._expand(i["ref"]) or [("", "")])[0]) in pending else ""
    return f"{_pretty_ref(i['ref'])}{tag}：{i.get('what', '')}"


def _label(p):
    return p["label"] + ("（可选）" if p.get("optional") else "")


def _pretty_ref(r):
    """'Fig4a' -> 'Fig 4a', 'S5a' -> 'Fig S5a', 'ST05' -> 'Table S5', 'T2' -> 'Table 2'."""
    m = re.match(r"^(Fig|S)(\d+)(.*)$", r)
    if m:
        return f"Fig {'S' if m.group(1) == 'S' else ''}{int(m.group(2))}{m.group(3)}"
    m = re.match(r"^(ST|T)(\d+)$", r)
    if m:
        return f"Table {'S' if m.group(1) == 'ST' else ''}{int(m.group(2))}"
    return r


def _cite_tail(p):
    return f"（{'、'.join(_pretty_ref(c) for c in p['cites'])}）" if p.get("cites") else ""


def _code_roles(code):
    """[(role, '`a.py`、`b.py`（推测）')] in 计算 / 绘图 / 表格 order: one line per role, not one per file."""
    roles = ROLE_ORDER + sorted({c.get("role", "") for c in code} - set(ROLE_ORDER))
    return [(r, "、".join(f"`{_code_line(c)}`" for c in code if c.get("role", "") == r))
            for r in roles if any(c.get("role", "") == r for c in code)]


def _code_line(c):
    path = c.get("path") or "TODO"
    return f"{path}（推测）" if c.get("guess") else path


# ------------------------------------------------------------------------------------------------ markdown
HEAD_PT = {0: 14, 1: 12, 2: 11}   # docx heading size by depth (section / subsection / sub-subsection)


def _walk(secs):
    yield from outline_check._tree(secs)


def _md_body(sec, results, pending=frozenset()):
    L = []
    if not results:
        if sec.get("focus"):
            L += ["**写作重点：**", ""]
            for blk in sec["focus"]:
                L.append(f"- {blk['topic']}：")
                L += [f"  - {t}" for t in blk.get("points", [])]
        if sec.get("foreshadow"):
            L += ["", "**为后文铺垫：**", ""] + [f"- {t}" for t in sec["foreshadow"]]
        if _items(sec):
            L += ["", "**引用图 / 表：**", ""] + [f"- {_item_line(i, pending)}" for i in _items(sec)]
        if sec.get("code"):
            L += ["", "**关联代码（只作为你脑内映射）：**", ""] + [f"- {r}：{line}" for r, line in _code_roles(sec["code"])]
        return L
    if sec.get("paragraphs"):
        L += ["**写作要点**", ""]
        for p in sec["paragraphs"]:
            L.append(f"- **{_label(p)}**：{p.get('claim', '')}{_cite_tail(p)}")
            L += [f"  - {t}" for t in p.get("points", [])]
    if _items(sec):
        L += ["", "**图 / 表**", ""] + [f"- {_item_line(i, pending)}" for i in _items(sec)]
    if sec.get("code"):
        L += ["", "**相关代码**", ""] + [f"- {role}：{line}" for role, line in _code_roles(sec["code"])]
    if sec.get("boundaries"):
        L += ["", "**措辞边界**", ""] + [f"- {t}" for t in sec["boundaries"]]
    return L


def to_md(o):
    pending = _pending(o)
    L = [f"# 写作大纲：{o.get('project', '')}", ""]
    for results, secs in ((False, o.get("methods", [])), (True, o.get("results", []))):
        for sec, depth, _ in _walk(secs):
            L += [f"{'#' * (depth + 2)} {sec['id']} {sec['title']}", ""]
            if results and sec.get("subtitle"):
                L += [f"（{sec['subtitle']}）", ""]
            body = _md_body(sec, results, pending)
            L += body + ([""] if body else [])
    rows = o.get("_coverage") or []
    if rows:
        L += ["## 图表引用清单", "", "| 资产 | panel | 首次引用 | 引用小节 | 状态 |", "|---|---|---|---|---|"]
        L += [f"| {a} | {p or '—'} | {f} | {'、'.join(s) or '—'} | {_status_zh(st)} |" for a, p, f, s, st in rows]
        L.append("")
    return "\n".join(L)


def _status_zh(st):
    return {"cited": "已引用", "pending": "已引用（外部绘制，待交付）", "NOT CITED": "未引用"}.get(
        st, st.replace("excluded: ", "不进稿件："))


def _pending(o):
    return {outline_check._asset(n, l) for r in o.get("pending", []) for n, l in (outline_check._expand(r) or [])}


# ------------------------------------------------------------------------------------------------ docx
def to_docx(o, path):
    import docx
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt

    d = docx.Document()
    sec0 = d.sections[0]
    sec0.page_height, sec0.page_width = Cm(29.7), Cm(21.0)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(sec0, side, Cm(2.54))
    st = d.styles["Normal"]
    st.font.name, st.font.size = "Times New Roman", Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    st.paragraph_format.space_after = Pt(2)

    def para(text="", level=0, bold=False, size=None):
        p = d.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.74 * level)
        for part in re.split(r"(`[^`]+`)", text):
            if not part:
                continue
            code = part.startswith("`") and part.endswith("`")
            r = p.add_run(part[1:-1] if code else part)
            r.bold = bold
            if size:
                r.font.size = Pt(size)
            if code:
                r.font.name = "Consolas"
                r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
        return p

    pending = _pending(o)
    for results, secs in ((False, o.get("methods", [])), (True, o.get("results", []))):
        for sec, depth, _ in _walk(secs):
            h = para(f"{sec['id']} {sec['title']}", bold=True, size=HEAD_PT.get(depth, 10.5))
            h.paragraph_format.space_before = Pt(10 if depth == 0 else 6)
            if results and sec.get("subtitle"):
                para(f"（{sec['subtitle']}）", size=11 if depth == 0 else 10.5)
            if not results:
                if sec.get("focus"):
                    para("写作重点：", bold=True)
                    for blk in sec["focus"]:
                        para(f"{blk['topic']}：", level=1)
                        for t in blk.get("points", []):
                            para(t, level=2)
                if sec.get("foreshadow"):
                    para("为后文铺垫：", level=1)
                    for t in sec["foreshadow"]:
                        para(t, level=2)
                if _items(sec):
                    para("引用图 / 表：", level=1)
                    for i in _items(sec):
                        para(_item_line(i, pending), level=2)
                if sec.get("code"):
                    para("关联代码（只作为你脑内映射）：", level=1)
                    for role, line in _code_roles(sec["code"]):
                        para(f"{role}：{line}", level=2)
                continue
            if sec.get("paragraphs"):
                para("写作要点", bold=True)
                for p in sec["paragraphs"]:
                    # one line per paragraph: bold label + claim + where it is shown; points follow as plain lines
                    q = d.add_paragraph()
                    q.paragraph_format.left_indent = Cm(0.74)
                    q.add_run(_label(p) + "：").bold = True
                    q.add_run(p.get("claim", "") + _cite_tail(p))
                    for t in p.get("points", []):
                        para(t, level=2)
            if _items(sec):
                para("图 / 表", bold=True)
                for i in _items(sec):
                    para(_item_line(i, pending), level=1)
            if sec.get("code"):
                para("相关代码", bold=True)
                for role, line in _code_roles(sec["code"]):
                    para(f"{role}：{line}", level=1)
            if sec.get("boundaries"):
                para("措辞边界", bold=True)
                for t in sec["boundaries"]:
                    para(t, level=1)
    rows = o.get("_coverage") or []
    if rows:
        h = para("图表引用清单", bold=True, size=14)
        h.paragraph_format.space_before = Pt(10)
        tab = d.add_table(rows=1, cols=5)
        tab.style = "Table Grid"
        for cell, t in zip(tab.rows[0].cells, ("资产", "panel", "首次引用", "引用小节", "状态")):
            cell.text = t
            cell.paragraphs[0].runs[0].bold = True
        for a, p, f, s, st in rows:
            for cell, t in zip(tab.add_row().cells, (a, p or "—", f, "、".join(s) or "—", _status_zh(st))):
                cell.text = t
    d.save(str(path))


# ------------------------------------------------------------------------------------------------ folders
def _caption_text(root, o, name):
    """Caption draft for figure ``name`` (fig2 / s05): its own file, or the '## Fig2' / '## S5' section."""
    head = f"Fig{int(name[3:])}" if name.startswith("fig") else f"S{int(name[1:])}"
    pat = re.compile(rf"^## {head}\s*$", re.M)
    for c in o.get("captions", []):
        p = root / c
        files = sorted(p.glob("*.md")) if p.is_dir() else [p] if p.is_file() else []
        for f in files:
            s = f.read_text(encoding="utf-8")
            m = pat.search(s)
            if m:
                nxt = re.compile(r"^## ", re.M).search(s, m.end())
                return s[m.start(): nxt.start() if nxt else len(s)].rstrip() + "\n"
    return None


def _copy_section(root, o, sec, results, dest):
    """Copy the outputs this section cites (figures, tables, captions) and the source files of its analysis code.
    Plotting and table-building scripts are not copied: they draw the figures, they are not part of the method."""
    figs, tabs = _refs(sec, results)
    pending = _pending(o)
    (dest / "figures").mkdir(parents=True, exist_ok=True)
    (dest / "tables").mkdir(exist_ok=True)
    (dest / "captions").mkdir(exist_ok=True)
    for name in figs:
        if name in pending:
            continue
        src = outline_check._source_json(root, o["figures_root"], name)
        for f in [src, *(src.with_name(f"{name}.{e}") for e in FIG_EXT)]:
            if f.is_file():
                shutil.copy2(f, dest / "figures" / f.name)
        cap = _caption_text(root, o, name)
        if cap:
            (dest / "captions" / f"{name}.md").write_text(cap, encoding="utf-8")
    for t in tabs:
        for e in TAB_EXT:
            f = root / o["tables_root"] / f"{t}.{e}"
            if f.is_file():
                shutil.copy2(f, dest / "tables" / f.name)
    if not sec.get("code"):
        return
    # source files themselves, flat by file name; files sharing a name keep their listed relative path
    files = list(dict.fromkeys((c["path"], f) for c in sec["code"]
                               if (f := outline_check.code_file(o, root, c.get("path")))))
    names = [f.name for _, f in files]
    for rel, f in files:
        target = dest / "code" / (f.name if names.count(f.name) == 1 else rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)


def build(outline_path, project, out, figkit_toml=None):
    root, out = Path(project).resolve(), Path(out).resolve()
    if out == root or root in out.parents:
        raise ValueError(f"output {out} must be outside the project {root}")
    issues = outline_check.check(outline_path, root, figkit_toml)
    if issues:
        raise RuntimeError("outline_check reported issues:\n" + "\n".join(issues))
    o = yaml.safe_load(Path(outline_path).read_text(encoding="utf-8"))
    o["_coverage"] = outline_check.coverage(o, root)
    out.mkdir(parents=True, exist_ok=True)
    md = out / "写作大纲.md"
    md.write_text(to_md(o), encoding="utf-8")
    dx = out / "写作大纲.docx"
    to_docx(o, dx)
    for results, top, secs in ((False, "2_Methods", o.get("methods", [])), (True, "3_Results", o.get("results", []))):
        for sec, _, parents in outline_check._tree(secs):
            # subsections live inside their parent's folder: 3_Results/3.1_x/3.1.2_y/
            dest = out / top
            for par in parents:
                dest = dest / f"{par['id']}_{par['short']}"
            dest = dest / f"{sec['id']}_{sec['short']}"
            if _refs(sec, results) != ([], []) or sec.get("code"):
                _copy_section(root, o, sec, results, dest)
            else:
                dest.mkdir(parents=True, exist_ok=True)
    return dict(docx=str(dx), md=str(md), out=str(out))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("outline")
    ap.add_argument("--project", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--figkit-toml")
    a = ap.parse_args(argv)
    res = build(a.outline, a.project, a.out, a.figkit_toml)
    print(res["docx"]); print(res["md"]); print(res["out"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
