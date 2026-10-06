from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import xml.etree.ElementTree as ET

from layout_guard import (Bounds, TextSpec, audit_svg, font_path, generic_bounds, measure_text, repair_svg,
                          rotated_bounds, text_metrics)

# layout_guard resolves real font files from C:/Windows/Fonts and falls back to an
# estimated table elsewhere; Arial Narrow ships with Office, not with mscorefonts, so
# the narrow-metric case only means something where arialn.ttf is actually resolvable.
_narrow = font_path("Arial Narrow")
ARIAL_NARROW_AVAILABLE = _narrow is not None and Path(_narrow).name.lower() == "arialn.ttf"


SVG_NS = "http://www.w3.org/2000/svg"


def fixture(
    box_width: float = 120,
    box_height: float = 48,
    text: str = "Graph Builder",
    font_size: float = 16,
    second_text: bool = False,
) -> str:
    extra = (
        '<text id="label-2" x="65" y="30" font-family="Arial" font-size="16" '
        'data-collision-role="text">Overlap</text>'
        if second_text
        else ""
    )
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="{SVG_NS}" width="200" height="100" viewBox="0 0 200 100">
  <rect id="box" x="10" y="10" width="{box_width}" height="{box_height}" rx="5"
        fill="#eeeeee" stroke="#111111" data-collision-role="container"/>
  <text id="label" x="{10 + box_width / 2}" y="38" text-anchor="middle"
        font-family="Arial" font-size="{font_size}" data-container-id="box"
        data-layout-group="module" data-collision-role="text">{text}</text>
  {extra}
