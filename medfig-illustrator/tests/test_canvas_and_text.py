from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from artboard_fit import plan  # noqa: E402
from svg_live_text import audit_text, describe, fix_text  # noqa: E402

A4_W, A4_H = 595.276, 841.89


class ArtboardFitTests(unittest.TestCase):
    def test_a4_too_small_for_wide_figure_resizes(self):
        result = plan(1536, 1024, 12, A4_W, A4_H, 0.72, 0.78)
        self.assertEqual(result["action"], "resize")
        self.assertLess(result["placed_min_font_pt"], 8.0)
        self.assertGreaterEqual(result["new_placed_min_font_pt"], 8.0)

    def test_resize_never_shrinks_either_side(self):
        result = plan(1536, 1024, 12, A4_W, A4_H, 0.72, 0.78)
        self.assertGreaterEqual(result["to"][0], A4_W)
        self.assertGreaterEqual(result["to"][1], A4_H)

    def test_large_enough_artboard_is_kept(self):
        result = plan(400, 300, 14, 1200, 900, 0.72, 0.78)
        self.assertEqual(result["action"], "keep")
        self.assertEqual(result["to"], result["from"])

    def test_rejects_non_positive_inputs(self):
        with self.assertRaises(ValueError):
            plan(0, 1024, 12, A4_W, A4_H, 0.72, 0.78)


GLYPH_SVG = """<svg viewBox="0 0 10 10"><font horiz-adv-x="1000"><font-face font-family="ArialMT"/>
<glyph unicode="a" d="M0 0L1 1z"/></font><text style="font-family:'ArialMT'; font-size:12px;">a</text></svg>"""
LIVE_SVG = """<svg viewBox="0 0 10 10"><text style="font-family:'Arial-BoldMT'; font-size:12px;">Edema</text>
<text style="font-family:'ArialMT'; font-size:12px;">Normal</text></svg>"""


class LiveTextTests(unittest.TestCase):
    def test_embedded_glyph_outlines_fail(self):
        result = audit_text(GLYPH_SVG)
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any(issue.startswith("SVG_EMBEDS_GLYPH_OUTLINES") for issue in result["issues"]))

    def test_font_referenced_text_passes_with_expected_count(self):
        self.assertEqual(audit_text(LIVE_SVG, expected_text_count=2)["status"], "PASS")

    def test_text_count_mismatch_fails(self):
        self.assertEqual(audit_text(LIVE_SVG, expected_text_count=3)["status"], "FAIL")

    def test_wrapped_text_with_font_on_tspans_passes(self):
        svg = ('<svg viewBox="0 0 1 1"><text transform="matrix(1 0 0 1 0 0)">'
               "<tspan x=\"0\" y=\"0\" style=\"font-family:'ArialMT'; font-size:9px;\">Stage 1</tspan>"
               "<tspan x=\"0\" y=\"11\" style=\"font-family:'ArialMT'; font-size:9px;\">labels</tspan></text></svg>")
        self.assertEqual(audit_text(svg)["status"], "PASS")

    def test_text_with_unstyled_tspan_fails(self):
        svg = ('<svg viewBox="0 0 1 1"><text><tspan style="font-family:\'ArialMT\'">a</tspan>'
               '<tspan>b</tspan></text></svg>')
        self.assertTrue(any(i.startswith("SVG_TEXT_WITHOUT_FONT_FAMILY") for i in audit_text(svg)["issues"]))

    def test_outlined_text_without_text_nodes_fails(self):
        result = audit_text('<svg viewBox="0 0 1 1"><path d="M0 0L1 1z"/></svg>')
        self.assertIn("SVG_HAS_NO_LIVE_TEXT", result["issues"])

    def test_fix_adds_family_fallback_and_weight(self):
        fixed, count = fix_text(LIVE_SVG)
        self.assertEqual(count, 2)
        self.assertIn("font-family:'Arial-BoldMT', 'Arial', sans-serif; font-weight:700", fixed)
        self.assertIn("font-family:'ArialMT', 'Arial', sans-serif; font-weight:400", fixed)
        self.assertEqual(audit_text(fixed, expected_text_count=2)["status"], "PASS")

    def test_fix_is_idempotent(self):
        once, _ = fix_text(LIVE_SVG)
        twice, _ = fix_text(once)
        self.assertEqual(once, twice)

    def test_describe_postscript_faces(self):
        self.assertEqual(describe("Arial-BoldMT"), ("Arial", "700", "normal"))
        self.assertEqual(describe("TimesNewRomanPS-ItalicMT"), ("Times New Roman", "400", "italic"))
        self.assertEqual(describe("ArialMT"), ("Arial", "400", "normal"))


if __name__ == "__main__":
    unittest.main()
