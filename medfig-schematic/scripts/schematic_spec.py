"""Load and self-check a medfig-schematic ``schematic.yaml`` (shared by prompt_check, image_check, round_pack).

Spec fields (references/spec_format.md):
  figure            str, e.g. "Fig 1"
  size              {width_mm: 180, aspect: "3:2"}
  palette           {group: {name: "#RRGGBB"}}; every colour the prompt may name
  distinct_groups   [group, ...] whose colours must stay apart (class colours)
  labels            {row: [label, ...]} or [label, ...]; every text string allowed in the figure
  allowed_numbers   ["4", "16", "90%", ...]; the only numbers that may appear inside labels
  image_slots       [label, ...]; empty placeholders, real images are pasted later
  forbidden_patterns [regex, ...]; internal codes (case-sensitive), never in prompt or figure
  ignore_quotes     [text, ...]; quoted phrases in prompts that are not figure labels
"""
import re
from pathlib import Path

import yaml

HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")
# numbers inside a label: 16, 2.5, 90%, also the parts of "16 × 3" / "5 × 256"
NUMBER = re.compile(r"(?<![\w#])\d+(?:\.\d+)?%?")


class SpecError(ValueError):
    pass


def _flat_labels(labels):
    if labels is None:
        return []
    if isinstance(labels, dict):
        out = []
        for row, items in labels.items():
            if not isinstance(items, list):
                raise SpecError(f"labels.{row} must be a list")
            out += items
        return [str(x) for x in out]
    if isinstance(labels, list):
        return [str(x) for x in labels]
    raise SpecError("labels must be a list or a {row: [labels]} mapping")


def load(path):
    """Read schematic.yaml and return a dict with normalised fields plus 'colours' {hex_upper: name}."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise SpecError("schematic.yaml must be a mapping")
    spec = dict(raw)
    spec["labels_flat"] = _flat_labels(raw.get("labels"))
    palette = raw.get("palette") or {}
    if not isinstance(palette, dict):
        raise SpecError("palette must be {group: {name: hex}}")
    colours = {}
    for group, items in palette.items():
        if not isinstance(items, dict):
            raise SpecError(f"palette.{group} must be {{name: hex}}")
        for name, hx in items.items():
            if not HEX.fullmatch(str(hx)):
                raise SpecError(f"palette.{group}.{name}: {hx!r} is not #RRGGBB")
            colours[str(hx).upper()] = f"{group}.{name}"
    spec["palette"] = palette
    spec["colours"] = colours
    for g in raw.get("distinct_groups") or []:
        if g not in palette:
            raise SpecError(f"distinct_groups: {g!r} is not a palette group")
    spec["distinct_groups"] = list(raw.get("distinct_groups") or [])
    spec["allowed_numbers"] = [str(x) for x in raw.get("allowed_numbers") or []]
    spec["image_slots"] = [str(x) for x in raw.get("image_slots") or []]
    spec["forbidden_patterns"] = [str(x) for x in raw.get("forbidden_patterns") or []]
    spec["ignore_quotes"] = [str(x) for x in raw.get("ignore_quotes") or []]
    for p in spec["forbidden_patterns"]:
        try:
            re.compile(p)
        except re.error as e:
            raise SpecError(f"forbidden_patterns: bad regex {p!r}: {e}") from e
    size = raw.get("size") or {}
    spec["aspect"] = parse_aspect(size.get("aspect")) if size.get("aspect") else None
    spec["width_mm"] = size.get("width_mm")
    return spec


def parse_aspect(text):
    """'3:2' -> 1.5 (width / height)."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[:/x×]\s*(\d+(?:\.\d+)?)\s*", str(text))
    if not m:
        raise SpecError(f"size.aspect {text!r} is not W:H")
    return float(m.group(1)) / float(m.group(2))


def label_numbers(text):
    return NUMBER.findall(str(text))


def self_check(spec):
    """Spec-level issues: [(level, message)]. Labels must only carry allowed numbers, slots must be labels,
    no label may match a forbidden pattern, duplicate labels are reported."""
    out = []
    allowed = set(spec["allowed_numbers"])
    labels = spec["labels_flat"]
    seen = set()
    for lab in labels:
        if lab in seen:
            out.append(("WARN", f"label listed twice: {lab!r}"))
        seen.add(lab)
        bad = [n for n in label_numbers(lab) if n not in allowed]
        if bad:
            out.append(("ERROR", f"label {lab!r} has numbers not in allowed_numbers: {bad} "
                                 "(design numbers only; add them to allowed_numbers if they are)"))
        for p in spec["forbidden_patterns"]:
            if re.search(p, lab):
                out.append(("ERROR", f"label {lab!r} matches forbidden pattern {p!r}"))
    for slot in spec["image_slots"]:
        if slot not in seen:
            out.append(("ERROR", f"image slot {slot!r} is not in labels"))
    if not labels:
        out.append(("ERROR", "no labels: list every text string the figure may contain"))
    if not spec["colours"]:
        out.append(("ERROR", "empty palette"))
    return out
