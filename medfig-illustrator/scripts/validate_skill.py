"""Validate this skill's SKILL.md frontmatter (stdlib only, bundled with the skill).

Mirrors the checks of the skill-creator quick validator so the quality gate does
not depend on a file that only exists on the author's machine.

Usage: validate_skill.py <skill_dir>
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ALLOWED_KEYS = {"name", "description", "license", "allowed-tools", "metadata"}
MAX_NAME = 64
MAX_DESCRIPTION = 1024


def parse_frontmatter(text: str) -> dict[str, str]:
    """Parse the flat ``key: value`` frontmatter used by skills (no nesting needed
    beyond ignoring indented lines under ``metadata``)."""
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        raise ValueError("Invalid frontmatter format")
    fields: dict[str, str] = {}
    for line in match.group(1).split("\n"):
        if not line.strip() or line[0] in " \t#":
            continue
        key, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"Invalid frontmatter line: {line!r}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


def validate(skill_dir: Path) -> tuple[bool, str]:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return False, "SKILL.md not found"
    text = skill_md.read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---"):
        return False, "No YAML frontmatter found"
    try:
        fields = parse_frontmatter(text)
    except ValueError as error:
        return False, str(error)
    unexpected = set(fields) - ALLOWED_KEYS
    if unexpected:
        return False, f"Unexpected key(s) in SKILL.md frontmatter: {', '.join(sorted(unexpected))}"
    for key in ("name", "description"):
        if not fields.get(key):
            return False, f"Missing '{key}' in frontmatter"
    name = fields["name"]
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        return False, f"Name '{name}' should be hyphen-case"
    if len(name) > MAX_NAME:
        return False, f"Name is too long ({len(name)} characters)"
    if name != skill_dir.resolve().name:
        return False, f"Name '{name}' does not match directory '{skill_dir.resolve().name}'"
    description = fields["description"]
    if "<" in description or ">" in description:
        return False, "Description cannot contain angle brackets (< or >)"
    if len(description) > MAX_DESCRIPTION:
        return False, f"Description is too long ({len(description)} characters)"
    return True, "Skill is valid!"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("Usage: validate_skill.py <skill_dir>")
        return 1
    ok, message = validate(Path(argv[1]))
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
