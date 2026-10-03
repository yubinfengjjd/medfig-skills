"""Recipe: risk-coverage (selective prediction) curve, AURC in the legend.

Use when: showing how the error rate on retained cases falls as the model abstains on low confidence.
Function: curves.risk_coverage.
"""
import numpy as np

from _common import run, style

NAME = "risk_coverage"
RECIPE = dict(
    chart='风险–覆盖曲线',
    category='校准与效用',
    use='模型可以弃权时，展示保留比例与错误率的关系',
    data='逐样本是否预测正确（0/1）+ 置信度分数',
    avoid='没有可用的置信度 / 不确定性分数',
    functions=['curves.risk_coverage'],
    tags=['selective prediction', 'AURC', 'abstention', '弃权', '覆盖率'],
    source='项目实战提炼',
)
SIZE = (style.SINGLE, style.SINGLE * 0.7)


def draw(ax, cfg, prov):
    from figkit.panels import curves
    pal = style.palette("model", cfg)
    for i, (key, k) in enumerate([("model_a", 4.0), ("model_b", 1.5)]):
        rng = np.random.default_rng(50 + i)
        conf = rng.uniform(size=1000)
        correct = (rng.uniform(size=1000) < 0.55 + 0.4 * conf ** (1 / k)).astype(int)
        st = pal[key]
        curves.risk_coverage(ax, correct, conf, label=st["label"], color=st["color"], linestyle=st["linestyle"])
    prov.set("aurc", {k: v["aurc"] for k, v in ax._anchor_rc.items()})


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
