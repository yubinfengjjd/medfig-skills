"""Recipe: pre-registered hypothesis scorecard -- estimate + CI per hypothesis, coloured by status.

Use when: reporting H1..Hn honestly, including negative / inconclusive results. Every status is a
saturated colour + marker (no grey "inconclusive"); the legend lists only statuses present.
Function: intervals.scorecard (status palette from figkit.toml).
"""
import pandas as pd

from _common import run, style

NAME = "scorecard"
RECIPE = dict(
    chart='假设记分卡（点 + CI）',
    category='区间与记分',
    use='如实报告预注册假设 H1..Hn，包括阴性和不确定结果',
    data='汇总行：每个假设的估计、CI、状态',
    avoid='假设之间单位不同又要共用一个 x 轴（拆 panel 或标准化）',
    functions=['intervals.scorecard'],
    tags=['hypothesis', 'pre-registered', 'scorecard', '预注册', '记分卡'],
    source='项目实战提炼',
)
SIZE = (style.SINGLE, style.SINGLE * 0.6)


def draw(ax, cfg, prov):
    from figkit.panels import intervals
    rows = pd.DataFrame([
        ("H1 vs baseline", 0.001, -0.004, 0.006, "inconclusive"),
        ("H2 concept gate", -0.030, -0.052, -0.008, "not_supported"),
        ("H3 localisation", 0.041, 0.012, 0.070, "supported"),
        ("H4 abstention", 0.233, 0.153, 0.319, "supported"),
    ], columns=["label", "est", "lo", "hi", "status"])
    # the bottom row (H4) sits at the right, so the legend goes to the empty centre right
    intervals.scorecard(ax, rows, style.palette("status", cfg), ref=0.0, legend_loc="center right")
    ax.set_xlabel("Effect (95% CI)")
    prov.set("status", ax._anchor_status)


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
