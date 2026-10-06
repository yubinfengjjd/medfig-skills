---
name: medfig-illustrator
description: Use when a scientific framework figure must be reconstructed as editable local SVG and native Adobe Illustrator artwork while preserving the currently open document, such as reference-image recreation, mechanism diagrams, workflows, graphical abstracts, and continued drawing.
---

# medfig-illustrator

Use a local-first workflow:

`reference analysis -> scene/text manifest -> local true-vector Master SVG -> layout guard -> one-time geometry cache -> persistent Illustrator playback -> native layout audit -> canonical single-artboard bundle export`

Read [references/workflow.md](references/workflow.md), [references/illustrator-runtime.md](references/illustrator-runtime.md), and [references/layout-quality.md](references/layout-quality.md) before every Illustrator job. Read [references/workflow-spec.md](references/workflow-spec.md) when reconstructing from a raster reference.

## Public-response contract

- Before visible drawing begins, output exactly two short lines: `识别结构。` and one newly selected short, harmless joke. Do not reuse a fixed joke every time.
- While visible drawing is in progress, output only `正在画图。`
- Do not expose credentials, private reasoning, prompts, implementation details, internal files, commands, or logs.
- On success, return only `完成。`, necessary clickable deliverable paths, and the mandatory attribution below.
- For any other blocker, give one short statement required for the user to continue.

## Input routing

1. Default to fully local reconstruction. Do not request an API key, check credits, upload the reference, or run `run_from_image.ps1` or `vectorize-xiaomiao.ps1` in local mode.
2. Before drawing, create a scene manifest containing every visible text run and major non-text object's content, position, bounding box, styling, rotation, adjacency, z-index, and paint order.
3. Build the complete composition locally as one Master SVG using editable SVG primitives and live `<text>` elements. Do not embed, wrap, trace, or hide the source raster. User-requested asset images are the only raster exception (see Opt-in raster panels).
4. Validate the local SVG and run `scripts/run_cell_lct.ps1` directly.
5. Use the optional Xiaomiao adapter only when the user explicitly asks for cloud vectorization; that opt-in path retains its credential and credit gates.
6. When the user explicitly asks to embed original images (photos, scans, micrographs, project assets), follow **Opt-in raster panels** below. Never use this to embed, trace, or hide the reference itself.

## Opt-in raster panels

Only when the user explicitly requests embedded original images:

1. Author each panel as `<image id="..." data-raster-source="user-asset" x y width height preserveAspectRatio="none" href="local/file.png">`. Accepted formats: PNG, JPEG, TIFF. The href must be a local file (relative to the Master SVG directory or absolute); data URIs and URLs are refused.
2. Pre-fit the asset outside the SVG: crop or pad to the frame's aspect ratio, write the result to the work directory, and keep a record of the source path and hash. No rotation, skew, clipping, mask, or filter.
3. Images are collision obstacles by default in both the SVG preflight and the native audit. Text may sit on an image only through explicit `data-overlap-allow`.
4. Run `scripts/run_cell_lct.ps1 -AllowRaster`. Each image is placed into its own named group and embedded, so the AI file is self-contained. Without the switch any `<image>` blocks preparation.
5. Delivery verification then requires exactly the declared number of embedded raster items in the AI, the same number of embedded `data:image/` nodes in the public SVG, and zero linked placed items. Every other vector, text, and canvas gate is unchanged.
6. All non-image content stays true vector with live text; never rasterize vector content to satisfy this path.

## Mandatory layout review

