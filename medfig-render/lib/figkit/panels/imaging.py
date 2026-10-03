"""Medical image panels: B-scan with boundary traces / band masks, and concept maps on a shared scale.

Red lines (B1-B3): images are always drawn with ``aspect="equal"`` (never stretched; ``set_anchor("C")``
letterboxes, size the grid cell with ``layout.image_width_ratios``); the grey raw image is flagged
``_figkit_raw_image = True`` so the S3 colour audit exempts it; concept maps use the caller's SHARED
``vmin`` / ``vmax`` (never per-image normalisation) and values <= 0 are transparent. Masks are never
resized (they must match the image); low-resolution model outputs go through ``prob_overlay`` /
``concept_map``, which record the resampling in ``ax._anchor_resampled`` for the caption.
"""
import numpy as np
from matplotlib import colormaps
from matplotlib.colors import Normalize
from scipy.ndimage import zoom

# saturated Okabe-Ito colours that read on a grey B-scan (no white / black traces: S3)
BOUNDARY_COLORS = ["#D55E00", "#F0E442", "#56B4E9", "#009E73", "#CC79A7", "#E69F00"]
BAND_ALPHA = 0.28
MAP_ALPHA = 0.55
MAP_THRESHOLD = 0.15


def upsample(a, shape, order=1):
    """Resize 2-D ``a`` to exactly ``shape`` (order 1 = bilinear, 0 = nearest). For probability /
    activation overlays only -- never for masks."""
    a = np.asarray(a, float)
    if a.ndim != 2:
        raise ValueError(f"upsample needs a 2-D array, got shape {a.shape}")
    out = zoom(a, (shape[0] / a.shape[0], shape[1] / a.shape[1]), order=order)
    if out.shape != tuple(shape):  # guard rounding in zoom's output size
        out = np.pad(out, [(0, max(0, s - o)) for s, o in zip(shape, out.shape)], mode="edge")
        out = out[:shape[0], :shape[1]]
    return out


def raw_image(ax, raw, cmap="gray"):
    """Draw the raw image at equal aspect, centred, without ticks or spines; flag it as raw (S3)."""
    raw = np.asarray(raw)
    im = ax.imshow(raw, cmap=cmap, aspect="equal", interpolation="nearest")
    im._figkit_raw_image = True
    ax.set_aspect("equal")
    ax.set_anchor("C")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    return im


def _limits(ax, H, W):
    ax.set_xlim(-0.5, W - 0.5)
    ax.set_ylim(H - 0.5, -0.5)


def bscan_with_boundaries(ax, raw, boundaries, band_masks=None, colors=None, band_cmap="viridis"):
    """Grey B-scan with boundary traces and optional band-mask overlays.

    ``boundaries``: (K, M) rows normalised to [0, 1] of image height, sampled at
    ``linspace(0, W - 1, M)``. ``band_masks``: (B, H, W) masks (bool or [0, 1]) at the image's own
    shape, overlaid in ``band_cmap`` colours at alpha 0.28 x value. Masks are never resized: any other
    shape raises ValueError (draw low-resolution model outputs with ``prob_overlay``). Stores
    ``ax._anchor_boundaries_px`` (K, M) and ``ax._anchor_bands`` (B, H, W)."""
    raw = np.asarray(raw)
    H, W = raw.shape[:2]
    raw_image(ax, raw)
    if band_masks is not None:
        bm = np.asarray(band_masks, float)
        if bm.ndim != 3 or bm.shape[1:] != (H, W):
            raise ValueError(
                f"band_masks shape {bm.shape} does not match the image {(H, W)}: masks are never resized. "
                "Pass masks at the image's native shape, or draw low-resolution model outputs with "
                "imaging.prob_overlay (which labels the resampling for the caption).")
        if not np.isfinite(bm).all() or bm.min() < 0 or bm.max() > 1:
            raise ValueError("band_masks must be finite values in [0, 1]")
        cols = colormaps[band_cmap](np.linspace(0, 1, len(bm)))
        for k, m in enumerate(bm):
            rgba = np.zeros((H, W, 4))
            rgba[..., :3] = cols[k][:3]
            rgba[..., 3] = BAND_ALPHA * m
            ax.imshow(rgba, aspect="equal", interpolation="nearest")
        ax._anchor_bands = bm
    b = np.asarray(boundaries, float)
    if b.ndim != 2:
        raise ValueError(f"boundaries must be (K, M), got shape {b.shape}")
    cols = colors or BOUNDARY_COLORS
    xs = np.linspace(0, W - 1, b.shape[1])
    for k, row in enumerate(b):
        ax.plot(xs, row * H, color=cols[k % len(cols)], linewidth=0.6)
    _limits(ax, H, W)
    ax.set_aspect("equal")
    ax._anchor_boundaries_px = b * H
    return ax


