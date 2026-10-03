"""Recipe: per-row 100% stacked composition (e.g. conformal prediction-set sizes per cohort x class).

Use when: showing how a total splits into ordered parts across many rows. Light -> dark palette for
ordered parts; rows with no cases are an aux hatched "absent" bar, never blank.
Function: bars.stacked_fraction.
"""
import pandas as pd

from _common import run, style

NAME = "stacked_fraction"
RECIPE = dict(
    chart='100% 堆叠横条',
    category='分布与组成',
    use='展示多行中总量如何分配到几个有序部分',
    data='每行一组计数（或比例）',
    avoid='只有一个部分非零（删除或进表）；部分超过 ~5 个',
    functions=['bars.stacked_fraction'],
    tags=['composition', 'stacked bar', 'set size', '构成', '堆叠'],
    source='项目实战提炼',
)
SIZE = (style.SINGLE, style.SINGLE * 0.6)


def draw(ax, cfg, prov):
    from figkit.panels import bars
    pal = style.palette("setsize", cfg)
    rows = pd.DataFrame([
        ("Site A / Normal", 820, 140, 12), ("Site A / Lesion", 410, 230, 40),
        ("Site B / Normal", 300, 160, 25), ("Site B / Lesion", 0, 0, 0),
        ("Site C / Normal", 95, 70, 30), ("Site C / Lesion", 40, 55, 41),
    ], columns=["label", "1", "2", "3"])
    bars.stacked_fraction(ax, rows, ["1", "2", "3"], palette=pal)
    ax.set_xlabel("Fraction of scans")
    ax.legend(loc="lower right", frameon=True, framealpha=0.9, edgecolor="none", ncol=3,
              bbox_to_anchor=(1.0, 1.0), borderaxespad=0.1)
    prov.set("frac", ax._anchor_frac)
    prov.set("absent", ax._anchor_absent)


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