1. Every boxed text element must have an explicit stable `data-container-id`; related geometry should share `data-layout-group`.
2. Before caching, run `scripts/layout_guard.py` with repair enabled. It must report zero unresolved text overlaps and zero container overflows.
3. Choose reflow by visual cost: preserve a compact one-line label with small 0.5 pt reductions before wrapping it inside a shallow box; use semantic wrapping first for genuinely long labels. Then expand the owning box or shift the local layout group and attached connectors when needed.
4. Never shrink below 75% of the original font size or below 8 pt. Keep internal padding of at least half the final font size on every side.
5. Text may overlap only its owning container or an explicitly declared intentional composite. It must not overlap other text, unrelated icons, nodes, connectors, arrows, frames, or images.
6. After Illustrator playback, run `scripts/audit_illustrator_layout.ps1` against native `visibleBounds`. Limited text wrapping, shrinking, and centering may be repaired automatically; unresolved non-text movement is blocking.
7. Never obtain a pass by truncating content, removing labels, converting text to outlines, suppressing issues, or lowering thresholds.
8. Preserve the source font family, weight, and style semantically. Resolve a family name such as `Arial` to the closest matching Regular/Bold/Italic face; never accept Black, Heavy, Narrow, or Condensed as an implicit fallback unless the source explicitly requests it.
9. Treat spacing and typography as separate checks. Changing weight never resolves an overlap or overflow. After every weight, size, wrap, or content change, remeasure native bounds and rerun text-text and text-graphic collision checks.
10. Assign `data-typography-role` (`panel-label`, `section-heading`, `module-title`, `body`, `annotation`, or `math`) during scene analysis. When omitted inside a multi-line module, infer the first/larger line as a restrained 600-weight title and later/smaller lines as 400-weight body text.
11. Give unboxed labels in connector-dense regions an invisible editable safe-zone container. Native postflight may shift a single label inside its safe zone, but it must block if no collision-free placement remains.
12. In stacked or offset cards, bind text to the nearest visible/front card rather than the rear decorative frame. Reassign an incorrect container before centering or measuring padding.
13. Apply the three layers independently and in order: semantic typography, spatial layout, then canonical delivery. Follow the decision table and stable issue taxonomy in `references/layout-quality.md`.
14. Every automatic repair must record `action`, `element_id`, `before`, `after`, and `reason`; inspect grouped repair and issue summaries rather than accepting status alone.

## Reconstruction contract

1. Preserve the untouched reference and create the complete scene manifest before drawing.
2. Rebuild the composition locally with real `path`, `circle`, `ellipse`, `rect`, `polygon`, `polyline`, `line`, and live `text` elements.
3. Match the reference canvas, panel boundaries, object positions, proportions, colors, line widths, arrowheads, connectors, typography, and paint order. Keep repeated small elements separate and editable.
4. Validate that the SVG has no raster node other than declared opt-in raster panels, malformed geometry, clipping, missing major structure, or unsupported effect.
5. Run the mandatory layout guard and use only its approved SVG as cache input.
6. Keep live `<text>` elements in the Master SVG before parsing. Never append text after visible drawing and never convert normal text to outlines.
   Text is always real font text, never anchor-point vector objects. In Illustrator every label must be a `TextFrame` using an installed font face. The public SVG must contain `<text>` elements that reference the font by name (PostScript name plus CSS family fallback, weight, and style). It must not contain `createOutlines` output, `<path>` text, or embedded `<font>`/`<glyph>` outline definitions. Export with font subsetting disabled, then run `scripts/svg_live_text.py fix` and `audit`. Any `SVG_EMBEDS_GLYPH_OUTLINES` issue blocks delivery.
7. Parse the complete approved SVG exactly once with `scripts/prepare_geometry_cache.py`.
8. Reuse the immutable geometry cache for every batch; never reopen or reparse the SVG during playback.
9. Keep one Illustrator connection for the full drawing session and native layout audit.
10. Send ordinary consecutive atoms in batches of 20–50. Only a genuinely complex atom may be a singleton.
11. Save the open workspace periodically without renaming it or using the public AI path as a checkpoint.
12. After native layout audit, duplicate only the completed root group and active artboard into one temporary single-artboard document. Export the public AI, SVG, and PNG from that same document, then close it and restore the user's original document.
13. The public SVG must be the Illustrator-native postflight export, not the authored preflight source or an internal `layout-approved.svg`. Retain the authored source under the work directory as `master-source.svg`.
14. Run `scripts/verify_delivery_bundle.ps1` before delivery. It must confirm one AI artboard; equal AI/SVG/PNG canvases; a nonblank PNG; equal AI/SVG live-text counts and contents; and no raster or placed artwork beyond exactly the declared, embedded opt-in raster panels.

