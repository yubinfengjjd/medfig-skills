"""FROZEN: write the split audit consumed by `controller.py audit`.

Usage: python audit_split.py --task classification --output PATH
Lists pseudonymised group IDs and class counts per split. The controller checks
that groups are disjoint across splits; it does not judge label quality.
"""
import argparse
import json

import numpy as np

import synth_data


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task", choices=("classification", "segmentation"), required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    data = synth_data.build(a.task)
    splits = {}
    for name, part in data.items():
        if a.task == "classification":
            counts = {str(k): int(v) for k, v in zip(*np.unique(part["targets"].astype(int), return_counts=True))}
        else:
            fg = part["targets"].reshape(len(part["ids"]), -1).max(axis=1).astype(int)
            counts = {"with_foreground": int(fg.sum()), "empty": int(len(fg) - fg.sum())}
        splits[name] = {"group_ids": [str(i) for i in part["ids"]], "class_counts": counts}
    with open(a.output, "w", encoding="utf-8") as f:
        json.dump({"group_unit": "patient", "splits": splits,
                   "note": "synthetic; one image per patient"}, f, indent=2)
        f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
