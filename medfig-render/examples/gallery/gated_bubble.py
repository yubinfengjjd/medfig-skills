"""Recipe: per-concept AUROC bubbles with a reporting gate -- failing rows stay visible.

Use when: many sub-scores have very different support (n positives). Area ∝ n; passing = filled +
solid CI; failing = hollow + hatch + dashed CI + "(n)". Never drop or grey out failing rows.
Function: scatter.gated_bubble.
"""
import numpy as np
import pandas as pd

from _common import run, style

NAME = "gated_bubble"
RECIPE = dict(
    chart='闸门气泡图',
    category='分布与组成',
    use='很多子指标的支持度差异很大，需要标出哪些可报告',
    data='汇总行：每个子指标的估计、CI、n 和是否过闸门',
    avoid='所有子指标支持度相近（普通点 + CI 即可）',
    functions=['scatter.gated_bubble'],
    tags=['bubble', 'gate', 'support', '气泡', '闸门'],
    source='项目实战提炼',
)
SIZE = (style.SINGLE, style.SINGLE * 0.7)
GATE = 200


def draw(ax, cfg, prov):
    from figkit.panels import scatter
    rng = np.random.default_rng(70)
    n = np.array([1200, 640, 410, 260, 150, 60, 25, 9])
    est = np.clip(0.95 - 0.04 * np.arange(8) + rng.normal(0, 0.02, 8), 0.3, 0.99)
    half = 1.5 / np.sqrt(n)
    rows = pd.DataFrame(dict(x=n / 6000, est=est, lo=np.clip(est - half, 0, 1), hi=np.clip(est + half, 0, 1),
                             n=n, passes=n >= GATE, label=[f"C{i}" for i in range(8)]))
    scatter.gated_bubble(ax, rows, color=style.palette("cohort", cfg)["site_a"]["color"], ref=0.5)
    ax.set_xscale("log")
    style.log_ticks(ax, "x")  # matplotlib's default 10^{-k} uses an ASCII hyphen
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Prevalence")
    ax.set_ylabel("AUROC (95% CI)")
    prov.set("gate", {k: bool(v) for k, v in ax._anchor_gate.items()})
    prov.set("gate_n_min", GATE)


if __name__ == "__main__":
    import sys
    print(run(sys.modules[__name__])["source"])
