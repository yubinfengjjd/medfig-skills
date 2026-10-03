"""Recipe: Bland-Altman agreement -- difference vs mean of paired measurements, bias and limits of
agreement (bias ± 1.96 SD, sample SD) as labelled reference lines.

Use for model-vs-measurement agreement (e.g. predicted vs measured thickness). Bias / limits match
statsmodels' mean_diff_plot when ``ddof=0`` (tested). Function: evidence.bland_altman.
"""
import numpy as np

from _common import run, style

NAME = "bland_altman"
RECIPE = dict(
    chart='Bland–Altman 一致性图',
    category='校准与效用',
    use='两种测量（模型预测 vs 实测，或两台设备）在同一批样本上的一致性',
    data='逐样本成对测量值（同一单位）',
    avoid='两者单位不同或量纲不可比；想证明相关性（相关高不等于一致，相关用散点）',
    functions=['evidence.bland_altman', 'stats.bland_altman'],
    tags=['Bland-Altman', 'agreement', 'limits of agreement', '一致性'],
    source='经典方法（Bland & Altman 1986），数值与 statsmodels 对照',
)
SIZE = (style.SINGLE, style.SINGLE * 0.72)


def draw(ax, cfg, prov):
    from figkit.panels import evidence
    rng = np.random.default_rng(31)
    measured = rng.normal(290, 45, 300)
    predicted = measured + rng.normal(4, 11, 300)
    evidence.bland_altman(ax, predicted, measured, units="µm")
    prov.set("agreement", ax._anchor_ba)


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
