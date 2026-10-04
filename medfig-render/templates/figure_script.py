"""Figure 1 (TODO): one-sentence conclusion of the whole figure.

Skeleton for one medfig-render figure: style.apply -> Reader -> GridSpec (layout.image_width_ratios)
-> panels -> mark_panel / label_panels -> export.save. Copy to <project>/scripts/fig1.py and edit the
TODO lines. Tests import this file and call build() -> (fig, prov); only __main__ exports.

Example panels (replace with the ones in your figure spec):
  a  image + low-resolution model probability map (imaging.prob_overlay, resampling for the caption)
  b  mean ± SD ROC over repeated runs (curves.roc_mean_sd, kind="scores")
  c  row-normalised confusion matrix with automatic absent rows (confusion.matrix)

Inputs (paths relative to data_root in figkit.toml):
  images/case01.npz          arrays "image" (H, W) and "prob" (h, w), prob in [0, 1]
  scores/roc_runs.csv        columns model, run, y_true, y_score
  tables/confusion.csv       columns truth, prediction, count
"""
import os
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# figkit lives in the installed skill; FIGKIT_LIB / FIGKIT_TOML override the defaults (tests, CI).
FIGKIT_LIB = Path(os.environ.get("FIGKIT_LIB", "~/.claude/skills/medfig-render/lib")).expanduser()
if str(FIGKIT_LIB) not in sys.path:
    sys.path.insert(0, str(FIGKIT_LIB))

from figkit import config, export, layout, panel, qa, style  # noqa: E402
from figkit.io import Reader  # noqa: E402
from figkit.panels import confusion, curves, imaging  # noqa: E402
from figkit.provenance import Provenance  # noqa: E402

# TODO: project toml (default: <project>/figkit.toml when this script sits in <project>/scripts/)
TOML = Path(os.environ.get("FIGKIT_TOML", Path(__file__).resolve().parents[1] / "figkit.toml"))
NAME, KIND = "fig1", "main"          # TODO: figure name; "main" or "supp"
SIZE = (style.DOUBLE, 6.0)           # final size in inches: QA runs at exactly this size
# Row a = full-width image (wide B-scan); row b/c = ROC + confusion side by side. Each stats panel is
# ~3.5 in wide, so the ROC legend "Model A (AUC = 0.973 ± 0.010)" (~1.5 in) fits inside its axes.
# A tall image (H > W / 2) would letterbox left/right here (S1 FAIL): put it in its own column instead.
CBAR_W = 0.6                         # inches taken by the colourbar next to the image
CLASSES = ["normal", "lesion_a", "lesion_b"]  # TODO: class order from the spec
# TODO: legend label -> value in the 'model' column; one ROC curve per entry, drawn in this order.
# Default: only the first model ("model_a"); add entries to compare models on the same axes.
MODELS = {"Model A": "model_a"}


