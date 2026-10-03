"""Recipe: multi-metric comparison bars (soft theme) -- one small axes per metric, same method order and
colours in every axes, one framed legend axes on the right, the proposed method in the one saturated colour.

Look after senlanke/figures4papers style 1 (no licence: idea only, re-derived): flat bars, light pastel
controls, values on the bars, thin dark min-max whiskers over 3 seeds (stated in the caption, no run
points), value axis truncated below the data with a break mark when the bars would otherwise look flat.
Functions: compare.metric_bars + compare.legend_panel; theme = "soft".
"""
import numpy as np
import pandas as pd

from _common import TOML, config, export, plt, style

NAME = "multi_metric_bars"
RECIPE = dict(
    chart='多指标对比柱（共享图例 panel）',
    category='区间与记分',
    use='几个方法在 2–4 个指标上并排比较，本文方法用唯一饱和色突出，对照方法用浅色，指标间顺序和颜色一致',
    data='方法 × 指标 × 重复（seed / 折）的长表',
    avoid='方法超过 6 个（浅色不够分，改分组或小多图）；只有一个指标（直接点图）；截断 y 轴却不画断轴标记（导出闸门会拦）',
    functions=['compare.metric_bars', 'compare.legend_panel', 'style.soft_controls', 'style.axis_break'],
    tags=['bar', 'multi-metric', 'soft theme', 'figures4papers', '柱状图', '多指标'],
    source='风格参考 senlanke/figures4papers 样式 1（无许可证，仅借鉴思路，代码重写）',
)
METHODS = ["base_1", "base_2", "base_3", "ours"]
LABELS = {"base_1": "Baseline 1", "base_2": "Baseline 2", "base_3": "Baseline 3", "ours": "Proposed"}
METRICS = {"AUROC": (0.80, 0.84, 0.86, 0.92), "AUPRC": (0.62, 0.68, 0.71, 0.80),
           "Sensitivity": (0.874, 0.882, 0.889, 0.921)}


def build(cfg=None):
    from figkit import panel
    from figkit.panels import compare
    from figkit.provenance import Provenance
    cfg = cfg or config.load(TOML)
    cfg.theme = "soft"
    style.apply(cfg)
    prov = Provenance(NAME, cfg)
    size = (style.DOUBLE, 2.0)
    fig, axes = plt.subplots(1, len(METRICS) + 1, figsize=size, layout="constrained",
                             gridspec_kw=dict(width_ratios=[1] * len(METRICS) + [0.7]))
    rng = np.random.default_rng(7)
    out = {}
    for ax, (metric, base) in zip(axes, METRICS.items()):
        df = pd.DataFrame([(m, r, b + rng.normal(0, 0.006)) for m, b in zip(METHODS, base) for r in range(3)],
                          columns=["method", "run", "value"])
        compare.metric_bars(ax, df, metric, METHODS, emphasis="ours")
        out[metric] = dict(bars=ax._anchor_bars, ylim=list(ax._anchor_ylim), truncated=ax._anchor_truncated)
    compare.legend_panel(axes[-1], METHODS, labels=LABELS, emphasis="ours")
    for ax, lab in zip(axes, "abc"):
        panel.mark_panel(ax, lab)
    prov.set("metrics", out)
    prov.set("whisker", axes[0]._anchor_whisker)  # caption: "whiskers: min–max over 3 seeds"
    return fig, prov, size


def run(cfg=None):
    cfg = cfg or config.load(TOML)
    fig, prov, size = build(cfg)
    res = export.save(fig, NAME, prov, kind="gallery", size=size, cfg=cfg)
    plt.close(fig)
    return res


if __name__ == "__main__":
    print(run()["source"])
