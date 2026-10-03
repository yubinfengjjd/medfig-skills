"""Recipe: decision curve (net benefit vs threshold) with treat all / treat none references.

Use when: a descriptive clinical-utility panel is in the spec. State in the caption that thresholds
were not tuned on the test set and that the curve does not license clinical decisions.
Function: curves.decision (after MenglinLu/Retinal_VascularEvents Decision curve.py, MIT).
"""
from _common import run, scores, style

NAME = "decision"
RECIPE = dict(
    chart='决策曲线 DCA',
    category='校准与效用',
    use='规格要求描述性的临床效用 panel',
    data='逐样本二分类标签 + 预测概率',
    avoid='阈值是在测试集上调的；想据此声称临床获益（禁用词）',
    functions=['curves.decision'],
    tags=['DCA', 'net benefit', '决策曲线', '净获益', '临床效用'],
    source='Retinal_VascularEvents Decision curve.py（MIT）',
)
SIZE = (style.SINGLE, style.SINGLE * 0.7)


def draw(ax, cfg, prov):
    from figkit.panels import curves
    pal = style.palette("model", cfg)
    out = {}
    for i, key in enumerate(["model_a", "model_b"]):
        y, p = scores(30, n=800, sep=1.4 - 0.5 * i)  # same patients -> one shared treat-all line
        st = pal[key]
        curves.decision(ax, y, p, label=st["label"], color=st["color"], linestyle=st["linestyle"],
                        treat_all=(i == 0), treat_all_color="aux", ylim=(-0.05, 0.45))
    for k, v in ax._anchor_dca.items():
        out[k] = dict(clipped_from=v["clipped_from"], max=v["max"])
    prov.set("dca", out)


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