def concept_map(ax, raw, spatial, vmin, vmax, cmap="magma", threshold=MAP_THRESHOLD, alpha=MAP_ALPHA):
    """Grey image with a bilinearly upsampled map on the SHARED ``[vmin, vmax]`` scale.

    ``vmin`` / ``vmax`` are required: compute them once over every case shown in the panel so all maps
    share one scale (the colourbar then shows raw units). Opaque (``alpha``) where the normalised value
    is >= ``threshold``; transparent below, and always transparent where the value is <= 0 (positive
    activation only; with a negative shared vmin, negative maps are not painted as evidence).
    Stores ``ax._anchor_mappable``, ``_anchor_upsampled``, ``_anchor_alpha`` and
    ``_anchor_threshold`` (normalised threshold, for provenance)."""
    if vmin is None or vmax is None or not np.isfinite([vmin, vmax]).all() or vmax <= vmin:
        raise ValueError(f"concept_map needs a finite shared scale with vmax > vmin, got {vmin!r}, {vmax!r}")
    raw = np.asarray(raw)
    H, W = raw.shape[:2]
    raw_image(ax, raw)
    src = np.asarray(spatial).shape
    up = upsample(spatial, (H, W))
    norm = Normalize(vmin, vmax, clip=True)
    n = np.ma.filled(norm(up), 0.0)
    a = np.where((n >= threshold) & (up > 0), alpha, 0.0)
    im = ax.imshow(up, cmap=cmap, norm=norm, alpha=a, aspect="equal", interpolation="nearest")
    _limits(ax, H, W)
    ax.set_aspect("equal")
    ax._anchor_mappable = im
    ax._anchor_upsampled = up
    ax._anchor_alpha = a
    ax._anchor_threshold = float(threshold)
    ax._anchor_resampled = (tuple(src), (H, W), "bilinear" if tuple(src) != (H, W) else "none")
    return ax


_RESAMPLE = {"bilinear": 1, "nearest": 0}


def prob_overlay(ax, raw, prob, vmin, vmax, cmap="viridis", resample="bilinear", alpha=MAP_ALPHA):
    """Grey image with a model probability map (possibly low resolution) on the shared ``[vmin, vmax]``.

    ``prob`` is resampled to the image shape with ``resample`` ("bilinear" or "nearest"); the result is
    a probability map, not a mask -- the mappable is labelled "probability map" and
    ``ax._anchor_resampled = (src_shape, dst_shape, method)`` (method "none" when shapes match) must be
    stated in the caption. Stores ``_anchor_mappable`` and ``_anchor_upsampled``."""
    if resample not in _RESAMPLE:
        raise ValueError(f"resample must be one of {sorted(_RESAMPLE)}, got {resample!r}")
    if vmin is None or vmax is None or not np.isfinite([vmin, vmax]).all() or vmax <= vmin:
        raise ValueError(f"prob_overlay needs a finite shared scale with vmax > vmin, got {vmin!r}, {vmax!r}")
    raw = np.asarray(raw)
    H, W = raw.shape[:2]
    p = np.asarray(prob, float)
    if p.ndim != 2 or not np.isfinite(p).all():
        raise ValueError(f"prob must be a finite 2-D array, got shape {p.shape}")
    raw_image(ax, raw)
    same = p.shape == (H, W)
    up = p if same else upsample(p, (H, W), order=_RESAMPLE[resample])
    im = ax.imshow(up, cmap=cmap, norm=Normalize(vmin, vmax, clip=True), alpha=alpha, aspect="equal",
                   interpolation="nearest", label="probability map")
    _limits(ax, H, W)
    ax.set_aspect("equal")
    ax._anchor_mappable = im
    ax._anchor_upsampled = up
    ax._anchor_resampled = (p.shape, (H, W), "none" if same else resample)
    return ax
