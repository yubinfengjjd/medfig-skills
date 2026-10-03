"""Recipe: mean ± SD ROC over repeated runs (seeds / folds), several models on one square axes.

Use when: >= 2 runs per model exist (else one curve, no band, say so in the caption).
Function: curves.roc_mean_sd (style after MenglinLu/Retinal_VascularEvents, MIT).
"""
from _common import run, scores, style

NAME = "roc_mean_sd"
RECIPE = dict(
    chart='ROC（多次重复均值 ± SD）',
    category='判别',
    use='比较几个模型的判别能力，每个模型有多个 seed / 折',
    data='每次重复的逐样本二分类标签 + 分数（或已算好的 fpr/tpr）',
    avoid='只有一次运行（改单条曲线、图注说明无 SD 带）；只有 AUC 数字没有曲线点',
    functions=['curves.roc_mean_sd'],
    tags=['ROC', 'AUC', 'seed', '判别', '受试者工作特征'],
    source='Retinal_VascularEvents ROC curve.py（MIT）',
)
SIZE = (style.SINGLE * 0.75, style.SINGLE * 0.75)


def draw(ax, cfg, prov):
    from figkit.panels import curves
    pal = style.palette("model", cfg)
    for i, (key, sep) in enumerate([("model_a", 1.4), ("model_b", 1.0), ("model_c", 0.7)]):
        runs = [scores(10 * i + s, sep=sep) for s in range(3)]
        st = pal[key]
        curves.roc_mean_sd(ax, runs, label=st["label"], color=st["color"])
        ax.get_lines()[-1].set_linestyle(st["linestyle"])
    prov.set("auc", {k: list(v) for k, v in ax._anchor_auc.items()})


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
