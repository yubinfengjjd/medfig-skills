"""FROZEN: synthetic data, fixed patient split and evaluation for the protocol demo.

Not medical data and not medical validation. One 16x16 image per synthetic
patient; split 48/16/16 (train/val/test) by patient with a fixed seed. The
evaluation functions here are shared by training (val) and the locked test
script so that every candidate is scored by identical code.
"""
from __future__ import annotations

import os

for _thread_setting in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_thread_setting, "1")

import numpy as np

IMAGE_SIZE = 16
DATA_SEED = 2026
PATIENT_COUNT = 80
SPLIT_SIZES = {"train": 48, "val": 16, "test": 16}


def patient_id(index: int) -> str:
    return f"synthetic-patient-{index:04d}"


def build(task: str) -> dict[str, dict[str, np.ndarray]]:
    images = np.empty((PATIENT_COUNT, IMAGE_SIZE, IMAGE_SIZE), dtype=np.float64)
    masks = np.empty_like(images)
    labels = np.arange(PATIENT_COUNT) % 2
    yy, xx = np.mgrid[:IMAGE_SIZE, :IMAGE_SIZE]
    for i in range(PATIENT_COUNT):
        rng = np.random.default_rng(np.random.SeedSequence([DATA_SEED, i, 701]))
        cx, cy = rng.uniform(5.0, 10.0, size=2)
        radius = rng.uniform(2.8, 4.2)
        mask = ((xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2).astype(np.float64)
        if task == "classification" and labels[i] == 0:
            mask[:] = 0.0
        noise = rng.normal(0.0, 0.07, size=(IMAGE_SIZE, IMAGE_SIZE))
        # Weak signal so that model choices matter in the demo.
        images[i] = np.clip(0.15 + rng.uniform(-0.03, 0.03) + noise + 0.18 * mask, 0.0, 1.0)
        masks[i] = mask
    order = np.random.default_rng(np.random.SeedSequence([DATA_SEED, 991])).permutation(PATIENT_COUNT)
    targets = labels.astype(np.float64) if task == "classification" else masks
    out, start = {}, 0
    for name, size in SPLIT_SIZES.items():
        idx = order[start:start + size]
        start += size
        out[name] = {"images": images[idx], "targets": targets[idx],
                     "ids": np.array([patient_id(int(i)) for i in idx])}
    return out


def evaluate(task: str, probabilities: np.ndarray, targets: np.ndarray, ids: np.ndarray) -> tuple[dict, list[dict]]:
    """probabilities: (n,) for classification, (n, H, W) for segmentation."""
    cases = []
    if task == "classification":
        correct = (probabilities >= 0.5) == (targets >= 0.5)
        for cid, y, p, ok in zip(ids, targets, probabilities, correct):
            cases.append({"case_id": str(cid), "label": int(y), "score": float(p), "value": float(ok)})
        brier = float(np.mean((probabilities - targets) ** 2))
        metrics = {"accuracy": float(np.mean(correct)), "brier": brier}
    else:
        pred = probabilities >= 0.5
        truth = targets >= 0.5
        inter = np.sum(pred & truth, axis=(1, 2))
        denom = np.sum(pred, axis=(1, 2)) + np.sum(truth, axis=(1, 2))
        dice = np.divide(2.0 * inter, denom, out=np.ones(len(ids)), where=denom != 0)
        for cid, d in zip(ids, dice):
            cases.append({"case_id": str(cid), "value": float(d)})
        area_error = float(np.mean(np.abs(pred.mean(axis=(1, 2)) - truth.mean(axis=(1, 2)))))
        metrics = {"dice": float(np.mean(dice)), "area_error": area_error}
    return metrics, cases