def build():
    """Draw the figure at its final size; return (fig, prov). No file is written here."""
    cfg = config.load(TOML)
    style.apply(cfg)
    prov = Provenance(NAME)
    rd = Reader(prov, cfg)

    # ---- data (every number shown below is computed from these frames, never typed in)
    z = rd.npz("images/case01.npz")
    img, prob = z["image"], z["prob"]
    roc = rd.csv("scores/roc_runs.csv")
    cm = rd.csv("tables/confusion.csv")

    # ---- layout: image row height follows the image aspect at full width (S1: a slightly taller row
    # only letterboxes top/bottom, never left/right); stats row takes the rest.
    img_h = 1.05 * (SIZE[0] - CBAR_W) / layout.image_width_ratios([img.shape[:2]])[0]
    fig = plt.figure(figsize=SIZE, layout="constrained")
    gs = fig.add_gridspec(2, 2, height_ratios=[img_h, max(SIZE[1] - img_h, 3.2)])
    ax_img = fig.add_subplot(gs[0, :])
    ax_roc, ax_cm = fig.add_subplot(gs[1, 0]), fig.add_subplot(gs[1, 1])

    # a: probability map on a fixed [0, 1] scale; resampling recorded for the caption
    imaging.prob_overlay(ax_img, img, prob, vmin=0.0, vmax=1.0, resample="bilinear")
    cb = fig.colorbar(ax_img._anchor_mappable, ax=ax_img, fraction=0.05, pad=0.02)
    cb.set_label("Model probability", fontsize=6)
    cb.ax.tick_params(labelsize=6, length=2)
    src, dst, method = ax_img._anchor_resampled
    prov.set("a_resampled", {"from": list(src), "to": list(dst), "method": method})
    prov.add_transform(f"a: probability map resampled {tuple(src)} -> {tuple(dst)} ({method}); "
                       "fixed colour scale 0-1")

    # b: one mean ± SD ROC per model over runs (seeds / folds)
    b = {}
    for label, key in MODELS.items():
        sub = roc[roc["model"] == key]
        if sub.empty:
            raise ValueError(f"no rows for model {key!r} in scores/roc_runs.csv")
        runs = [(g["y_true"].to_numpy(), g["y_score"].to_numpy()) for _, g in sub.groupby("run")]
        curves.roc_mean_sd(ax_roc, runs, label=label, kind="scores")
        n = sub.groupby("run").size()  # n per run over ALL runs (runs may differ)
        mean, sd = ax_roc._anchor_auc[label]
        b[label] = {"n_runs": len(runs), "n_min": int(n.min()), "n_max": int(n.max()),
                    "auc_mean": mean, "auc_sd": sd}
    prov.set("b_roc", b)

    # c: confusion matrix; zero-total rows become hatched "absent" rows automatically
    confusion.matrix(ax_cm, cm, CLASSES, annot="pct", tick_labels=["N", "A", "B"])
    prov.set("c_n", int(cm["count"].sum()))
    prov.set("c_absent", ax_cm._anchor_absent)

    # ---- panels: mark for S4 standalone export, then letter them (letters only in the composite)
    panel.mark_panel(ax_img, "a", extra_axes=[cb.ax])
    panel.mark_panel(ax_roc, "b")
    panel.mark_panel(ax_cm, "c")
    fig.set_size_inches(*SIZE)
    fig.canvas.draw()
    panel.label_panels(fig, [ax_img, ax_roc, ax_cm], ["a", "b", "c"], cfg=cfg)
    return fig, prov


def caption(prov):
    """Caption draft built from provenance values (no typed-in numbers); checked for banned words."""
    v = prov.values
    r = v["a_resampled"]
    parts = []
    for label, m in v["b_roc"].items():
        auc = (f"{m['auc_mean']:.3f} ± {m['auc_sd']:.3f} (mean ± SD over {m['n_runs']} runs)"
               if m["n_runs"] > 1 else f"{m['auc_mean']:.3f} (single run; no SD band)")
        n = str(m["n_min"]) if m["n_min"] == m["n_max"] else f"{m['n_min']}–{m['n_max']}"
        parts.append(f"{label}, AUC = {auc}, n = {n} images per run")
    absent = ", ".join(v["c_absent"]) or "none"
    text = (
        "Figure 1 | TODO one-sentence conclusion. "
        f"a, Model probability map (not a mask), resampled from {r['from'][0]}×{r['from'][1]} to "
        f"{r['to'][0]}×{r['to'][1]} pixels ({r['method']}); fixed colour scale 0–1. "
        f"b, ROC curves: {'; '.join(parts)}; shaded band = ±1 SD across runs, not a confidence "
        "interval. "
        f"c, Row-normalised confusion matrix, n = {v['c_n']} images; absent classes (hatched): {absent}."
    )
    # no per-figure exploratory statement and no development history (mainline_rules.md)
    hits = qa.banned_in_text(text) + qa.dev_history_in_text(text)
    if hits:
        raise RuntimeError(f"caption contains banned words: {hits}")
    return text


if __name__ == "__main__":
    fig, prov = build()
    text = caption(prov)  # banned-word check first: a hit fails before any file is written
    res = export.save(fig, NAME, prov, kind=KIND, size=SIZE)  # the only export; never wrap in try/except
    cap = Path(res["source"]).with_name(f"{NAME}.caption.md")
    cap.write_text(text + "\n", encoding="utf-8")
    print("\n".join(res["files"] + [str(res["source"]), str(cap)]))