</svg>'''


class LayoutGuardTests(unittest.TestCase):
    def write_svg(self, root: Path, content: str, name: str = "input.svg") -> Path:
        path = root / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_arc_path_bounds_do_not_treat_arc_flags_as_coordinates(self) -> None:
        path = ET.fromstring('<path d="M964 507 L964 497 A10 10 0 0 1 974 507 Z"/>')
        bounds = generic_bounds(path)
        self.assertGreaterEqual(bounds.left, 954)
        self.assertLessEqual(bounds.right, 984)
        self.assertGreaterEqual(bounds.top, 487)
        self.assertLessEqual(bounds.bottom, 517)

    @unittest.skipUnless(ARIAL_NARROW_AVAILABLE, "Arial Narrow (arialn.ttf) is not installed")
    def test_arial_narrow_metrics_support_dense_table_cells(self) -> None:
        width, _ = text_metrics("Eₛ₁·Eₕ₁", "Arial Narrow", 8)
        self.assertLess(width, 26)

    def test_middle_anchored_text_bounds(self) -> None:
        spec = TextSpec("Graph Builder", 100, 50, 16, "Arial", "middle", 0)
        bounds = measure_text(spec)
        self.assertLess(bounds.left, 100)
        self.assertGreater(bounds.right, 100)
        self.assertGreater(bounds.width, 40)

    def test_rotated_bounds_swap_dimensions(self) -> None:
        source = Bounds(10, 20, 50, 40)
        result = rotated_bounds(source, -90, 10, 40)
        self.assertAlmostEqual(result.width, source.height, places=3)
        self.assertAlmostEqual(result.height, source.width, places=3)

    def test_boxed_text_requires_half_font_padding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_svg(Path(tmp), fixture(box_width=80, text="Too wide for this box"))
            report = audit_svg(path)
            self.assertTrue(any(issue.code == "TEXT_CONTAINER_OVERFLOW" for issue in report.issues))

    def test_text_collision_is_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_svg(Path(tmp), fixture(second_text=True))
            report = audit_svg(path)
            self.assertTrue(any(issue.code == "TEXT_TEXT_OVERLAP" for issue in report.issues))

    def test_diagonal_connector_uses_segment_not_bounding_box(self) -> None:
        svg = f'''<svg xmlns="{SVG_NS}" width="200" height="100">
          <text id="label" x="80" y="25" font-family="Arial" font-size="12">Clear</text>
          <line id="edge" x1="10" y1="90" x2="190" y2="10" data-collision-role="connector"/>
        </svg>'''
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_svg(self.write_svg(Path(tmp), svg))
        self.assertFalse(any(issue.code == "TEXT_GRAPHIC_OVERLAP" for issue in report.issues))

    def test_connector_crossing_text_is_blocking(self) -> None:
        svg = f'''<svg xmlns="{SVG_NS}" width="200" height="100">
          <text id="label" x="80" y="55" font-family="Arial" font-size="12">Hit</text>
          <line id="edge" x1="10" y1="50" x2="190" y2="50" data-collision-role="connector"/>
        </svg>'''
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_svg(self.write_svg(Path(tmp), svg))
        self.assertTrue(any(issue.code == "TEXT_GRAPHIC_OVERLAP" for issue in report.issues))

    def test_inherited_group_font_size_is_used_for_collision_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="{SVG_NS}" width="120" height="60" viewBox="0 0 120 60">
  <g font-family="Arial" font-size="8" data-collision-role="text">
    <text id="first" x="10" y="20">Eₛ₁·Eₕ₁</text>
    <text id="second" x="50" y="20">Eₛ₂·Eₕ₂</text>
  </g>
</svg>'''
            path = self.write_svg(Path(tmp), source)
            report = audit_svg(path)
            self.assertFalse(any(issue.code == "TEXT_TEXT_OVERLAP" for issue in report.issues))

    def test_repair_wraps_before_shrinking(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_svg(Path(tmp), fixture(box_width=105, box_height=80, text="Core Symptom Encoder"))
            repaired = repair_svg(path)
            label = repaired.text("label")
            self.assertGreaterEqual(label.line_count, 2)
            self.assertEqual(label.font_size, 16)

    def test_compact_single_line_label_shrinks_before_wrapping(self) -> None:
        """Catch the Symptom Vocab regression: one short label must stay one line."""
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_svg(Path(tmp), fixture(box_width=128, box_height=34, text="Symptom Vocab"))
            repaired = repair_svg(path)
            label = repaired.text("label")
            self.assertEqual(label.line_count, 1)
            self.assertGreaterEqual(label.font_size, 14)

    def test_typography_hierarchy_assigns_title_weight_without_bolding_body(self) -> None:
        """Catch flat typography: the larger first line is a title, the subtitle is body text."""
        with tempfile.TemporaryDirectory() as tmp:
            source = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="{SVG_NS}" width="180" height="100" viewBox="0 0 180 100">
  <rect id="box" x="10" y="10" width="150" height="70" fill="#eeeeee" data-collision-role="container"/>
  <text id="title" x="85" y="38" text-anchor="middle" font-family="Arial" font-size="16"
        data-container-id="box" data-collision-role="text">Herb Encoder</text>
  <text id="body" x="85" y="62" text-anchor="middle" font-family="Arial" font-size="12"
        data-container-id="box" data-collision-role="text">Structure to features</text>
</svg>'''
            repaired = repair_svg(self.write_svg(Path(tmp), source))
            self.assertEqual(repaired._find("title").get("font-weight"), "600")
            self.assertEqual(repaired._find("body").get("font-weight"), "400")

    def test_stacked_card_text_uses_nearest_visible_frame(self) -> None:
        """Catch text being centered in the rear card instead of the visible front card."""
        with tempfile.TemporaryDirectory() as tmp:
            source = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="{SVG_NS}" width="200" height="100" viewBox="0 0 200 100">
  <rect id="rear" x="20" y="10" width="128" height="34" data-collision-role="container" data-layout-group="cards"/>
  <rect id="middle" x="24" y="14" width="128" height="34" data-collision-role="frame" data-layout-group="cards"/>
  <rect id="front" x="28" y="18" width="128" height="34" data-collision-role="frame" data-layout-group="cards"/>
  <text id="label" x="92" y="40" text-anchor="middle" font-family="Arial" font-size="16"
        data-container-id="rear" data-layout-group="cards" data-collision-role="text">Symptom Vocab</text>
</svg>'''
            repaired = repair_svg(self.write_svg(Path(tmp), source))
            self.assertEqual(repaired._find("label").get("data-container-id"), "front")

    def test_repair_respects_font_floor_and_expands_container(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_svg(Path(tmp), fixture(box_width=25, box_height=15, text="Target", font_size=10))
            repaired = repair_svg(path)
            self.assertGreaterEqual(repaired.text("label").font_size, 8)
            self.assertGreater(repaired.container("box").width, 25)

    def test_repair_keeps_multiple_texts_in_one_container_separate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="{SVG_NS}" width="160" height="100" viewBox="0 0 160 100">
  <rect id="box" x="10" y="10" width="120" height="64" fill="#eeeeee" data-collision-role="container"/>
  <text id="title" x="70" y="34" text-anchor="middle" font-family="Arial" font-size="16"
        data-container-id="box" data-collision-role="text">Herb Encoder</text>
  <text id="subtitle" x="70" y="58" text-anchor="middle" font-family="Arial" font-size="12"
        data-container-id="box" data-collision-role="text">Structure to features</text>
</svg>'''
            path = self.write_svg(Path(tmp), source)
            repaired = repair_svg(path)
            self.assertFalse(any(issue.code == "TEXT_TEXT_OVERLAP" for issue in repaired.report.issues))
            title_y = float(repaired._find("title").get("y"))
            subtitle_y = float(repaired._find("subtitle").get("y"))
            self.assertGreater(subtitle_y - title_y, 12)

    def test_cli_writes_passing_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_svg = self.write_svg(root, fixture(box_width=105, box_height=80, text="Core Symptom Encoder"))
            output_svg = root / "approved.svg"
            report_path = root / "report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "layout_guard.py"),
                    "--input",
                    str(input_svg),
                    "--output",
                    str(output_svg),
                    "--report",
                    str(report_path),
                    "--repair",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["unresolved_count"], 0)
            self.assertIn("summary", report)
            self.assertGreater(report["summary"]["repairs_by_action"].get("reflow_text", 0), 0)
            for repair in report["repairs"]:
                self.assertEqual(
                    {"action", "element_id", "before", "after", "reason"} - set(repair),
                    set(),
                )
            self.assertTrue(output_svg.exists())

    # run_cell_lct.ps1 is a PowerShell driver, so this case can only run on Windows.
    # The rest of this module is pure Python and runs everywhere.
    @unittest.skipUnless(sys.platform == "win32", "run_cell_lct.ps1 is a PowerShell driver")
    def test_runner_dry_run_caches_layout_approved_svg(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_svg = self.write_svg(root, fixture(box_width=105, box_height=80, text="Core Symptom Encoder"))
            work_dir = root / "cache"
            runner = SCRIPT_DIR / "run_cell_lct.ps1"
            completed = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(runner),
                    "-InputSvg",
                    str(input_svg),
                    "-WorkDir",
                    str(work_dir),
                    "-DryRun",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            cache = json.loads((work_dir / "geometry-cache.json").read_text(encoding="utf-8-sig"))
            self.assertEqual(Path(cache["source_svg"]).name, "layout-approved.svg")
            report = json.loads((work_dir / "layout-preflight.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "PASS")


def raster_fixture(href: str = "assets/panel.png", text_y: float = 90) -> str:
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="{SVG_NS}" xmlns:xlink="http://www.w3.org/1999/xlink" width="200" height="100" viewBox="0 0 200 100">
  <rect id="frame" x="5" y="5" width="60" height="20" fill="#eeeeee"/>
  <image id="panel" data-raster-source="user-asset" x="80" y="10" width="80" height="40"
         preserveAspectRatio="none" xlink:href="{href}"/>
  <text id="caption" x="80" y="{text_y}" font-family="Arial" font-size="10">Input B-scan</text>
</svg>'''


class RasterOptInTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "assets").mkdir()
        from PIL import Image
        Image.new("L", (40, 20), 128).save(self.root / "assets" / "panel.png")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def prepare(self, svg: str, *extra: str) -> subprocess.CompletedProcess:
        path = self.root / "input.svg"
        path.write_text(svg, encoding="utf-8")
        work = self.root / ("work" + str(len(list(self.root.glob("work*")))))
        return subprocess.run(
            [sys.executable, "-X", "utf8", str(SCRIPT_DIR / "prepare_geometry_cache.py"),
             "--input", str(path), "--output-dir", str(work), "--job-id", "raster", *extra],
            text=True, capture_output=True, check=False,
        ), work

    def test_image_is_refused_without_opt_in(self) -> None:
        completed, _ = self.prepare(raster_fixture())
        self.assertEqual(completed.returncode, 1)
        self.assertIn("--allow-raster", completed.stderr)

    def test_opt_in_image_becomes_image_atom_with_hash(self) -> None:
        completed, work = self.prepare(raster_fixture(), "--allow-raster")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        cache = json.loads((work / "geometry-cache.json").read_text(encoding="utf-8"))
        self.assertEqual(cache["raster_count"], 1)
        image = [atom for atom in cache["atoms"] if atom["kind"] == "image"][0]["image"]
        self.assertEqual(image["bounds"], [80.0, 10.0, 160.0, 50.0])
        self.assertEqual(len(image["sha256"]), 64)

    def test_data_uri_and_unmarked_images_are_refused(self) -> None:
        completed, _ = self.prepare(raster_fixture("data:image/png;base64,AAAA"), "--allow-raster")
        self.assertEqual(completed.returncode, 1)
        unmarked = raster_fixture().replace(' data-raster-source="user-asset"', "")
        completed, _ = self.prepare(unmarked, "--allow-raster")
        self.assertEqual(completed.returncode, 1)

    def test_text_on_image_is_a_blocking_collision(self) -> None:
        path = self.root / "clash.svg"
        path.write_text(raster_fixture(text_y=30), encoding="utf-8")
        report = audit_svg(path)
        offending = {(issue.code, issue.other_id) for issue in report.issues}
        self.assertIn(("TEXT_GRAPHIC_OVERLAP", "panel"), offending)


if __name__ == "__main__":
    unittest.main()
