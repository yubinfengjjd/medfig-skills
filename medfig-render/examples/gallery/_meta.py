"""Single source of truth for the gallery: one RECIPE dict per recipe file, INDEX.md is generated from them.

Fields (all required, strings in Chinese except ``functions`` / ``source``):
  chart     图型名（与 medfig-plan chart_diversity.md 推荐图一列的说法一致）
  category  分组：判别 / 校准与效用 / 区间与记分 / 分布与组成 / 版式
  use       什么时候用（一句话）
  data      输入数据形状（逐样本标签 + 分数 / 多次重复 / 汇总行 / 计数表 ...）
  avoid     不要用的情况
  functions 库函数列表（figkit 模块路径）
  tags      检索用关键词（英文缩写 + 中文）
  source    来源（开源仓库 + 许可证，或"项目实战提炼"）

Run ``python _meta.py`` to rewrite INDEX.md; ``tests/test_gallery_recipes.py`` fails if INDEX.md is stale.
"""
import ast
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ("chart", "category", "use", "data", "avoid", "functions", "tags", "source")
CATEGORIES = ("判别", "校准与效用", "区间与记分", "分布与组成", "版式")


def recipes():
    """{recipe name: RECIPE dict} read statically (no import, no matplotlib) from every recipe file."""
    out = {}
    for p in sorted(HERE.glob("*.py")):
        if p.stem.startswith("_"):
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        meta = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "RECIPE" for t in node.targets):
                v = node.value
                if isinstance(v, ast.Call) and getattr(v.func, "id", None) == "dict" and not v.args:
                    meta = {kw.arg: ast.literal_eval(kw.value) for kw in v.keywords}  # RECIPE = dict(...)
                else:
                    meta = ast.literal_eval(v)
        if meta is None:
            raise ValueError(f"{p.name}: no RECIPE dict")
        missing = [f for f in FIELDS if not meta.get(f)]
        if missing:
            raise ValueError(f"{p.name}: RECIPE missing {missing}")
        if meta["category"] not in CATEGORIES:
            raise ValueError(f"{p.name}: category {meta['category']!r} not in {CATEGORIES}")
        out[p.stem] = meta
    return out


HEADER = """# Panel gallery 索引

> 本文件由 `_meta.py` 根据各配方的 `RECIPE` 元数据自动生成，不要手改；改元数据后运行
> `python _meta.py`。测试会在本文件过期时失败。

用法：先按"输入数据形状"和"不要用"两列排除，再看"什么时候用"；打开配方脚本看 `draw()`，把调用和
`figkit.toml` 里用到的色板复制进项目。全部配方用合成数据，导出时所有 QA 闸门（含色差闸门）必须为空。

运行：`python medfig-render/examples/gallery/<配方>.py`，输出到 `examples/gallery/out/figures/gallery/`。
"""

FOOTER = """
已有、未单独做配方的图型（见 `references/figkit_api.md`）：森林图 / 哑铃图 / 配对估计图（`intervals`）、
小提琴 / 箱线 / ECDF / HDR 轮廓（`dist`）、标注热图 / 瀑布图（`heat`）、混淆矩阵（`confusion`）、
B-scan 边界与分带 / 概念图 / 概率叠加（`imaging`）、阶梯图 / 干预曲线（`curves`）。

## 通用经验

- 颜色：数据色一律从 `figkit.toml` 色板取；同一 axes 里不同数据色 ΔE00 < 12 会被 `qa.palette_clash` 拦下
  （阈值可在 `[qa] palette_min_delta_e` 调）。选新色时用 `style.delta_e` 和图内每个颜色比，最好 ≥ 20。
- 参考线、对角线、背景带、尺寸图例都用 `style.aux` 标成辅助元素，不要画成灰色数据。
- 对数 / symlog 轴调用 `style.log_ticks(ax)`，否则默认的 10^{-k} 用 ASCII 连字符，过不了真减号检查。
- 图例压住数据时，换图例位置（`scorecard` / `sized` 有 `legend_loc` 参数，其余函数画完后调用 `ax.legend(loc=...)`
  覆盖），或者给轴范围留出空白，不要缩小字号（下限 6 pt）。`roc_mean_sd` 没有 `linestyle` 参数，需要线型冗余时
  画完后设置最后一条线（见 `roc_mean_sd.py`）。
- 只有一次运行时不画 SD 带，图注里要说明；SD 用样本 SD（ddof = 1）。
- DCA、风险覆盖是描述性分析，图注写明阈值没有在测试集上调，不构成临床决策依据。
"""


def _cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def render(meta=None):
    meta = recipes() if meta is None else meta
    lines = [HEADER]
    for cat in CATEGORIES:
        rows = {k: v for k, v in meta.items() if v["category"] == cat}
        if not rows:
            continue
        lines += [f"\n## {cat}\n", "| 配方 | 图型 | 什么时候用 | 输入数据形状 | 不要用 | 库函数 | 关键词 | 来源 |",
                  "|---|---|---|---|---|---|---|---|"]
        for name, m in rows.items():
            fn = " + ".join(f"`{f}`" for f in m["functions"])
            lines.append("| " + " | ".join([f"`{name}.py`", _cell(m["chart"]), _cell(m["use"]), _cell(m["data"]),
                                            _cell(m["avoid"]), fn, _cell(", ".join(m["tags"])),
                                            _cell(m["source"])]) + " |")
    lines.append(FOOTER)
    return "\n".join(lines)


if __name__ == "__main__":
    text = render()
    (HERE / "INDEX.md").write_text(text, encoding="utf-8")
    print(f"INDEX.md: {len(recipes())} recipes", file=sys.stderr)