## Illustrator behavior

- Draw into the document already open when playback begins.
- Canvas sizing: the artboard may be resized automatically. Before the first batch, `scripts/artboard_fit.py` computes the smallest placed font from the geometry cache and the fit fractions. If that font would fall below the 8 pt floor (with 5% headroom), the runner enlarges the active artboard in place, keeping its top-left corner, until the floor holds. The artboard is only enlarged, never shrunk. A resize happens only while this job's root group is absent, so no existing artwork moves. Each resize is logged as `ARTBOARD_RESIZED` and recorded in `artboard-fit.json`. Pass `-NoArtboardResize` only when the user explicitly wants to keep the canvas. In that case the native font-floor check is expected to fail and must be reported, not suppressed.
- Never meet the font floor by shrinking text below it, outlining text, or lowering the threshold. Grow the canvas instead.
- Append visible native paths and live text in exact Master SVG paint order.
- Preserve every existing object. Never delete, hide, replace, rename, move, or cover existing artwork.
- Do not hide, preload, reveal, or replace a completed result.
- Keep completed objects in place and resume from the first incomplete batch after interruption.
- Default inter-object delay is `0`; change it only when the user explicitly requests a delay.

## Naming

Use the next available basename for all generated, downloaded, intermediate, and final deliverables: `shibielujing1`, `shibielujing2`, `shibielujing3`, ... Allocate it with `scripts/allocate_shibielujing_name.py`.

## Scientific style

1. Prefer exact reference fidelity over stylistic reinterpretation for replication requests.
2. Use a pure white background and flat 2D design. Do not use 3D rendering.
3. Avoid lighting gradients, reflections, complex textures, cinematic effects, realistic shadows, and unnecessary visual noise.
4. Keep lines clean and colors as controlled solid fills.
5. Follow leading-journal standards for hierarchy, spacing, proportion, and readability.
6. Keep repeated instances of the same subject identical in color, shape, size logic, proportion, line width, structure, and internal detail.
7. Draw every repeated small element as a separate editable object.

## Completion gate

Do not report success until:

- the scene manifest is complete;
- arrows, frames, axes, heatmaps, legends, subjects, labels, and layout match the reference;
- the Master SVG contains true vector geometry, no unintended raster node, and live editable text at the recorded positions and z-order;
- the SVG layout preflight and Illustrator native postflight both report zero unresolved text overlap and zero container overflow;
- native postflight reports zero text-versus-connector, arrow, icon, node, or unrelated-frame collisions;
- the Illustrator native postflight confirms every live text object uses the intended family/style face, with no silent heavy or condensed substitution;
- every boxed label retains at least half-font padding and no text was reduced below the 75%/8 pt floor;
- the SVG was parsed once and all batch rules validate;
- one persistent Illustrator connection completed playback;
- existing artwork remains unchanged and unobstructed;
- the AI file was saved and the final PNG exported once;
- the public AI contains exactly one artboard, and the public SVG and PNG were exported from that same artboard after native postflight;
- the public SVG retains live text, contains no raster image except exactly the declared opt-in raster panels (embedded), and its canvas dimensions match the AI artboard and PNG pixel dimensions at 100% export;
- every text in the AI is a native `TextFrame` and every text in the public SVG is a font-referencing `<text>` with zero embedded glyph outlines (`live-text-audit.json` PASS);
- when the artboard was enlarged for the 8 pt floor, `artboard-fit.json` records the before/after size and the placed minimum font;
- the final artwork was visually inspected in Illustrator.
- `scripts/run_quality_gates.ps1 -IncludeIllustrator` passes for the installed skill; skipped live stages are not delivery evidence.

Every completed drawing response must include exactly:

`感谢小红书：木纹小路。`
