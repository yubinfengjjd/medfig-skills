"""
scipilot-medimg-figure-skill :: image_io.py
===========================================
Read exported medical images, masks and heatmaps without silently altering them.

- Images: PNG / JPG / TIF, 8-bit or 16-bit grayscale, RGB (alpha dropped with a note).
- Masks: integer label maps (binary or multi-class); shape must equal the image.
- Heatmaps: .npy / .npz (named key) / grayscale PNG, any resolution.
- Intensity: whole-image *linear* window only; one window per group, computed once
  over every image of the group, recorded for disclosure (journal image-integrity rules).

Nothing here guesses: a missing field, unknown mode or shape mismatch raises
``SpecError`` / ``ShapeMismatchError`` with the offending path.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

import numpy as np

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
LOSSY_SUFFIXES = {".jpg", ".jpeg"}


class SpecError(ValueError):
    """Invalid or incomplete layout specification (message names the field)."""


class ShapeMismatchError(ValueError):
    """Image and overlay do not share the same pixel grid."""


def sha256_file(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _require_file(path: str, where: str) -> str:
    if not isinstance(path, str) or not path:
        raise SpecError(f"{where}: missing file path")
    if not os.path.isfile(path):
        raise SpecError(f"{where}: file not found: {path}")
    return path


@dataclass
class ImageRecord:
    path: str
    array: np.ndarray            # native values, float64, (H, W) or (H, W, 3)
    mode: str
    bit_depth: int
    sha256: str
    notes: list[str] = field(default_factory=list)

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.array.shape[0]), int(self.array.shape[1])

    @property
    def is_rgb(self) -> bool:
        return self.array.ndim == 3


def load_image(path: str, where: str = "image") -> ImageRecord:
    from PIL import Image

    _require_file(path, where)
    notes: list[str] = []
    suffix = os.path.splitext(path)[1].lower()
    if suffix not in IMAGE_SUFFIXES:
        raise SpecError(f"{where}: unsupported image type {suffix} ({path}); "
                        f"use one of {sorted(IMAGE_SUFFIXES)}")
    if suffix in LOSSY_SUFFIXES:
        notes.append("source is JPEG (lossy); compression artefacts are part of the source")
    with Image.open(path) as im:
        mode = im.mode
        if mode in ("I;16", "I;16B", "I;16L", "I"):
            arr = np.asarray(im, dtype=np.float64)
            bit_depth = 16 if mode.startswith("I;16") or arr.max() <= 65535 else 32
        elif mode == "L":
            arr, bit_depth = np.asarray(im, dtype=np.float64), 8
        elif mode == "F":
            arr, bit_depth = np.asarray(im, dtype=np.float64), 32
        elif mode in ("RGB", "RGBA", "P", "LA", "CMYK"):
            if mode in ("RGBA", "LA"):
                notes.append(f"alpha channel of {mode} source dropped")
            conv = im.convert("L" if mode == "LA" else "RGB")
            arr, bit_depth = np.asarray(conv, dtype=np.float64), 8
            if mode == "P":
                notes.append("palette image converted to RGB")
        else:
            raise SpecError(f"{where}: unsupported PIL mode {mode} ({path})")
    if arr.ndim == 3 and np.allclose(arr[..., 0], arr[..., 1]) and np.allclose(arr[..., 1], arr[..., 2]):
        arr = arr[..., 0]
        notes.append("RGB source with identical channels treated as grayscale")
    return ImageRecord(path=path, array=arr, mode=mode, bit_depth=bit_depth,
                       sha256=sha256_file(path), notes=notes)


def load_mask(path: str, expected_shape: tuple[int, int], where: str) -> tuple[np.ndarray, str]:
    """Integer label map; raises ShapeMismatchError when the grid differs from the image."""
    from PIL import Image

    _require_file(path, where)
    suffix = os.path.splitext(path)[1].lower()
    if suffix == ".npy":
        arr = np.load(path)
    elif suffix in (".png", ".tif", ".tiff"):
        with Image.open(path) as im:
            if im.mode not in ("L", "1", "P", "I", "I;16"):
                raise SpecError(f"{where}: mask must be single-channel (got {im.mode}): {path}")
            arr = np.asarray(im)
    else:
        raise SpecError(f"{where}: mask must be .png/.tif/.npy (lossless), got {suffix}: {path}")
    if arr.ndim != 2:
        raise SpecError(f"{where}: mask must be 2-D, got shape {arr.shape}: {path}")
    if tuple(arr.shape) != tuple(expected_shape):
        raise ShapeMismatchError(
            f"{where}: mask {path} is {arr.shape[1]}x{arr.shape[0]} (W x H) but the image is "
            f"{expected_shape[1]}x{expected_shape[0]}. Masks are never resized automatically; "
            "export the mask on the image's pixel grid.")
    return arr.astype(np.int64), sha256_file(path)


def load_heatmap(path: str, where: str, key: str | None = None) -> tuple[np.ndarray, str]:
    from PIL import Image

    _require_file(path, where)
    suffix = os.path.splitext(path)[1].lower()
    if suffix == ".npz":
        if not key:
            raise SpecError(f"{where}: .npz heatmap needs 'key' (available: "
                            f"{list(np.load(path).files)})")
        z = np.load(path)
        if key not in z.files:
            raise SpecError(f"{where}: key '{key}' not in {path} (available: {z.files})")
        arr = z[key]
    elif suffix == ".npy":
        arr = np.load(path)
    elif suffix in (".png", ".tif", ".tiff"):
        with Image.open(path) as im:
            if im.mode not in ("L", "I", "I;16", "F"):
                raise SpecError(f"{where}: heatmap image must be single-channel (got {im.mode}); "
                                "a colour-rendered heatmap cannot be re-mapped honestly")
            arr = np.asarray(im)
    else:
        raise SpecError(f"{where}: heatmap must be .npy/.npz/.png/.tif, got {suffix}")
    arr = np.asarray(arr, dtype=np.float64)
    if arr.ndim != 2:
        raise SpecError(f"{where}: heatmap must be 2-D, got {arr.shape}")
    if not np.isfinite(arr).all():
        raise SpecError(f"{where}: heatmap contains NaN/Inf")
    return arr, sha256_file(path)


def resize_heatmap(arr: np.ndarray, shape: tuple[int, int], method: str) -> np.ndarray:
    """Resample a (low-res) map onto the full native image grid."""
    from PIL import Image

    if method not in ("bilinear", "nearest"):
        raise SpecError(f"heatmap upsample must be 'bilinear' or 'nearest', got {method!r}")
    if arr.shape == tuple(shape):
        return arr.copy()
    resample = Image.BILINEAR if method == "bilinear" else Image.NEAREST
    im = Image.fromarray(arr.astype(np.float32), mode="F")
    return np.asarray(im.resize((shape[1], shape[0]), resample=resample), dtype=np.float64)


def compute_window(images: list[np.ndarray], spec: dict, where: str) -> dict:
    """One linear window for a group. Returns disclosure record."""
    mode = spec.get("mode", "none")
    if mode == "none":
        # identity for the source bit depth: display native values unchanged
        return {"mode": "none"}
    if mode == "percentile":
        lo_p, hi_p = spec.get("lo"), spec.get("hi")
        if lo_p is None or hi_p is None or not (0 <= lo_p < hi_p <= 100):
            raise SpecError(f"{where}: percentile window needs 0 <= lo < hi <= 100")
        pooled = np.concatenate([a.ravel() for a in images])
        lo, hi = np.percentile(pooled, [lo_p, hi_p])
    elif mode == "absolute":
        lo, hi = spec.get("lo"), spec.get("hi")
        if lo is None or hi is None or not lo < hi:
            raise SpecError(f"{where}: absolute window needs lo < hi")
    else:
        raise SpecError(f"{where}: intensity mode must be none|percentile|absolute, got {mode!r}")
    if not hi > lo:
        raise SpecError(f"{where}: degenerate window lo={lo} hi={hi} (flat images?)")
    rec = {"mode": mode, "lo_value": float(lo), "hi_value": float(hi)}
    if mode == "percentile":
        rec.update(lo_percentile=float(spec["lo"]), hi_percentile=float(spec["hi"]))
    return rec


def apply_window(arr: np.ndarray, window: dict, bit_depth: int) -> tuple[np.ndarray, float]:
    """Linear map to [0, 1]; returns (display array, fraction of pixels clipped)."""
    if window["mode"] == "none":
        full = float(2 ** bit_depth - 1) if bit_depth in (8, 16) else float(arr.max() or 1.0)
        return np.clip(arr / full, 0, 1), 0.0
    lo, hi = window["lo_value"], window["hi_value"]
    clipped = float(((arr < lo) | (arr > hi)).mean())
    return np.clip((arr - lo) / (hi - lo), 0, 1), clipped
