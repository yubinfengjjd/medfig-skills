"""Recipe: reliability diagram, one curve per model, Brier score in the legend.

Use when: reporting whether predicted probabilities match observed event rates.
Function: curves.calibration (after MenglinLu/Retinal_VascularEvents Calibration plot.py, MIT).
"""
from _common import run, scores, style

NAME = "calibration"
RECIPE = dict(
    chart='可靠性图（校准曲线）',
    category='校准与效用',
    use='报告预测概率是否与实际事件率一致',
    data='逐样本二分类标签 + 预测概率（必须是 [0, 1] 概率，不是 logit）',
    avoid='输出不是概率（先校准或换图）；样本很少（每箱 < ~20 例，改用较少分箱或 quantile）',
    functions=['curves.calibration'],
    tags=['calibration', 'Brier', '校准', 'reliability'],
    source='Retinal_VascularEvents Calibration plot.py（MIT）',
)
SIZE = (style.SINGLE * 0.75, style.SINGLE * 0.75)


def draw(ax, cfg, prov):
    from figkit.panels import curves
    pal = style.palette("model", cfg)
    for i, (key, sep) in enumerate([("model_a", 1.4), ("model_b", 0.8)]):
        y, p = scores(20 + i, n=800, sep=sep)
        st = pal[key]
        curves.calibration(ax, y, p, label=st["label"], color=st["color"], marker=st["marker"],
                           n_bins=10, strategy="quantile")
    prov.set("brier", {k: v["brier"] for k, v in ax._anchor_calibration.items()})


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
