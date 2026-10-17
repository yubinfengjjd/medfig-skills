#!/usr/bin/env python3
"""EDITABLE trainer for the synthetic CPU protocol demo (NumPy, not PyTorch/GPU).

Writes metrics.jsonl per epoch on the validation split, keeps the best-val
checkpoint (primary_metric.selection = "best"), and for that checkpoint writes
cases.jsonl, weights.npz and result.json. Test data are never touched here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

import numpy as np

import model
import synth_data


def log_line(f, run_id, phase, step, metric, value):
    f.write(json.dumps({"run_id": run_id, "phase": phase, "step": step, "metric": metric, "value": value,
                        "time": datetime.now(timezone.utc).isoformat()}, allow_nan=False) + "\n")
    f.flush()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task", choices=("classification", "segmentation"), required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument("--epochs", type=int, default=40)
    p.add_argument("--width", type=int, default=8)
    p.add_argument("--learning-rate", type=float, default=0.3)
    a = p.parse_args()
    run_id, phase, out = os.environ["ME_RUN_ID"], os.environ["ME_PHASE"], Path(os.environ["ME_OUTPUT_DIR"])
    data = synth_data.build(a.task)
    tr, va = data["train"], data["val"]
    x = model.features(a.task, tr["images"])
    y = tr["targets"].reshape(-1, 1)
    if a.task == "segmentation":
        fg = float(np.mean(y))
        sample_w = np.where(y > 0.5, 0.5 / fg, 0.5 / (1 - fg))
    else:
        sample_w = np.ones_like(y)
    w = model.init(x.shape[1], a.width, a.seed)
    score = "accuracy" if a.task == "classification" else "dice"
    guard = "brier" if a.task == "classification" else "area_error"
    best = None
    with (out / "metrics.jsonl").open("x", encoding="utf-8", newline="\n") as f:
        for epoch in range(a.epochs + 1):
            if epoch:
                hidden, logits = model.forward(x, w)
                g_out = (model.sigmoid(logits) - y) * sample_w / len(y)
                g_hid = (g_out @ w["w2"].T) * (1 - hidden**2)
                grads = {"w1": x.T @ g_hid, "b1": g_hid.sum(0), "w2": hidden.T @ g_out, "b2": g_out.sum(0)}
                for k in w:
                    w[k] = w[k] - a.learning_rate * grads[k]
                    if not np.all(np.isfinite(w[k])):
                        print("non-finite weights", file=sys.stderr)
                        return 1
            metrics, cases = synth_data.evaluate(a.task, model.predict(a.task, va["images"], w), va["targets"], va["ids"])
            for k, v in metrics.items():
                log_line(f, run_id, phase, epoch, k, v)
            if best is None or metrics[score] > best[0]:
                best = (metrics[score], metrics, cases, {k: v.copy() for k, v in w.items()}, epoch)
    _, metrics, cases, weights, epoch = best
    np.savez_compressed(out / "weights.npz", **weights)
    with (out / "cases.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
    (out / "checkpoint.json").write_text(json.dumps({"selection": "best", "epoch": epoch, "metric": score}) + "\n", encoding="utf-8")
    result = {"run_id": run_id, "phase": phase, "completed": True,
              "metrics": {score: metrics[score], guard: metrics[guard]},
              "artifacts": ["weights.npz", "cases.jsonl", "checkpoint.json"]}
    tmp = out / "result.json.tmp"
    tmp.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    tmp.replace(out / "result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
