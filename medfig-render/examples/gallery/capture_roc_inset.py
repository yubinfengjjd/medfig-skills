"""Recipe: error-capture curves (colour = signal, linestyle = cohort) with a small ROC inset.

Use when: a triage / review-budget panel also needs a compact discrimination summary. The inset is a
CHILD axes (exported with the host panel, exempt from the whitespace audit); one single-run curve per
group, no ±SD band -- say so in the caption.
Functions: curves.capture(color_key=, style_key=), curves.roc_inset.
"""
import numpy as np
import pandas as pd

from _common import run, scores, style

NAME = "capture_roc_inset"
RECIPE = dict(
    chart='错误捕获曲线 + ROC 小插图',
    category='校准与效用',
    use='分诊 / 复核预算 panel，另需一个紧凑的判别摘要',
    data='每个信号 × 队列的 (预算, 捕获比例) 曲线点；插图要逐样本标签 + 分数',
    avoid='插图需要 ±SD（插图只画单条曲线）；主图曲线超过 6 条（太挤）',
    functions=['curves.capture', 'curves.roc_inset'],
    tags=['triage', 'error capture', 'inset', '分诊', '插图'],
    source='项目实战提炼',
)
SIZE = (style.SINGLE, style.SINGLE * 0.75)
SIGNALS = {"disagreement": "#AA4499", "low_confidence": "#44AA99"}


def draw(ax, cfg, prov):
    from figkit.panels import curves
    rows, ins = [], []
    budget = np.linspace(0, 1, 11)
    for j, cohort in enumerate(["Site A", "Site B"]):
        for k, sig in enumerate(SIGNALS):
            cap = budget ** (0.45 + 0.25 * k + 0.1 * j)
            rows += [(sig, cohort, b, c) for b, c in zip(budget, cap)]
            fpr, tpr = curves.roc_points(*scores(40 + 2 * j + k, sep=1.2 - 0.3 * k))
            ins.append(dict(fpr=fpr, tpr=tpr, color=SIGNALS[sig], linestyle=["-", "--"][j],
                            label=f"{sig} / {cohort}"))
    df = pd.DataFrame(rows, columns=["signal", "cohort", "budget", "capture"])
    curves.capture(ax, df, group=["signal", "cohort"], colors=SIGNALS,
                   color_key=lambda key: key[0], style_key=lambda key: key[1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.legend(loc="upper left", frameon=False, fontsize=6)
    inset = curves.roc_inset(ax, ins)
    prov.set("inset_auc", inset._anchor_auc)


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
