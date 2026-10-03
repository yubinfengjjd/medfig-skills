"""Recipe: cumulative area trend (soft theme) -- light tint fill + a line one tone darker per series, the
hatched fill in that darker tone (greyscale), legend handles = fill + line, optional event arrow.

Look after senlanke/figures4papers (ophthalmology review trend; no licence: idea only, re-derived).
Function: compare.area_trend.
"""
import numpy as np

from _common import run, style

NAME = "area_trend"
THEME = "soft"
RECIPE = dict(
    chart='累计面积趋势图',
    category='分布与组成',
    use='两三个类别随时间的累计数量（文献数、入组数、病例数），可标一两个事件',
    data='时间点 × 类别 的计数表',
    avoid='类别超过 3 个（面积互相遮挡，改小多图或折线）；需要比较比例而非数量（改堆叠比例）',
    functions=['compare.area_trend'],
    tags=['area', 'trend', 'cumulative', 'soft theme', 'figures4papers', '面积图', '趋势'],
    source='风格参考 senlanke/figures4papers（无许可证，仅借鉴思路，代码重写）',
)
SIZE = (style.SINGLE, style.SINGLE * 0.66)


def draw(ax, cfg, prov):
    from figkit.panels import compare
    rng = np.random.default_rng(11)
    months = np.arange(36)
    series = {"OCT": rng.poisson(4 + months / 6), "Fundus": rng.poisson(2 + months / 12)}
    compare.area_trend(ax, months, series, cumulative=True, hatches={"Fundus": "////"},
                       events=[(18, "Public dataset")])
    ax.set_xlabel("Month")
    ax.set_ylabel("Cumulative publications")
    prov.set("cumulative", {k: v.tolist() for k, v in ax._anchor_area.items()})


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
