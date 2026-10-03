"""Recipe: paired per-sample cloud on the identity line, with binned medians + IQR band.

Use when the same samples are measured under two conditions and the claim lives in the cloud's shape
(on y = x = unchanged, below = smaller). Run ``stats.structure_strength`` first: if it fails, the cloud
will not show the structure -- use a difference distribution or a table row instead.
Idea after taoge946/academic-figure-patterns (MIT). Functions: evidence.paired_cloud + evidence.binned_median.
"""
import numpy as np

from _common import run, style

NAME = "paired_cloud"
RECIPE = dict(
    chart='配对散点云（y = x 参考线 + 分箱中位数）',
    category='分布与组成',
    use='同一批样本在两种条件 / 两个方法下的逐样本对比，结论体现在点云形状',
    data='逐样本成对数值（同一单位）',
    avoid='structure_strength 不通过（结构看不出，改差值分布或表格）；样本不成对',
    functions=['evidence.paired_cloud', 'evidence.binned_median', 'stats.structure_strength'],
    tags=['paired', 'scatter', 'identity line', 'per-sample', '配对', '散点'],
    source='思路参考 taoge946/academic-figure-patterns（MIT），代码按 figkit 重写',
)
SIZE = (style.SINGLE * 0.75, style.SINGLE * 0.75)


def draw(ax, cfg, prov):
    from figkit import stats
    from figkit.panels import evidence
    rng = np.random.default_rng(41)
    before = rng.gamma(3.0, 0.6, 800)
    after = before * 0.82 + rng.normal(0, 0.12, 800)
    check = stats.structure_strength(before, after, kind="paired")
    assert check["passes"], check
    evidence.paired_cloud(ax, before, after, color=style.DATA_CYCLE[0])
    evidence.binned_median(ax, before, after, nbins=8, color=style.DATA_CYCLE[1])
    ax.set_xlabel("Error, stage 1 (px)")
    ax.set_ylabel("Error, final (px)")
    prov.set("structure_strength", check)
    prov.set("below_diagonal", ax._anchor_paired["below_diagonal"])


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
