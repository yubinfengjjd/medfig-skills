"""Recipe: group-level scatter, marker area ∝ group size, cohort colour + marker, symlog x.

Use when: per-group agreement / heterogeneity vs a spread that spans zero to large values.
The size key is aux grey (not data). Function: scatter.sized.
"""
import numpy as np
import pandas as pd

from _common import run, style

NAME = "sized_scatter"
RECIPE = dict(
    chart='组级散点（面积 ∝ 组大小）',
    category='分布与组成',
    use='按组看一致性 / 异质性，组大小相差很大',
    data='每组一行：x、y、组大小、分组标签',
    avoid='组大小相近（点大小无信息）；点数 > ~2000（改 hexbin）',
    functions=['scatter.sized'],
    tags=['scatter', 'symlog', 'group size', '散点', '异质性'],
    source='项目实战提炼',
)
SIZE = (style.SINGLE, style.SINGLE * 0.85)


def draw(ax, cfg, prov):
    from figkit.panels import scatter
    rng = np.random.default_rng(80)
    rows = []
    for j, site in enumerate(style.palette("cohort", cfg)):
        m = 60 - 15 * j
        sd = np.where(rng.uniform(size=m) < 0.2, 0.0, rng.lognormal(-4, 1, m))
        agree = np.clip(1 - 2 * sd + rng.normal(0, 0.03, m), 0.3, 1.0)
        rows += [(site, s, a, int(k)) for s, a, k in zip(sd, agree, rng.integers(2, 300, m))]
    df = pd.DataFrame(rows, columns=["site", "sd", "agree", "n"])
    scatter.sized(ax, df, x="sd", y="agree", group="site", size="n",
                  palette=style.palette("cohort", cfg), key_sizes=[10, 100], symlog=True,
                  legend_loc="lower left")  # low SD -> high agreement, so the lower left stays empty
    ax.set_xlabel("Within-group SD")
    ax.set_ylabel("Label agreement")
    ax.set_ylim(0.3, 1.04)
    prov.set("groups", ax._anchor_groups)


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
