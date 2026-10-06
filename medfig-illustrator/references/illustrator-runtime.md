# Illustrator runtime reference

## Supported workflow

The default local runtime uses Illustrator as a native path author from the immutable geometry cache:

1. Parse the validated Master SVG locally exactly once.
2. Cache anchors, Bézier handles, closure, fill, stroke, text, paint order, and compound-path membership.
3. Connect through the unversioned `Illustrator.Application` ProgID only after confirming Illustrator is already open.
4. Create final native paths and live text in the visible target, one atomic object per redraw.

No complete artwork is ever inserted, hidden, moved off-canvas, or later swapped in the target document.

## Stacking rule

SVG paint order and Illustrator collection indexes use opposite traversal directions after import:

- `pageItems[0]`: topmost.
- `pageItems[pageItems.length - 1]`: bottommost.

Traverse from the final index to `0`. Each newly created destination object is brought to the front, so later source layers remain above earlier layers.

Never reorder by semantic labels such as background, outline, fill, detail, or text.

## Compatibility

- Required for cached local playback: Illustrator 2020 / version 24.x or newer.
- The unversioned COM ProgID attaches to the currently registered, already-open Illustrator installation; do not hard-code a yearly ProgID.
- Illustrator 2020 does not reliably expose imported SVG child path points, so do not use the older import-and-snapshot direct runtime on version 24.x. Cached local playback does not depend on that import behavior.
- Illustrator 2026 remains the preferred tested version for the optional import-based workflow.

## Supported SVG content

Designed for editable scientific figures and flat vector illustrations containing:

- Regular paths.
- Compound paths.
- Solid RGB, CMYK, Gray, or Lab fills and strokes.
- Bézier handles, open paths, closed paths, opacity, stroke caps, and stroke joins.

The runtime intentionally refuses:

- Clipped groups.
- Gradient, pattern, or spot colors.
- Raster images (except opt-in raster panels run with `-AllowRaster`), meshes, live effects, symbols, or unsupported imported item types.

Pre-expand or simplify these features in a source copy before rerunning. Never flatten the target artwork to hide a compatibility problem.

## Placement

Available placements: `center`, `bottom-right`, `top-right`, `bottom-left`, and `top-left`.

Coordinates are mapped from the imported Illustrator geometry bounds to the active artboard. Stroke widths scale with artwork. Use the same `MaxWidthFraction` and `MaxHeightFraction` for predictable proportional fitting.

Artboard growth: placed scale is `min(W*MaxWidthFraction/viewW, H*MaxHeightFraction/viewH)`, so the smallest placed font is `minSourceFont * scale`. When that would drop below 8 pt, `artboard_fit.py` returns the smallest enlargement that restores `8 pt * 1.05`, and the runtime's `resizeArtboard` operation applies it. The operation keeps the top-left corner, refuses to shrink, and refuses to run once the job root group exists. Example: a 1536×1024 figure with 12 px minimum text on A4 portrait (595×842 pt) places at about 3.3 pt, so it is enlarged to about 1494×1167 pt.

## Text export

SVG export uses `fontSubsetting = None`, so `<text>` references the installed font (`font-family:'Arial-BoldMT'`) instead of embedding `<font>/<glyph>` outlines. `svg_live_text.py fix` appends `'Arial', sans-serif` plus `font-weight`/`font-style` so browsers that don't resolve PostScript names still use the same face. `svg_live_text.py audit` and `verify_delivery_bundle.ps1` both block on glyph outlines.

## Failure behavior

The runtime creates one named destination group. On failure it removes that group, closes the non-UI source document, restores Illustrator's interaction level, and returns an `ERROR|...` result. Existing target artwork remains untouched.
