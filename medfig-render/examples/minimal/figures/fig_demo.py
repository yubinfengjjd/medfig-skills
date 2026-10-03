"""Minimal mixed figure: B-scan with predicted boundaries (a), mean ± SD ROC over 5 runs (b),
confusion matrix with one absent row (c), subgroup estimates with 95% intervals (d).

Run from anywhere: ``python figures/fig_demo.py``. Paths come from ../figkit.toml; outputs go to
<out_dir>/figures/main/fig_demo.* and <out_dir>/panels/fig_demo/fig_demo_<id>.{pdf,svg}.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
if str(PROJECT) not in sys.path:
    sys.path.insert(0, str(PROJECT))
import _figkit_path  # noqa: E402,F401  (importable -> $FIGKIT_LIB -> repo lib -> installed skill)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from figkit import config, export, io, layout, panel, style  # noqa: E402
from figkit.panels import confusion, curves, imaging, intervals  # noqa: E402
from figkit.provenance import Provenance  # noqa: E402

NAME = "fig_demo"
SIZE = (style.DOUBLE, 4.2)
CLASSES = ["Alpha", "Beta", "Gamma"]
EXPECTED_ABSENT = ["Gamma"]  # documented: the synthetic set has no Gamma cases


def build(cfg):
    style.apply(cfg)
    prov = Provenance(NAME)
    rd = io.Reader(prov, cfg)
    z = rd.npz("bscan.npz")
    img, bnd = z["image"], z["boundaries"]
    roc = rd.csv("roc_runs.csv")
    cc = rd.csv("confusion.csv")
    iv = rd.csv("intervals.csv")

    fig = plt.figure(figsize=SIZE, layout="constrained")
    fig.get_layout_engine().set(w_pad=0.02, h_pad=0.02, wspace=0.04, hspace=0.04)
    H, W = img.shape
    gs = fig.add_gridspec(2, 3, width_ratios=[1.0, 1.0, 1.25])

    # a: image panel -- equal aspect, never stretched; row height sized to the image aspect (S1)
    ax_a = fig.add_subplot(gs[0, :])
    imaging.bscan_with_boundaries(ax_a, img, bnd)
    prov.set("a_native_shape", [H, W])
    prov.set("a_width_ratio", layout.image_width_ratios([(H, W)])[0])

    # b: mean ± SD ROC over repeated runs (S5)
    ax_b = fig.add_subplot(gs[1, 0])
    runs = [(g["y_true"].to_numpy(), g["score"].to_numpy()) for _, g in roc.groupby("run")]
    meth = style.palette("method", cfg)["model_a"]
    curves.roc_mean_sd(ax_b, runs, label=meth["label"], color=meth["color"])
    prov.set("b_n_runs", len(runs))
    prov.set("b_auc_mean_sd", [ax_b._anchor_mean_auc, ax_b._anchor_sd_auc])

    # c: confusion matrix; zero-count rows become "absent" automatically (never blank)
    ax_c = fig.add_subplot(gs[1, 1])
    confusion.matrix(ax_c, cc, CLASSES, tick_labels=["A", "B", "G"])
    if ax_c._anchor_absent != EXPECTED_ABSENT:
        raise RuntimeError(f"absent rows {ax_c._anchor_absent} != expected {EXPECTED_ABSENT}")
    prov.set("c_absent", ax_c._anchor_absent)
    prov.set("c_n_per_row", dict(zip(CLASSES, ax_c._anchor_counts.sum(1).astype(int).tolist())))

    # d: estimates with 95% intervals, dashed reference at the overall estimate
    ax_d = fig.add_subplot(gs[1, 2])
    overall = float(iv.loc[iv["label"] == "Overall", "est"].iloc[0])
    intervals.forest(ax_d, iv, ref=overall, band_rows=[0], color=meth["color"])
    ax_d.set_xlabel("Balanced accuracy (95% CI)")
    prov.set("d_n_rows", len(iv))

    for pid, ax in zip("abcd", (ax_a, ax_b, ax_c, ax_d)):
        panel.mark_panel(ax, pid)
    fig.canvas.draw()
    panel.label_panels(fig, [ax_a, ax_b, ax_c, ax_d], list("abcd"), cfg=cfg)
    return fig, prov


def main():
    cfg = config.load(PROJECT / "figkit.toml")
    fig, prov = build(cfg)
    return export.save(fig, NAME, prov, kind="main", size=SIZE, cfg=cfg)


if __name__ == "__main__":
    res = main()
    print(res["source"])
