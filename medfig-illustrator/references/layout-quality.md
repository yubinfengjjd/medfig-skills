# medfig-illustrator Layout Quality Contract

Use this contract for every reconstruction with live text. It records the reusable lessons from production framework figures without encoding exceptions for particular labels.

## Core invariant

A deliverable passes only when meaning, spacing, and export identity all pass independently:

1. typography communicates the intended hierarchy;
2. every text frame has collision-free native bounds and, when boxed, remains inside its true owner with required padding;
3. AI, SVG, and PNG describe the same single artboard after native postflight.

Do not use a typography change to claim a spacing repair. Do not use a visually similar export to claim canonical identity.

## Layer 1: semantic typography

Assign `data-typography-role` during scene analysis.

| Role | Default weight | Use |
|---|---:|---|
| `panel-label` | 700 | Panel letters or equivalent navigation marks |
| `section-heading` | 600 | Headings spanning a stage or panel |
| `module-title` | 600 | Primary line inside a module |
| `body` | 400 | Supporting line inside a module |
| `annotation` | 400 | Small explanatory labels |
| `math` | 400 | Mathematical or italic embedding labels |

Explicit source style wins. When the source omits hierarchy inside one container, infer the first or larger eligible line as `module-title`; later or smaller lines are `body`. Never infer Black, Heavy, Narrow, or Condensed solely to make text fit. Font face resolution must respect requested weight and style.

After any family, face, weight, style, size, content, or line-break change, remeasure the native bounds. A weight change is recorded as `set_font_weight`, not as reflow or collision repair.

## Layer 2: spatial layout

### Ownership

- Every boxed text has a stable `data-container-id`.
- Related geometry uses `data-layout-group`.
- Intentional composites use explicit `data-overlap-allow` IDs.
- Unboxed labels in dense regions receive an invisible editable safe-zone container.
- In stacked cards, choose the nearest visible/front card in the same group. Reassign ownership before centering, padding checks, or expansion.

### Repair decision order

Use the first operation that preserves the most reference fidelity:

1. Preserve original content, family, style, weight, and size.
2. For a compact label in a shallow box, try 0.5 pt reductions while keeping one line.
3. For genuinely long prose-like labels, try balanced semantic wrapping at spaces, hyphens, or slashes.
4. Reduce in 0.5 pt steps, never below `max(75% of original, 8 pt)`.
5. Expand the owning container symmetrically to restore padding.
6. Move a label or local group only inside an explicit safe zone or corridor; update attached connector endpoints.
7. Block when no permitted state is collision-free.

The minimum padding on each side is half the final font size. Every repair must preserve the complete normalized text content.

### Collision policy

Text may overlap only its owner or an explicitly allowed composite. It must not overlap:

- other text;
- unrelated frames;
- icons or nodes;
- connectors, arrow shafts, or arrowheads;
- placed or raster artwork.

Use segment geometry for connectors where an axis-aligned line bounding box would create a false positive. Use transformed axis-aligned bounds for rotated text. Illustrator `visibleBounds` are authoritative after playback.

## Layer 3: canonical delivery

After native postflight, duplicate only the completed root group and active artboard into one temporary document. Export public AI, SVG, and PNG from that document. The Illustrator-native SVG is public; the authored Master SVG remains internal.

Delivery requires:

- exactly one AI artboard;
- equal AI/SVG canvas dimensions and matching PNG dimensions at 100% export;
- equal AI/SVG live-text counts and normalized contents;
- no raster or placed objects in AI and no `<image>` node in SVG, except exactly the declared opt-in raster panels, embedded in both;
- a nonblank PNG;
- acceptable Illustrator raster-render difference between public SVG and PNG;
- no U+FFFD replacement character.

## Stable diagnostics

Preflight report schema 2.0 retains `type` and `id` for compatibility. Every repair also contains:

- `action` and `element_id`;
- `before` and `after` values;
- a concise `reason`;
- action-specific compatibility fields.

The summary groups repairs by action and unresolved issues by code. Native reports retain raw `issues` and add parsed `diagnostics` with `code`, `element_id`, `other_id`, and `raw`.

Stable issue codes include:

- `MISSING_TEXT_CONTAINER`
- `TEXT_CONTAINER_OVERFLOW`
- `TEXT_TEXT_OVERLAP`
- `TEXT_GRAPHIC_OVERLAP`
- `TEXT_CONTENT_MISMATCH`
- `TEXT_COUNT_MISMATCH`
- `AI_SVG_CANVAS_MISMATCH`
- `PNG_SVG_CANVAS_MISMATCH`
- `SVG_RENDER_DIFFERENCE`

Do not suppress, rename, or downgrade an issue to obtain a pass.

## Forbidden shortcuts

Never truncate labels, remove text, turn ordinary text into outlines, cover a defect with a white object, lower thresholds, skip native postflight, publish the preflight SVG, or branch production behavior on exact label content.

## Regression commands

Run non-live checks:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\run_quality_gates.ps1
```

When Illustrator and a target document are already open, run all checks:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts\run_quality_gates.ps1 -IncludeIllustrator
```

The unified report must be `PASS`. A skipped Illustrator stage is acceptable only during skill development, never as evidence that a user deliverable passed native or canonical verification.

## Final review checklist

- Compare scene-manifest text to public SVG text, not just object counts.
- Inspect every structured repair; unexplained or repeated large repairs indicate a scene-layout problem.
- Confirm all issue summaries are empty.
- Visually inspect the final Illustrator artboard at normal and high zoom.
- Confirm the original user document and existing artwork remain present and unobstructed.
