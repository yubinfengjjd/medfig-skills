"""Recipe: odds ratio of each predicted-risk decile vs the lowest decile (log-x forest).

Use when: showing risk stratification of a score (does observed risk rise across groups?).
Functions: stats.risk_group_or (Woolf CI, Haldane 0.5 correction flagged), intervals.or_forest
(after MenglinLu/Retinal_VascularEvents OR.py, MIT).
"""
from _common import run, scores, style

NAME = "or_forest"
RECIPE = dict(
    chart='风险分组 OR 森林图',
    category='区间与记分',
    use='展示风险评分的分层能力：各风险组相对最低组的 OR',
    data='逐样本二分类结局 + 预测风险分数',
    avoid='事件很少导致多个零格（OR 不稳定，改报事件率）',
    functions=['stats.risk_group_or', 'intervals.or_forest'],
    tags=['OR', 'odds ratio', 'decile', '风险分层', '比值比'],
    source='Retinal_VascularEvents OR.py（MIT）',
)
SIZE = (style.SINGLE * 0.8, style.SINGLE * 0.8)


def draw(ax, cfg, prov):
    from figkit import stats
    from figkit.panels import intervals
    y, p = scores(50, n=3000, sep=0.9, prev=0.25)
    t = stats.risk_group_or(y, p, n_groups=10)
    t["label"] = [f"D{g}" for g in t["group"]]
    intervals.or_forest(ax, t, color=style.palette("model", cfg)["model_a"]["color"])
    ax.set_ylabel("Predicted-risk decile")
    prov.set("or", t[["label", "n", "events", "or_", "lo", "hi", "corrected"]].to_dict("records"))


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
