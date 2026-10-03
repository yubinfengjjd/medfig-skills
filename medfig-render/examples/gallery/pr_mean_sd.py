"""Recipe: mean ± SD precision-recall over runs, prevalence baseline as aux dotted line.

Use when: classes are imbalanced and ROC alone hides the positive-class trade-off.
Function: curves.pr_mean_sd (AP = sklearn average_precision_score definition).
"""
from _common import run, scores, style

NAME = "pr_mean_sd"
RECIPE = dict(
    chart='PR 曲线（多次重复均值 ± SD）',
    category='判别',
    use='类别不平衡，需要看阳性类的精度–召回取舍',
    data='每次重复的逐样本二分类标签 + 分数',
    avoid='类别基本平衡（ROC 已足够）；只有 AP 数字',
    functions=['curves.pr_mean_sd'],
    tags=['PR', 'AP', 'precision', 'recall', '不平衡'],
    source='项目实战提炼',
)
SIZE = (style.SINGLE * 0.75, style.SINGLE * 0.75)


def draw(ax, cfg, prov):
    from figkit.panels import curves
    pal = style.palette("model", cfg)
    for i, (key, sep) in enumerate([("model_a", 1.4), ("model_b", 0.9)]):
        runs = [scores(40 + 10 * i + s, sep=sep, prev=0.2) for s in range(3)]
        st = pal[key]
        curves.pr_mean_sd(ax, runs, label=st["label"], color=st["color"], prevalence=(i == 0))
    prov.set("ap", {k: [v["mean_ap"], v["sd_ap"]] for k, v in ax._anchor_pr.items()})


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
