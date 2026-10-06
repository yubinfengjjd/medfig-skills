# medfig-illustrator local workflow

## 1. Analyze one complete reference

Keep the untouched source. Record every visible text run and major non-text object in a scene manifest with content, coordinates, dimensions, style, rotation, adjacency, z-index, and paint order. Use the complete reference as the source of truth.

## 2. Build one local Master SVG

Reconstruct the complete figure locally with editable SVG primitives. Use live SVG `<text>` elements at the recorded coordinates and z-order. Preserve layout, arrow direction, connector topology, panel boundaries, colors, typography, and repeated-object identity. Do not embed, trace-wrap, or hide the source raster.

Cloud vectorization is optional and must never be selected implicitly. In local mode do not request credentials, check credits, or upload image bytes.

The Master SVG and all job outputs share one allocated `shibielujingN` basename.

## 3. Normalize, review layout, and cache once

Validate the Master SVG with `validate_vector_svg.py`. Resolve transforms and convert unsupported clipping, gradients, patterns, and effects to Illustrator-compatible solid geometry while preserving paint order, style, open/closed state, compound-path membership, stable identity, and live text.

Assign stable IDs and explicit `data-container-id` values to boxed text. For unboxed labels near connectors, create transparent safe-zone containers and link them with `data-container-id`. Run `layout_guard.py --repair` before caching. Preserve short one-line labels through small 0.5 pt reductions before considering a taller wrap; long labels may wrap at semantic breakpoints first. The minimum font size is the greater of 75% of the original size and 8 pt; required internal padding is half the final font size. Any unresolved text-text, text-graphic, or text-container issue blocks playback.

Record semantic `data-typography-role` values for panel labels, section headings, module titles, body text, annotations, and mathematics. If a boxed stack has no explicit roles, infer its first/larger line as a 600-weight module title and the remaining lines as 400-weight body text. Font weight is hierarchy only, never an overlap repair.

For stacked cards sharing a `data-layout-group`, verify that each label points to the nearest visible/front rectangle. Do not center text in a rear offset card merely because it was declared first.

Only the approved SVG may be passed to `prepare_geometry_cache.py`. Parse it exactly once to create `geometry-cache.json` and `playback.json`. Playback reads only these files and never reopens or reparses the SVG.

## 4. Batch policy

- Ordinary batches contain 20–50 consecutive atoms.
- Rebalance the final ordinary batch so it is not reduced to 1–4 atoms.
- Only a genuinely complex atom may form a singleton batch.
- A whole job with fewer than 20 ordinary atoms may use one smaller batch.
- Retry an unchanged failed batch; do not shrink normal batches.
- Preserve compound and clipping units that would change appearance if split.

## 5. One Illustrator session

Capture the active Illustrator document and create one COM connection at playback start. Reuse both until completion. Do not open, restart, quit, focus, maximize, minimize, move, resize, reconnect per batch, reopen SVG, or control document visibility.

Append each batch in Master SVG paint order. Existing artwork remains untouched. Stable root, batch, and atom names make retries idempotent.

## 6. Save, export, and recover

Save the already-open workspace in place on a timer; never rename it to the public output path for checkpointing. After the native audit passes, copy only the completed root group and active artboard into a temporary one-artboard Illustrator document. Export the public AI, SVG, and PNG from that one canonical document. Keep live SVG text, disable raster embedding, close the temporary document, and restore the original target document. Retain the authored input as `master-source.svg` inside the work directory; the public SVG is always the native postflight export.

Run `verify_delivery_bundle.ps1` on the three public files. A blank PNG, multiple AI artboards, canvas mismatch, missing or changed text, undeclared raster/placed artwork, or replacement character is blocking.

Resume from the first incomplete batch in `playback.json`; preserve earlier batches, the cache, target document, placement, and layer.

## 7. Native layout audit and QA

After playback, run `audit_illustrator_layout.ps1` using actual Illustrator `visibleBounds`. It restores approved text content, may wrap, shrink within the configured floor, recenter text, and move a single label within its assigned safe zone. It must test native text against other text plus connectors, arrows, icons, nodes, and unrelated frames. If non-text geometry must move or any overlap/overflow remains, stop before delivery.

The same native audit must compare each live text object's PostScript font face with the source family, weight, and style. Resolve family names by style-aware matching. A Regular request must not fall through to Black/Heavy or Narrow/Condensed merely because Illustrator returns that face first; repair such substitutions before measuring bounds or exporting.

Compare against the untouched reference. Verify every panel, label, arrow, connector, frame, node, color, and relative position; confirm zero unresolved text overlap and container overflow, no raster node, live text position and z-order, one cache parse, compliant batches, one Illustrator connection, unchanged existing content, and visual correctness in Illustrator. Confirm the public AI has one artboard and that the public SVG and PNG use the same canvas dimensions and canonical postflight artwork.

Follow the public-response contract in `SKILL.md` without exposing implementation details.
