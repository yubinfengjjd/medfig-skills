"""Recipe: exceedance (tail) curves -- fraction of samples whose error exceeds x, log y.

Use when the claim is "fewer large errors": a mean error per method hides the tail, the exceedance curve
reads it directly. Idea after taoge946/academic-figure-patterns (MIT). Function: evidence.exceedance.
"""
import numpy as np

from _common import run, style

NAME = "exceedance"
RECIPE = dict(
    chart='超越曲线（尾部误差）',
    category='分布与组成',
    use='结论是"大误差更少"：比较两三个方法逐样本误差分布的尾部',
    data='每个方法的逐样本误差（同一批样本）',
    avoid='只有汇总误差（没有逐样本值）；结论关于平均水平而非尾部（改分布图或点 + 区间）',
    functions=['evidence.exceedance'],
    tags=['exceedance', 'tail', 'per-sample', 'error', '超越曲线', '尾部'],
    source='思路参考 taoge946/academic-figure-patterns（MIT），代码按 figkit 重写',
)
SIZE = (style.SINGLE, style.SINGLE * 0.7)


def draw(ax, cfg, prov):
    from figkit.panels import evidence
    rng = np.random.default_rng(21)
    pal = style.palette("model", cfg)
    errs = {"model_a": rng.gamma(2.0, 0.6, 2000), "model_b": rng.gamma(2.0, 0.6, 2000) * 1.25}
    for k, v in errs.items():
        evidence.exceedance(ax, v, color=pal[k]["color"], linestyle=pal[k]["linestyle"], label=pal[k]["label"])
    ax.set_xlabel("Boundary error (px)")
    ax.legend(loc="lower left")
    prov.set("tail_at_3px", {k: float(np.mean(v > 3)) for k, v in errs.items()})


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
