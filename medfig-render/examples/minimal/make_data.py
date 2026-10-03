"""Generate the synthetic inputs of the minimal example into ./data (deterministic, seed 20260930).

Files:
  bscan.npz        image (H, W) float in [0, 1] -- a layered grey "B-scan"; boundaries (K, M) in [0, 1]
                   of image height (predicted layer boundaries sampled at linspace(0, W - 1, M))
  roc_runs.csv     run, y_true, score  -- 5 repeated runs (seeds) of one binary classifier
  confusion.csv    truth, prediction, count -- 3 classes; class "Gamma" has no cases (count 0)
  intervals.csv    label, est, lo, hi -- per-subgroup estimate with 95% interval
Everything is synthetic; no study data.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter

SEED = 20260930
H, W, M = 96, 384, 64
HERE = Path(__file__).resolve().parent


def bscan(rng):
    x = np.linspace(0, 1, W)
    # three smooth layer boundaries (fraction of height), gently curved
    b = np.vstack([0.30 + 0.05 * np.sin(2 * np.pi * x),
                   0.50 + 0.04 * np.sin(2 * np.pi * x + 0.6),
                   0.72 + 0.03 * np.cos(2 * np.pi * x)])
    rows = np.arange(H)[:, None] / H
    img = np.full((H, W), 0.08)
    img += 0.55 * ((rows >= b[0]) & (rows < b[1]))
    img += 0.30 * ((rows >= b[1]) & (rows < b[2]))
    img += 0.75 * (np.abs(rows - b[2]) < 0.025)
    img = gaussian_filter(img + rng.normal(0, 0.08, img.shape), 1.0)
    img = np.clip((img - img.min()) / (img.max() - img.min()), 0, 1)
    xs = np.linspace(0, W - 1, M).round().astype(int)
    pred = b[:, xs] + rng.normal(0, 0.006, (3, M))  # "predicted" boundaries = truth + small error
    return img, np.clip(pred, 0, 1)


def roc_runs(rng, n_runs=5, n=200):
    out = []
    for r in range(n_runs):
        y = rng.integers(0, 2, n)
        score = rng.normal(0, 1, n) + (1.3 + 0.1 * r) * y
        out.append(pd.DataFrame({"run": r, "y_true": y, "score": score.round(5)}))
    return pd.concat(out, ignore_index=True)


def confusion(rng):
    classes = ["Alpha", "Beta", "Gamma"]
    rows = []
    for t in classes:
        for p in classes:
            if t == "Gamma":
                n = 0  # no Gamma cases in this synthetic set -> must render as "absent"
            else:
                n = int(rng.integers(60, 90)) if t == p else int(rng.integers(2, 15))
            rows.append((t, p, n))
    return pd.DataFrame(rows, columns=["truth", "prediction", "count"])


def intervals(rng):
    labels = ["Overall", "Age < 60", "Age ≥ 60", "Site 1", "Site 2"]
    est = 0.80 + rng.normal(0, 0.03, len(labels))
    half = rng.uniform(0.02, 0.06, len(labels))
    return pd.DataFrame({"label": labels, "est": est.round(4),
                         "lo": (est - half).round(4), "hi": (est + half).round(4)})


def main(data_dir=HERE / "data"):
    rng = np.random.default_rng(SEED)
    d = Path(data_dir)
    d.mkdir(parents=True, exist_ok=True)
    img, pred = bscan(rng)
    np.savez(d / "bscan.npz", image=img, boundaries=pred)
    roc_runs(rng).to_csv(d / "roc_runs.csv", index=False)
    confusion(rng).to_csv(d / "confusion.csv", index=False)
    intervals(rng).to_csv(d / "intervals.csv", index=False)
    return d


if __name__ == "__main__":
    print(main())
