"""FROZEN: locked test evaluation. Run only by `controller.py test`.

Usage: python evaluate_test.py --task T --run-dir RUN --output OUT
Loads RUN/weights.npz with the model code of the tested commit (the controller
runs this from a detached checkout of that commit), scores the test split with
the same evaluation as validation, and writes OUT/cases.jsonl and OUT/result.json.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import model
import synth_data


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--task", choices=("classification", "segmentation"), required=True)
    p.add_argument("--run-dir", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()
    run, out = Path(a.run_dir), Path(a.output)
    with np.load(run / "weights.npz") as z:
        w = {k: z[k] for k in z.files}
    te = synth_data.build(a.task)["test"]
    metrics, cases = synth_data.evaluate(a.task, model.predict(a.task, te["images"], w), te["targets"], te["ids"])
    with (out / "cases.jsonl").open("w", encoding="utf-8", newline="\n") as f:
        for c in cases:
            f.write(json.dumps(c) + "\n")
    (out / "result.json").write_text(json.dumps({"completed": True, "metrics": metrics}, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
