"""Reusable panel functions. Every function draws into an existing ``ax`` and returns it; key computed
arrays are attached as ``ax._anchor_<name>`` for tests and provenance (C7).

S3: data artists are drawn in saturated colours by default (``style.DATA_CYCLE`` or a palette from
``figkit.toml``); reference lines, diagonals, bands and not-estimable hatching are marked with
``style.aux`` so ``qa.colour_audit`` exempts them.
"""
from . import confusion, intervals, dist, curves, heat, imaging, scatter, bars  # noqa: F401

__all__ = ["confusion", "intervals", "dist", "curves", "heat", "imaging", "scatter", "bars"]
