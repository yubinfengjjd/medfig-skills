"""Recipe: ROC small multiples -- one square cell per cohort in ONE row, mean ± SD over runs per model.

Use when: the same models are compared on several cohorts. Facet rule S8: one row when the cells fit
(else layout.small_multiples centres the short last row); ONE shared key over the row
(curves.shared_key) and per-cell AUC as a coloured text block (curves.value_block) -- never the same
3-entry legend repeated in every cell (qa.repeated_legend fails it). With the key moved out, 1.2-in cells
are enough. The whole grid is ONE panel (first cell marked, other cells as extra_axes).
"""
from _common import TOML, config, export, plt, scores, style

NAME = "roc_grid"
RECIPE = dict(
    chart='ROC 小多图',
    category='版式',
    use='同一组模型在多个队列上分别比较，每队列一格',
    data='队列 × 模型 × 重复的逐样本标签 + 分数',
    avoid='只有 1–2 个队列（直接并排两个 roc_mean_sd 即可）；每格各画一份同样的图例',
    functions=['layout.small_multiples', 'curves.roc_mean_sd', 'curves.shared_key', 'curves.value_block'],
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
    fig = plt.figure(layout="constrained")  # frozen before the shared key is placed
    axes, size = layout.small_multiples(fig, len(COHORTS), ncols=len(COHORTS), cell_in=1.25)
    size = (size[0], size[1] + 0.25)  # headroom for the one-row shared key above the titles
    fig.set_size_inches(*size)
    fig.get_layout_engine().set(rect=(0, 0, 1, 1 - 0.25 / size[1]))
    cohorts, models = style.palette("cohort", cfg), style.palette("model", cfg)
    auc = {}
    for j, (ax, c) in enumerate(zip(axes, COHORTS)):
        for i, m in enumerate(MODELS):
            runs = [scores(100 * j + 10 * i + s, n=300, sep=1.3 - 0.25 * i) for s in range(3)]
            curves.roc_mean_sd(ax, runs, label=models[m]["label"], color=models[m]["color"],
                               linestyle=models[m]["linestyle"], legend=False)
        ax.set_title(cohorts[c]["label"], pad=2)
        if j:
            ax.set_ylabel("")
            ax.tick_params(labelleft=False)
        auc[c] = {k: list(v) for k, v in ax._anchor_auc.items()}
        curves.value_block(ax, [ax._anchor_auc[models[m]["label"]] for m in MODELS],
                           [models[m]["color"] for m in MODELS])
    fig.canvas.draw()
    fig.set_layout_engine("none")  # freeze the cell geometry, then put the key above the titles
    curves.shared_key(fig, axes, [dict(label=models[m]["label"] + " (AUC = mean ± SD)" if i == 0 else
                                       models[m]["label"], color=models[m]["color"],
                                       linestyle=models[m]["linestyle"]) for i, m in enumerate(MODELS)])
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
