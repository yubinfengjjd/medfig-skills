#!/usr/bin/env python3
"""Audit and repair text layout in medfig-illustrator Master SVG files."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

try:
    from PIL import ImageFont
except ImportError:  # Deterministic fallback remains available.
    ImageFont = None


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def numeric(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.search(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", value)
    return float(match.group(0)) if match else default


def fmt(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


@dataclass(frozen=True)
class Bounds:
    left: float
    top: float
    right: float
    bottom: float

    @property
    def width(self) -> float:
        return max(0.0, self.right - self.left)

    @property
    def height(self) -> float:
        return max(0.0, self.bottom - self.top)

    def inset(self, amount: float) -> "Bounds":
        return Bounds(self.left + amount, self.top + amount, self.right - amount, self.bottom - amount)

    def contains(self, other: "Bounds", tolerance: float = 0.5) -> bool:
        return (
            other.left >= self.left - tolerance
            and other.top >= self.top - tolerance
            and other.right <= self.right + tolerance
            and other.bottom <= self.bottom + tolerance
        )

    def intersection_area(self, other: "Bounds") -> float:
        width = min(self.right, other.right) - max(self.left, other.left)
        height = min(self.bottom, other.bottom) - max(self.top, other.top)
        return max(0.0, width) * max(0.0, height)


@dataclass(frozen=True)
class TextSpec:
    content: str
    x: float
    y: float
    font_size: float
    font_family: str
    anchor: str
    rotation: float
    line_height: float = 1.15


@dataclass
class AuditIssue:
    code: str
    element_id: str
    other_id: str | None
    message: str
    overlap_area: float = 0.0


@dataclass
class AuditReport:
    issues: list[AuditIssue] = field(default_factory=list)

    @property
    def status(self) -> str:
        return "PASS" if not self.issues else "FAIL"


@dataclass
class TextView:
    id: str
    font_size: float
    line_count: int
    content: str


@dataclass
class ContainerView:
    id: str
    width: float
    height: float


@dataclass
class RepairResult:
    tree: ET.ElementTree
    report: AuditReport
    repairs: list[dict]
    source_path: Path

    def _find(self, element_id: str) -> ET.Element:
        for element in self.tree.getroot().iter():
            if element.get("id") == element_id:
                return element
        raise KeyError(element_id)

    def text(self, element_id: str) -> TextView:
        element = self._find(element_id)
        content = "".join(element.itertext())
        lines = re.split(r"[\r\n]+", content)
        return TextView(element_id, numeric(element.get("font-size"), 16), len([line for line in lines if line]), content)

    def container(self, element_id: str) -> ContainerView:
        element = self._find(element_id)
        return ContainerView(element_id, numeric(element.get("width")), numeric(element.get("height")))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.tree.write(path, encoding="utf-8", xml_declaration=True)


@dataclass
class ElementInfo:
    id: str
    element: ET.Element
    kind: str
    bounds: Bounds
    role: str
    container_id: str | None
    layout_group: str | None
    allowed_overlaps: set[str]
    text_spec: TextSpec | None = None


def record_repair(
    repairs: list[dict],
    action: str,
    element_id: str,
    before: dict,
    after: dict,
    reason: str,
    **legacy: object,
) -> None:
    """Append one backward-compatible, reviewable repair record."""
    repairs.append(
        {
            "type": action,
            "id": element_id,
            "action": action,
            "element_id": element_id,
            "before": before,
            "after": after,
            "reason": reason,
            **legacy,
        }
    )


def font_path(family: str) -> Path | None:
    family_lower = family.lower()
    windows_fonts = Path("C:/Windows/Fonts")
    candidates = ["arial.ttf"]
    if "arial narrow" in family_lower:
        candidates = ["arialn.ttf", "arial.ttf"]
    elif "times" in family_lower:
        candidates = ["times.ttf", "arial.ttf"]
    elif "calibri" in family_lower:
        candidates = ["calibri.ttf", "arial.ttf"]
    for name in candidates:
        path = windows_fonts / name
        if path.exists():
            return path
    return None


def text_metrics(content: str, family: str, size: float, line_height: float = 1.15) -> tuple[float, float]:
    lines = re.split(r"[\r\n]+", content) or [""]
    if ImageFont is not None:
        path = font_path(family)
        if path is not None:
            font = ImageFont.truetype(str(path), max(1, round(size * 4)))
            widths = []
            for line in lines:
                box = font.getbbox(line or " ")
                widths.append((box[2] - box[0]) / 4)
            return max(widths, default=0.0), len(lines) * size * line_height
    widest = max((len(line) for line in lines), default=0)
    return widest * size * 0.56, len(lines) * size * line_height


def rotated_bounds(bounds: Bounds, degrees: float, cx: float, cy: float) -> Bounds:
    if not degrees:
        return bounds
    angle = math.radians(degrees)
    cosine, sine = math.cos(angle), math.sin(angle)
    corners = [
        (bounds.left, bounds.top),
        (bounds.right, bounds.top),
        (bounds.right, bounds.bottom),
        (bounds.left, bounds.bottom),
    ]
    points = []
    for x, y in corners:
        dx, dy = x - cx, y - cy
        points.append((cx + dx * cosine - dy * sine, cy + dx * sine + dy * cosine))
    xs, ys = zip(*points)
    return Bounds(min(xs), min(ys), max(xs), max(ys))


def measure_text(spec: TextSpec) -> Bounds:
    width, height = text_metrics(spec.content, spec.font_family, spec.font_size, spec.line_height)
    if spec.anchor == "middle":
        left = spec.x - width / 2
    elif spec.anchor == "end":
        left = spec.x - width
    else:
        left = spec.x
    source = Bounds(left, spec.y - height, left + width, spec.y)
    return rotated_bounds(source, spec.rotation, spec.x, spec.y)


def parse_rotation(value: str | None) -> float:
    if not value:
        return 0.0
    match = re.search(r"rotate\(\s*([-+0-9.eE]+)", value)
    return float(match.group(1)) if match else 0.0


def rect_bounds(element: ET.Element) -> Bounds:
    x, y = numeric(element.get("x")), numeric(element.get("y"))
    return Bounds(x, y, x + numeric(element.get("width")), y + numeric(element.get("height")))


def path_bounds(path_data: str) -> Bounds:
    """Return conservative SVG path bounds without interpreting flags as points."""
    tokens = re.findall(r"[AaCcHhLlMmQqSsTtVvZz]|[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", path_data)
    arity = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}
    points: list[tuple[float, float]] = []
    index = 0
    command = ""
    current_x = current_y = 0.0
    start_x = start_y = 0.0
    while index < len(tokens):
        if re.fullmatch(r"[A-Za-z]", tokens[index]):
            command = tokens[index]
            index += 1
            if command.upper() == "Z":
                current_x, current_y = start_x, start_y
                points.append((current_x, current_y))
                continue
        if not command:
            break
        upper = command.upper()
        count = arity[upper]
        if index + count > len(tokens) or (index < len(tokens) and re.fullmatch(r"[A-Za-z]", tokens[index])):
            continue
        values = [float(value) for value in tokens[index : index + count]]
        index += count
        relative = command.islower()

        def absolute(x: float, y: float) -> tuple[float, float]:
            return (current_x + x, current_y + y) if relative else (x, y)

        if upper in {"M", "L", "T"}:
            current_x, current_y = absolute(values[0], values[1])
            points.append((current_x, current_y))
            if upper == "M":
                start_x, start_y = current_x, current_y
                command = "l" if relative else "L"
        elif upper == "H":
            current_x = current_x + values[0] if relative else values[0]
            points.append((current_x, current_y))
        elif upper == "V":
            current_y = current_y + values[0] if relative else values[0]
            points.append((current_x, current_y))
        elif upper == "C":
            controls = [absolute(values[offset], values[offset + 1]) for offset in (0, 2, 4)]
            points.extend(controls)
            current_x, current_y = controls[-1]
        elif upper in {"S", "Q"}:
            controls = [absolute(values[offset], values[offset + 1]) for offset in (0, 2)]
            points.extend(controls)
            current_x, current_y = controls[-1]
        elif upper == "A":
            radius_x, radius_y = abs(values[0]), abs(values[1])
            end_x, end_y = absolute(values[5], values[6])
            points.extend(
                [
                    (current_x - radius_x, current_y - radius_y),
                    (current_x + radius_x, current_y + radius_y),
                    (end_x - radius_x, end_y - radius_y),
                    (end_x + radius_x, end_y + radius_y),
                ]
            )
            current_x, current_y = end_x, end_y
    if not points:
        return Bounds(0, 0, 0, 0)
    xs, ys = zip(*points)
    return Bounds(min(xs), min(ys), max(xs), max(ys))


def generic_bounds(element: ET.Element) -> Bounds:
    kind = local_name(element.tag)
    if kind in {"rect", "image"}:
        return rect_bounds(element)
    if kind == "circle":
        cx, cy, radius = numeric(element.get("cx")), numeric(element.get("cy")), numeric(element.get("r"))
        return Bounds(cx - radius, cy - radius, cx + radius, cy + radius)
    if kind == "ellipse":
        cx, cy = numeric(element.get("cx")), numeric(element.get("cy"))
        rx, ry = numeric(element.get("rx")), numeric(element.get("ry"))
        return Bounds(cx - rx, cy - ry, cx + rx, cy + ry)
    if kind == "line":
        x1, y1, x2, y2 = (numeric(element.get(key)) for key in ("x1", "y1", "x2", "y2"))
        return Bounds(min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))
    if kind == "path":
        return path_bounds(element.get("d") or "")
    values = [float(item) for item in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", element.get("points") or "")]
    points = list(zip(values[::2], values[1::2]))
    if not points:
        return Bounds(0, 0, 0, 0)
    xs, ys = zip(*points)
    return Bounds(min(xs), min(ys), max(xs), max(ys))


def collect_elements(root: ET.Element) -> list[ElementInfo]:
    result: list[ElementInfo] = []
    generated = 0

    inherited_keys = {
        "font-size",
        "font-family",
        "text-anchor",
        "data-line-height",
        "data-collision-role",
        "data-layout-group",
        "data-overlap-allow",
    }

    def walk(parent: ET.Element, inherited: dict[str, str]) -> None:
        nonlocal generated
        for element in list(parent):
            resolved = dict(inherited)
            for key in inherited_keys:
                if element.get(key) is not None:
                    resolved[key] = str(element.get(key))
            kind = local_name(element.tag)
            if kind in {"text", "rect", "circle", "ellipse", "line", "path", "polygon", "polyline", "image"}:
                element_id = element.get("id")
                if not element_id:
                    generated += 1
                    element_id = f"layout-auto-{generated:04d}"
                    element.set("id", element_id)
                # Opt-in raster panels are always obstacles: text must never sit on image pixels.
                default_role = "text" if kind == "text" else ("obstacle" if kind == "image" else "decorative")
                role = resolved.get("data-collision-role") or default_role
                allowed = {
                    item.strip()
                    for item in resolved.get("data-overlap-allow", "").split(",")
                    if item.strip()
                }
                if kind == "text":
                    spec = TextSpec(
                        "".join(element.itertext()),
                        numeric(element.get("x")),
                        numeric(element.get("y")),
                        numeric(resolved.get("font-size"), 16),
                        resolved.get("font-family", "Arial"),
                        resolved.get("text-anchor", "start"),
                        parse_rotation(element.get("transform")),
                        numeric(resolved.get("data-line-height"), 1.15),
                    )
                    bounds = measure_text(spec)
                else:
                    spec = None
                    bounds = generic_bounds(element)
                result.append(
                    ElementInfo(
                        element_id,
                        element,
                        kind,
                        bounds,
                        role,
                        element.get("data-container-id"),
                        resolved.get("data-layout-group"),
                        allowed,
                        spec,
                    )
                )
            walk(element, resolved)

    root_style = {key: str(root.get(key)) for key in inherited_keys if root.get(key) is not None}
    walk(root, root_style)
    return result


def segment_intersects_bounds(x1: float, y1: float, x2: float, y2: float, bounds: Bounds) -> bool:
    """Liang-Barsky segment/rectangle intersection, including contained ends."""
    dx, dy = x2 - x1, y2 - y1
    lower, upper = 0.0, 1.0
    for p, q in (
        (-dx, x1 - bounds.left),
        (dx, bounds.right - x1),
        (-dy, y1 - bounds.top),
        (dy, bounds.bottom - y1),
    ):
        if abs(p) < 1e-12:
            if q < 0:
                return False
            continue
        ratio = q / p
        if p < 0:
            lower = max(lower, ratio)
        else:
            upper = min(upper, ratio)
        if lower > upper:
            return False
    return True


def graphical_overlap(text_bounds: Bounds, obstacle: ElementInfo) -> float:
    """Measure visual collision using shape geometry where boxes over-report."""
    if obstacle.role == "connector" and obstacle.kind == "line":
        element = obstacle.element
        hit = segment_intersects_bounds(
            numeric(element.get("x1")),
            numeric(element.get("y1")),
            numeric(element.get("x2")),
            numeric(element.get("y2")),
            text_bounds,
        )
        return 1.0 if hit else 0.0
    if obstacle.role == "connector" and obstacle.kind == "polyline":
        values = [float(value) for value in re.findall(r"[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?", obstacle.element.get("points") or "")]
        points = list(zip(values[::2], values[1::2]))
        return 1.0 if any(segment_intersects_bounds(*first, *second, text_bounds) for first, second in zip(points, points[1:])) else 0.0
    if obstacle.kind in {"circle", "ellipse"}:
        element = obstacle.element
        cx, cy = numeric(element.get("cx")), numeric(element.get("cy"))
        rx = numeric(element.get("r")) if obstacle.kind == "circle" else numeric(element.get("rx"))
        ry = numeric(element.get("r")) if obstacle.kind == "circle" else numeric(element.get("ry"))
        if rx <= 0 or ry <= 0:
            return 0.0
        nearest_x = min(max(cx, text_bounds.left), text_bounds.right)
        nearest_y = min(max(cy, text_bounds.top), text_bounds.bottom)
        hit = ((nearest_x - cx) / rx) ** 2 + ((nearest_y - cy) / ry) ** 2 <= 1.0
        return 1.0 if hit else 0.0
    return text_bounds.intersection_area(obstacle.bounds)


def audit_tree(tree: ET.ElementTree) -> AuditReport:
    infos = collect_elements(tree.getroot())
    by_id = {item.id: item for item in infos}
    issues: list[AuditIssue] = []
    texts = [item for item in infos if item.kind == "text"]
    for item in texts:
        if item.container_id:
            container = by_id.get(item.container_id)
            if container is None:
                issues.append(AuditIssue("MISSING_TEXT_CONTAINER", item.id, item.container_id, "Assigned text container does not exist."))
            else:
                padding = (item.text_spec.font_size if item.text_spec else 16) * 0.5
                inner = container.bounds.inset(padding)
                if inner.width <= 0 or inner.height <= 0 or not inner.contains(item.bounds):
                    issues.append(AuditIssue("TEXT_CONTAINER_OVERFLOW", item.id, container.id, "Text exceeds the required padded container bounds."))

    for index, first in enumerate(texts):
        for second in texts[index + 1 :]:
            if second.id in first.allowed_overlaps or first.id in second.allowed_overlaps:
                continue
            area = first.bounds.intersection_area(second.bounds)
            if area > 0.5:
                issues.append(AuditIssue("TEXT_TEXT_OVERLAP", first.id, second.id, "Text bounds overlap.", area))

    obstacles = [item for item in infos if item.role in {"obstacle", "connector", "arrow", "icon", "node", "frame"}]
    for item in texts:
        for obstacle in obstacles:
            if obstacle.id == item.container_id or obstacle.id in item.allowed_overlaps or item.id in obstacle.allowed_overlaps:
                continue
            if item.layout_group and item.layout_group == obstacle.layout_group and obstacle.role == "frame":
                continue
            area = graphical_overlap(item.bounds, obstacle)
            if area > 0.5:
                issues.append(AuditIssue("TEXT_GRAPHIC_OVERLAP", item.id, obstacle.id, "Text overlaps an unrelated graphical object.", area))
    return AuditReport(issues)


def audit_svg(path: Path | str) -> AuditReport:
    return audit_tree(ET.parse(Path(path)))


def wrap_candidates(content: str) -> list[list[str]]:
    words = [part for part in re.split(r"\s+", content.strip()) if part]
    if len(words) <= 1:
        return [words or [""]]
    candidates: list[list[str]] = [[content.strip()]]
    for line_count in range(2, len(words) + 1):
        target = sum(len(word) for word in words) / line_count
        lines: list[str] = []
        current: list[str] = []
        current_length = 0
        remaining_lines = line_count
        for word in words:
            projected = current_length + (1 if current else 0) + len(word)
            remaining_words = len(words) - sum(len(line.split()) for line in lines) - len(current)
            if current and projected > target and remaining_words >= remaining_lines - 1:
                lines.append(" ".join(current))
                current = [word]
                current_length = len(word)
                remaining_lines -= 1
            else:
                current.append(word)
                current_length = projected
        if current:
            lines.append(" ".join(current))
        if len(lines) == line_count and lines not in candidates:
            candidates.append(lines)
    return candidates


def lines_fit(lines: list[str], family: str, size: float, container: Bounds, line_height: float) -> bool:
    padding = size * 0.5
    inner = container.inset(padding)
    width, height = text_metrics("\n".join(lines), family, size, line_height)
    return inner.width > 0 and inner.height > 0 and width <= inner.width + 0.5 and height <= inner.height + 0.5


def set_text_layout(
    element: ET.Element,
    lines: list[str],
    size: float,
    container: Bounds,
    line_height: float,
    block_top: float | None = None,
) -> None:
    # Remove only previous text/tspan content. Element.clear() would also
    # erase the stable id and layout ownership metadata required downstream.
    for child in list(element):
        element.remove(child)
    element.text = None
    element.text = "\r".join(lines)
    element.set("font-size", fmt(size))
    element.set("data-line-height", fmt(line_height))
    element.set("x", fmt((container.left + container.right) / 2))
    element.set("text-anchor", "middle")
    total_height = len(lines) * size * line_height
    baseline = (
        block_top + total_height
        if block_top is not None
        else container.top + (container.height - total_height) / 2 + total_height
    )
    element.set("y", fmt(baseline))


def choose_horizontal_layout(item: ElementInfo, container: Bounds) -> tuple[list[str], float]:
    """Choose wrapping and font size without consuming the vertical budget.

    Text blocks sharing one container are laid out as a group later.  Testing
    vertical fit here would incorrectly give every block the full box height.
    """
    if item.text_spec is None:
        return [""], 8.0
    spec = item.text_spec
    candidates = wrap_candidates(spec.content)
    floor = max(8.0, spec.font_size * 0.75)
    # Preserve compact labels on one line when a small size adjustment is
    # enough. Wrapping first can split a compact two-token label even when a
    # visually negligible reduction preserves the source's one-line layout.
    single_line = re.sub(r"\s+", " ", spec.content).strip()
    size = spec.font_size
    while size >= floor - 1e-9:
        available_width = max(0.0, container.width - size)
        width, _ = text_metrics(single_line, spec.font_family, size, spec.line_height)
        if width <= available_width + 0.5:
            return [single_line], size
        size -= 0.5
    size = spec.font_size
    while size >= floor - 1e-9:
        available_width = max(0.0, container.width - size)
        for lines in candidates:
            if len(lines) == 1:
                continue
            width, _ = text_metrics("\n".join(lines), spec.font_family, size, spec.line_height)
            if width <= available_width + 0.5:
                return lines, size
        size -= 0.5
    return (
        min(
            candidates,
            key=lambda lines: text_metrics("\n".join(lines), spec.font_family, floor, spec.line_height)[0],
        ),
        floor,
    )


def apply_typography_hierarchy(infos: list[ElementInfo], repairs: list[dict]) -> None:
    """Assign restrained semantic weights when the source omits hierarchy."""
    texts = [item for item in infos if item.kind == "text" and item.text_spec]
    grouped: dict[str, list[ElementInfo]] = {}
    for item in texts:
        if item.container_id:
            grouped.setdefault(item.container_id, []).append(item)

    role_weights = {
        "panel-label": "700",
        "section-heading": "600",
        "module-title": "600",
        "body": "400",
        "annotation": "400",
        "math": "400",
    }
    for item in texts:
        role = (item.element.get("data-typography-role") or "").strip().lower()
        if role in role_weights:
            desired = role_weights[role]
            if item.element.get("font-weight") != desired:
                previous = item.element.get("font-weight")
                item.element.set("font-weight", desired)
                record_repair(
                    repairs,
                    "set_font_weight",
                    item.id,
                    {"font_weight": previous, "typography_role": role},
                    {"font_weight": desired, "typography_role": role},
                    "Apply the explicit semantic typography role.",
                    role=role,
                    font_weight=desired,
                )

    for items in grouped.values():
        items.sort(key=lambda entry: (entry.text_spec.y if entry.text_spec else 0.0, entry.id))
        eligible = [item for item in items if not item.element.get("data-typography-role")]
        if not eligible:
            continue
        for index, item in enumerate(eligible):
            if item.element.get("font-weight") is not None:
                continue
            spec = item.text_spec
            assert spec is not None
            italic = (item.element.get("font-style") or "").strip().lower() in {"italic", "oblique"}
            if italic or spec.font_size < 12:
                desired = "400"
                role = "math" if italic else "annotation"
            elif index == 0:
                desired = "600"
                role = "module-title"
            else:
                desired = "400"
                role = "body"
            previous = item.element.get("font-weight")
            item.element.set("font-weight", desired)
            item.element.set("data-typography-role", role)
            record_repair(
                repairs,
                "set_font_weight",
                item.id,
                {"font_weight": previous, "typography_role": None},
                {"font_weight": desired, "typography_role": role},
                "Infer restrained hierarchy for an unclassified text run.",
                role=role,
                font_weight=desired,
            )


def repair_container_ownership(infos: list[ElementInfo], repairs: list[dict]) -> None:
    """Bind stacked-card labels to the nearest visible rect in their group."""
    by_id = {item.id: item for item in infos}
    rects_by_group: dict[str, list[ElementInfo]] = {}
    for item in infos:
        if item.kind == "rect" and item.layout_group and item.role in {"container", "frame"}:
            rects_by_group.setdefault(item.layout_group, []).append(item)
    for item in infos:
        if not item.text_spec or not item.container_id or not item.layout_group:
            continue
        current = by_id.get(item.container_id)
        candidates = rects_by_group.get(item.layout_group, [])
        if current is None or current.kind != "rect" or len(candidates) < 2:
            continue
        spec = item.text_spec
        visual_x = spec.x
        visual_y = spec.y - spec.font_size * 0.35

        def distance(candidate: ElementInfo) -> float:
            center_x = (candidate.bounds.left + candidate.bounds.right) / 2
            center_y = (candidate.bounds.top + candidate.bounds.bottom) / 2
            return (visual_x - center_x) ** 2 + (visual_y - center_y) ** 2

        nearest = min(candidates, key=distance)
        if nearest.id != current.id and distance(nearest) + 0.25 < distance(current):
            previous = item.container_id
            item.container_id = nearest.id
            item.element.set("data-container-id", nearest.id)
            record_repair(
                repairs,
                "reassign_container",
                item.id,
                {"container_id": previous},
                {"container_id": nearest.id},
                "Bind stacked-card text to the nearest visible card in its layout group.",
                **{"from": previous, "to": nearest.id},
            )


def repair_svg(path: Path | str) -> RepairResult:
    source = Path(path)
    tree = ET.parse(source)
    root = tree.getroot()
    repairs: list[dict] = []
    infos = collect_elements(root)
    repair_container_ownership(infos, repairs)
    apply_typography_hierarchy(infos, repairs)
    by_id = {item.id: item for item in infos}
    grouped: dict[str, list[ElementInfo]] = {}
    for item in [entry for entry in infos if entry.kind == "text" and entry.container_id and entry.text_spec]:
        grouped.setdefault(item.container_id or "", []).append(item)

    for container_id, items in grouped.items():
        container = by_id.get(container_id)
        if container is None or container.kind != "rect":
            continue
        items.sort(key=lambda entry: (entry.text_spec.y if entry.text_spec else 0.0, entry.id))
        layouts: list[dict] = []
        for item in items:
            spec = item.text_spec
            assert spec is not None
            lines, size = choose_horizontal_layout(item, container.bounds)
            layouts.append({"item": item, "spec": spec, "lines": lines, "size": size})

        def vertical_requirements() -> tuple[float, float, float]:
            block_height = sum(len(layout["lines"]) * layout["size"] * layout["spec"].line_height for layout in layouts)
            gap = max(2.0, min((layout["size"] for layout in layouts), default=8.0) * 0.15) if len(layouts) > 1 else 0.0
            padding = max((layout["size"] for layout in layouts), default=8.0) * 0.5
            return block_height, gap, block_height + gap * max(0, len(layouts) - 1) + 2 * padding

        block_height, gap, needed_height = vertical_requirements()
        # If the stack is too tall, shrink blocks together but never below the
        # agreed 75% / 8 pt floor.  Expansion is the deterministic last resort.
        while needed_height > container.bounds.height + 0.5:
            changed = False
            for layout in layouts:
                floor = max(8.0, layout["spec"].font_size * 0.75)
                if layout["size"] - 0.5 >= floor - 1e-9:
                    layout["size"] -= 0.5
                    changed = True
            block_height, gap, needed_height = vertical_requirements()
            if not changed:
                break

        needed_width = max(
            (
                text_metrics("\n".join(layout["lines"]), layout["spec"].font_family, layout["size"], layout["spec"].line_height)[0]
                + layout["size"]
                for layout in layouts
            ),
            default=container.bounds.width,
        )
        old = rect_bounds(container.element)
        new_width = max(old.width, needed_width)
        new_height = max(old.height, needed_height)
        if new_width > old.width + 0.5 or new_height > old.height + 0.5:
            center_x = (old.left + old.right) / 2
            center_y = (old.top + old.bottom) / 2
            container.element.set("x", fmt(center_x - new_width / 2))
            container.element.set("y", fmt(center_y - new_height / 2))
            container.element.set("width", fmt(new_width))
            container.element.set("height", fmt(new_height))
            container.bounds = rect_bounds(container.element)
            record_repair(
                repairs,
                "expand_container",
                container.id,
                {"width": old.width, "height": old.height},
                {"width": new_width, "height": new_height},
                "Restore required half-font padding after bounded text reflow.",
                width=new_width,
                height=new_height,
            )

        total_stack_height = block_height + gap * max(0, len(layouts) - 1)
        cursor = container.bounds.top + (container.bounds.height - total_stack_height) / 2
        for layout in layouts:
            item = layout["item"]
            spec = layout["spec"]
            lines = layout["lines"]
            size = layout["size"]
            set_text_layout(item.element, lines, size, container.bounds, spec.line_height, cursor)
            cursor += len(lines) * size * spec.line_height + gap
            if lines != [spec.content] or size != spec.font_size:
                record_repair(
                    repairs,
                    "reflow_text",
                    item.id,
                    {"lines": [spec.content], "font_size": spec.font_size},
                    {"lines": lines, "font_size": size},
                    "Fit text spatially while preserving content and configured font floors.",
                    lines=lines,
                    font_size=size,
                )

    report = audit_tree(tree)
    return RepairResult(tree, report, repairs, source)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_report(result: RepairResult, input_path: Path, output_path: Path | None) -> dict:
    repairs_by_action = Counter(repair.get("action", repair.get("type", "unknown")) for repair in result.repairs)
    issues_by_code = Counter(issue.code for issue in result.report.issues)
    return {
        "schema_version": "2.0",
        "status": result.report.status,
        "input_svg": str(input_path.resolve()),
        "input_sha256": sha256(input_path),
        "output_svg": str(output_path.resolve()) if output_path else None,
        "thresholds": {"relative_font_floor": 0.75, "absolute_font_floor": 8.0, "padding_font_multiple": 0.5},
        "repair_count": len(result.repairs),
        "repairs": result.repairs,
        "unresolved_count": len(result.report.issues),
        "issues": [asdict(issue) for issue in result.report.issues],
        "summary": {
            "repairs_by_action": dict(sorted(repairs_by_action.items())),
            "issues_by_code": dict(sorted(issues_by_code.items())),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    try:
        result = repair_svg(args.input) if args.repair else RepairResult(ET.parse(args.input), audit_svg(args.input), [], args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.write(args.output)
        report = render_report(result, args.input, args.output)
        report["output_sha256"] = sha256(args.output)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["status"], "report": str(args.report.resolve()), "output": str(args.output.resolve())}))
        return 0 if report["status"] == "PASS" else 2
    except (OSError, ET.ParseError, ValueError) as error:
        print(f"LAYOUT_GUARD_ERROR|{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
