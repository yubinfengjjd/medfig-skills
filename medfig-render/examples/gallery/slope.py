"""Recipe: slope chart across ordered conditions -- thin line per seed, bold mean per cohort.

Use when: a metric is compared across a few ordered rules / settings and seed spread matters.
Thin lines take the cohort colour at low alpha (never grey: they are data).
Function: intervals.slope.
"""
import numpy as np
import pandas as pd

from _common import run, style

NAME = "slope"
RECIPE = dict(
    chart='斜率图（重复细线 + 均值粗线）',
    category='区间与记分',
    use='少数几个有序条件下比较一个指标，并展示 seed 间离散',
    data='组 × 重复 × 条件 的长表',
    avoid='条件无序（不应连线，改点图）；条件超过 ~6 个',
    functions=['intervals.slope'],
    tags=['slope chart', 'seed', 'paired', '斜率图', '配对'],
    source='项目实战提炼',
)
SIZE = (style.SINGLE, style.SINGLE * 0.7)
RULES = ["R0", "R1", "R2"]


def draw(ax, cfg, prov):
    from figkit.panels import intervals
    rng = np.random.default_rng(60)
    pal = style.palette("cohort", cfg)
    rows = []
    for j, site in enumerate(pal):
        base = 0.80 - 0.06 * j
        for seed in range(3):
            for i, r in enumerate(RULES):
                rows.append((site, seed, r, base + 0.02 * i + rng.normal(0, 0.01)))
    df = pd.DataFrame(rows, columns=["site", "seed", "rule", "bacc"])
    intervals.slope(ax, df, x="rule", y="bacc", group="site", run="seed", order=RULES, colors=pal)
    for ln in ax.get_lines():  # legend shows cohort labels, not keys
        if ln.get_label() in pal:
            ln.set_label(pal[ln.get_label()]["label"])
    ax.set_ylabel("Balanced accuracy")
    ax.legend(loc="lower right", frameon=False)
    prov.set("mean", ax._anchor_slope_mean)


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
