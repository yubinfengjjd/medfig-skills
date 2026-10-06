"""Keep exported SVG text as real font text, never embedded glyph outlines.

Illustrator's SVG export can embed ``<font>/<glyph>`` outline definitions. Those
glyphs are anchor-point vector shapes, not a font. medfig-illustrator exports with font
subsetting disabled so each ``<text>`` only references an installed font by
its PostScript name (for example ``'Arial-BoldMT'``). This module then:

* appends a CSS family fallback plus explicit weight/style, so browsers that do
  not resolve PostScript names still render the same Arial Regular/Bold face;
* audits that the file has live ``<text>``, no glyph outlines, and that every
  text node resolves a font-family.

Usage:
    svg_live_text.py fix   --svg out.svg
    svg_live_text.py audit --svg out.svg [--expected-text-count N]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# PostScript base names whose CSS family name is not a plain camel-case split.
FAMILY_ALIASES = {
    "ArialMT": "Arial",
    "Arial": "Arial",
    "TimesNewRomanPS": "Times New Roman",
    "TimesNewRomanPSMT": "Times New Roman",
    "CourierNewPS": "Courier New",
    "CourierNewPSMT": "Courier New",
    "MicrosoftYaHei": "Microsoft YaHei",
}
GENERIC = {"Times New Roman": "serif", "Courier New": "monospace"}

# Also consumes a weight/style pair written by a previous fix so reruns are idempotent.
QUOTED_FAMILY = re.compile(
    r"font-family:\s*'([^',;]+)'(?:\s*,[^;\"}]*)?"
    r"(?:;\s*font-weight:[^;\"}]*;\s*font-style:[^;\"}]*)?")
ATTR_FAMILY = re.compile(r'font-family="([^",]+)(?:,[^"]*)?"(?:\s+font-weight="[^"]*"\s+font-style="[^"]*")?')
GLYPH_NODES = re.compile(r"<(?:font|font-face|glyph|missing-glyph)[\s>/]")
TEXT_OPEN = re.compile(r"<text\b[^>]*>")
TEXT_BLOCK = re.compile(r"(<text\b[^>]*>)(.*?)</text>", re.S)


def has_family(tag: str, class_rules: dict) -> bool:
    if "font-family" in tag:
        return True
    classes = re.search(r'class="([^"]+)"', tag)
    names = classes.group(1).split() if classes else []
    return any("font-family" in class_rules.get(name, "") for name in names)


def describe(postscript: str) -> tuple[str, str, str]:
    """Map a PostScript name to (css family, weight, style)."""
    base, _, face = postscript.partition("-")
    family = FAMILY_ALIASES.get(base) or re.sub(r"(?<=[a-z])(?=[A-Z])", " ", re.sub(r"(PS)?MT$", "", base))
    face_lower = face.lower()
    if "black" in face_lower or "heavy" in face_lower:
        weight = "900"
    elif "semibold" in face_lower or "demi" in face_lower:
        weight = "600"
    elif "bold" in face_lower:
        weight = "700"
    else:
        weight = "400"
    style = "italic" if ("italic" in face_lower or "oblique" in face_lower) else "normal"
    return family, weight, style


def css_stack(postscript: str) -> str:
    family, weight, style = describe(postscript)
    generic = GENERIC.get(family, "sans-serif")
    return (f"font-family:'{postscript}', '{family}', {generic}; "
            f"font-weight:{weight}; font-style:{style}")


def fix_text(svg: str) -> tuple[str, int]:
    count = 0

    def quoted(match: re.Match) -> str:
        nonlocal count
        count += 1
        return css_stack(match.group(1).strip())

    svg = QUOTED_FAMILY.sub(quoted, svg)

    def attribute(match: re.Match) -> str:
        nonlocal count
        count += 1
        family, weight, style = describe(match.group(1).strip())
        generic = GENERIC.get(family, "sans-serif")
        return (f'font-family="{match.group(1)}, \'{family}\', {generic}" '
                f'font-weight="{weight}" font-style="{style}"')

    svg = ATTR_FAMILY.sub(attribute, svg)
    return svg, count


def audit_text(svg: str, expected_text_count: int | None = None) -> dict:
    issues: list[str] = []
    text_tags = TEXT_OPEN.findall(svg)
    glyph_nodes = len(GLYPH_NODES.findall(svg))
    if not text_tags:
        issues.append("SVG_HAS_NO_LIVE_TEXT")
    if glyph_nodes:
        issues.append(f"SVG_EMBEDS_GLYPH_OUTLINES:{glyph_nodes}")
    class_rules = dict(re.findall(r"\.(st\d+)\{([^}]*)\}", svg))
    unresolved = 0
    for match in TEXT_BLOCK.finditer(svg):
        tag, body = match.group(1), match.group(2)
        if "font-family" in tag:
            continue
        # Wrapped labels carry the font on each child <tspan>.
        spans = re.findall(r"<tspan\b[^>]*>", body)
        if spans and all(has_family(span, class_rules) for span in spans):
            continue
        if not has_family(tag, class_rules):
            unresolved += 1
    if unresolved:
        issues.append(f"SVG_TEXT_WITHOUT_FONT_FAMILY:{unresolved}")
    if expected_text_count is not None and len(text_tags) != expected_text_count:
        issues.append(f"SVG_TEXT_COUNT_MISMATCH:{len(text_tags)}:{expected_text_count}")
    return {"status": "PASS" if not issues else "FAIL", "text_count": len(text_tags),
            "glyph_nodes": glyph_nodes, "issues": issues}


def read(path: Path) -> str:
    # Illustrator declares iso-8859-1 and escapes non-ASCII as entities, so a
    # latin-1 round trip is lossless for every byte.
    return path.read_bytes().decode("latin-1")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["fix", "audit"])
    parser.add_argument("--svg", required=True)
    parser.add_argument("--expected-text-count", type=int)
    parser.add_argument("--report")
    args = parser.parse_args()
    path = Path(args.svg)
    content = read(path)
    if args.command == "fix":
        content, changed = fix_text(content)
        path.write_bytes(content.encode("latin-1"))
        print(f"LIVE_TEXT_FIX|families={changed}")
        return 0
    result = audit_text(content, args.expected_text_count)
    if args.report:
        Path(args.report).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"LIVE_TEXT_AUDIT|status={result['status']}|texts={result['text_count']}|glyphs={result['glyph_nodes']}"
          + ("|" + ",".join(result["issues"]) if result["issues"] else ""))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
