"""Shared helpers for the panel gallery recipes: config, synthetic data, single-panel export.

Every recipe module defines NAME, SIZE and ``draw(ax, cfg, prov)`` (optionally THEME = "soft"); ``run(module)`` builds the figure,
exports it with ``export.save`` (all QA gates must be empty) and returns the result dict.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import _figkit_path  # noqa: E402,F401

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from figkit import config, export, style  # noqa: E402
from figkit.provenance import Provenance  # noqa: E402

TOML = HERE / "figkit.toml"


def scores(seed, n=400, sep=1.0, prev=0.4):
    """Synthetic binary labels + probabilities (logistic of a shifted normal score)."""
    rng = np.random.default_rng(seed)
    y = (rng.uniform(size=n) < prev).astype(int)
    z = rng.normal(size=n) + sep * (2 * y - 1)
    return y, 1 / (1 + np.exp(-z))


def build(mod, cfg=None):
    cfg = cfg or config.load(TOML)
    cfg.theme = getattr(mod, "THEME", "default")  # a recipe may declare THEME = "soft"
    style.apply(cfg)
    prov = Provenance(mod.NAME, cfg)
    fig, ax = plt.subplots(figsize=mod.SIZE, layout="constrained")
    mod.draw(ax, cfg, prov)
    return fig, prov


def run(mod, cfg=None):
    cfg = cfg or config.load(TOML)
    fig, prov = build(mod, cfg)
    res = export.save(fig, mod.NAME, prov, kind="gallery", size=mod.SIZE, cfg=cfg, panels="none")
    plt.close(fig)
    return res
