"""Recipe: ordinal ablation bars (soft theme) -- components added one by one, single-hue light -> dark
gradient (2..5 levels, adjacent ΔE00 >= 12), flat bars, values at the bar ends, dark-grey CI whiskers,
value axis truncated below the data with a break mark.

Look after senlanke/figures4papers (graded ablation bars; no licence: idea only, re-derived). A gradient
is for ORDERED levels only; unordered methods take distinct colours (multi_metric_bars).
Function: compare.ordinal_bars (style.ordinal_gradient, style.axis_break).
"""
import pandas as pd

from _common import run, style

NAME = "ordinal_ablation"
THEME = "soft"
RECIPE = dict(
    chart='有序消融柱（单色相深浅梯度）',
    category='区间与记分',
    use='组件逐个叠加的消融（基线 → +A → +A+B …），顺序本身有含义',
    data='汇总行：每个有序水平的估计值（可带 CI）',
    avoid='水平之间没有顺序（改不同颜色）；超过 5 级（相邻色差不够，改点图或分箱）',
    functions=['compare.ordinal_bars', 'style.ordinal_gradient', 'style.axis_break'],
    tags=['ablation', 'ordinal', 'gradient', 'soft theme', 'figures4papers', '消融', '梯度'],
    source='风格参考 senlanke/figures4papers（无许可证，仅借鉴思路，代码重写）',
)
SIZE = (style.SINGLE, 1.75)


def draw(ax, cfg, prov):
    from figkit.panels import compare
    rows = pd.DataFrame(dict(label=["Backbone", "+ Anatomy prior", "+ Concept bottleneck", "+ Both"],
                             value=[0.712, 0.768, 0.801, 0.842], lo=[0.69, 0.75, 0.78, 0.82],
                             hi=[0.73, 0.79, 0.82, 0.86]))
    compare.ordinal_bars(ax, rows, lo_col="lo", hi_col="hi", xlabel="Balanced accuracy ↑")
    prov.set("values", ax._anchor_ordinal)
    prov.set("levels", ax._figkit_ordinal)
    prov.set("xlim", list(ax._anchor_xlim))


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
