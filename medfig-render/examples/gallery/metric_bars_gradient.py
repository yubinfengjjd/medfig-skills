"""Recipe: many-method bars with gradient controls (soft theme) -- one metric, the proposed method in the one
saturated colour, the controls as one light -> mid gradient of the same hue (declared as one control
group), values on every bar, legend inside the axes on top, truncated value axis with
a break mark.

Look after senlanke/figures4papers style 2 (no licence: idea only, re-derived).
Functions: compare.metric_bars(controls="gradient") + compare.legend_inside; theme = "soft".
"""
import numpy as np
import pandas as pd

from _common import run, style

NAME = "metric_bars_gradient"
THEME = "soft"
RECIPE = dict(
    chart='多方法单指标柱（同色相渐变对照 + 内置图例）',
    category='区间与记分',
    use='一个指标上比较 3–5 个方法，对照方法同属一类（同一色相深浅），本文方法突出',
    data='方法 × 重复（seed / 折）的长表',
    avoid='对照方法超过 4 个（渐变分不开，改 pastel 浅色）；对照方法之间本身要比较（改 pastel 不同色相）；截断却不画断轴标记（导出闸门会拦）',
    functions=['compare.metric_bars', 'compare.legend_inside', 'style.soft_controls', 'style.mark_controls'],
    tags=['bar', 'gradient', 'soft theme', 'figures4papers', '柱状图', '渐变'],
    source='风格参考 senlanke/figures4papers 样式 2（无许可证，仅借鉴思路，代码重写）',
)
SIZE = (style.SINGLE, 2.3)
METHODS = ["m1", "m2", "m3", "m4", "ours"]
LABELS = {**{f"m{i}": f"Baseline {i}" for i in range(1, 5)}, "ours": "Proposed"}
BASE = [0.781, 0.808, 0.829, 0.848, 0.912]


def draw(ax, cfg, prov):
    from figkit.panels import compare
    rng = np.random.default_rng(3)
    df = pd.DataFrame([(m, r, b + rng.normal(0, 0.005)) for m, b in zip(METHODS, BASE) for r in range(3)],
                      columns=["method", "run", "value"])
    compare.metric_bars(ax, df, "AUROC", METHODS, emphasis="ours", controls="gradient", ylim=(0.70, 1.02))
    compare.legend_inside(ax, METHODS, labels=LABELS, emphasis="ours", controls="gradient", ncol=2)
    prov.set("bars", ax._anchor_bars)
    prov.set("ylim", list(ax._anchor_ylim))
    prov.set("whisker", ax._anchor_whisker)


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
