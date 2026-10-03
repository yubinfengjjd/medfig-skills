"""Recipe: ROC small multiples -- one square cell per cohort, mean ± SD over runs per model.

Use when: the same models are compared on several cohorts. Cells are >= 1.6 in so a 3-entry
"model (AUC = mean ± SD)" legend fits at 6 pt (1-in cells overlap the curves). The whole grid is ONE
panel (first cell marked, other cells as extra_axes). Functions: layout.small_multiples + curves.roc_mean_sd.
"""
from _common import TOML, config, export, plt, scores, style

NAME = "roc_grid"
RECIPE = dict(
    chart='ROC 小多图',
    category='版式',
    use='同一组模型在多个队列上分别比较，每队列一格',
    data='队列 × 模型 × 重复的逐样本标签 + 分数',
    avoid='只有 1–2 个队列（直接并排两个 roc_mean_sd 即可）',
    functions=['layout.small_multiples', 'curves.roc_mean_sd'],
    tags=['ROC', 'small multiples', '队列', '小多图'],
    source='项目实战提炼',
)
COHORTS = ["site_a", "site_b", "site_c"]
MODELS = ["model_a", "model_b", "model_c"]


def build(cfg=None):
    from figkit import layout, panel
    from figkit.panels import curves
    from figkit.provenance import Provenance
    cfg = cfg or config.load(TOML)
    style.apply(cfg)
    prov = Provenance(NAME, cfg)
    fig = plt.figure(layout="constrained")
    axes, size = layout.small_multiples(fig, len(COHORTS), ncols=3, cell_in=1.6, legend_rows=0)
    fig.set_size_inches(*size)
    cohorts, models = style.palette("cohort", cfg), style.palette("model", cfg)
    auc = {}
    for j, (ax, c) in enumerate(zip(axes, COHORTS)):
        for i, m in enumerate(MODELS):
            runs = [scores(100 * j + 10 * i + s, n=300, sep=1.3 - 0.25 * i) for s in range(3)]
            curves.roc_mean_sd(ax, runs, label=models[m]["label"], color=models[m]["color"])
            ax.get_lines()[-1].set_linestyle(models[m]["linestyle"])
        ax.set_title(cohorts[c]["label"], loc="left", pad=2)
        if j:
            ax.set_ylabel("")
        auc[c] = {k: list(v) for k, v in ax._anchor_auc.items()}
    prov.set("auc_mean_sd", auc)
    panel.mark_panel(axes[0], "a", extra_axes=axes[1:])
    return fig, prov, size


def run(cfg=None):
    cfg = cfg or config.load(TOML)
    fig, prov, size = build(cfg)
    res = export.save(fig, NAME, prov, kind="gallery", size=size, cfg=cfg)
    plt.close(fig)
    return res


if __name__ == "__main__":
    print(run()["source"])
