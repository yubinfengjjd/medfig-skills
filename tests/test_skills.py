"""Suite-wide skill format checks (mirrors skill-creator quick_validate.py).

Dirs that do not exist yet are skipped so the test works before all merges.
"""
import json
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ["medfig-suite", "medfig-plan", "medfig-render", "medfig-orchestrate", "medfig-outline"]
ALLOWED = {"name", "description", "license", "metadata"}
# Project names / dataset names that must never appear in the skills: one per line in the git-ignored
# tests/leak_strings.local.txt (kept out of the public repo), plus the generic markers below.
_LOCAL = ROOT / "tests" / "leak_strings.local.txt"
LEAK_STRINGS = ["@local>", "C:/Users/"] + (
    [l.strip() for l in _LOCAL.read_text(encoding="utf-8").splitlines() if l.strip()] if _LOCAL.is_file() else [])
# Isolation guard (spec §0): no reference to the external workflow suite.
FORBIDDEN = re.compile(
    r"paper-harness|paperflow|harness|visual-plan|visual-render|visual-review",
    re.IGNORECASE,
)


def _skill_dir(name):
    d = ROOT / name
    if not d.is_dir():
        pytest.skip(f"{name}/ not present yet")
    return d


def _split(skill_md):
    text = skill_md.read_text(encoding="utf-8").replace("\r\n", "\n")
    assert text.startswith("---"), "No YAML frontmatter found"
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    assert m, "Invalid frontmatter format"
    fm = yaml.safe_load(m.group(1))
    assert isinstance(fm, dict), "Frontmatter must be a YAML dictionary"
    return fm, text[m.end():]


@pytest.mark.parametrize("name", SKILLS)
def test_skill_md_exists(name):
    d = _skill_dir(name)
    assert (d / "SKILL.md").is_file(), f"{name}/ exists but SKILL.md missing"


def _skill_md(name):
    d = _skill_dir(name)
    p = d / "SKILL.md"
    assert p.is_file(), f"{name}/ exists but SKILL.md missing"
    return d, p


@pytest.mark.parametrize("name", SKILLS)
def test_frontmatter(name):
    d, p = _skill_md(name)
    fm, body = _split(p)
    extra = set(fm) - ALLOWED
    assert not extra, f"unexpected frontmatter keys: {sorted(extra)}"
    assert "name" in fm and "description" in fm
    n = fm["name"]
    assert isinstance(n, str)
    n = n.strip()
    assert re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", n), f"not kebab-case: {n}"
    assert len(n) <= 64
    assert n == d.name, f"name {n!r} != dir {d.name!r}"
    desc = fm["description"]
    assert isinstance(desc, str)
    desc = desc.strip()
    assert desc.startswith("Use when"), "description must start with 'Use when'"
    assert len(desc) <= 1024, f"description too long: {len(desc)}"
    assert "<" not in desc and ">" not in desc, "angle brackets in description"
    assert len(body.splitlines()) <= 500, "SKILL.md body > 500 lines"


@pytest.mark.parametrize("name", SKILLS)
def test_evals(name):
    d, _ = _skill_md(name)
    p = d / "evals" / "evals.json"
    assert p.is_file(), f"{name}/evals/evals.json missing"
    data = json.loads(p.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 20, "need >= 20 evals"
    for e in data:
        assert isinstance(e.get("query"), str) and e["query"].strip()
        assert isinstance(e.get("should_trigger"), bool)
    neg = sum(1 for e in data if e["should_trigger"] is False)
    assert neg >= 8, f"need >= 8 should_trigger=false, got {neg}"


LINK_RE = re.compile(r"\]\(([^)\s#]*references/[^)\s#]+\.md)(?:#[^)]*)?\)")
CODE_REF_RE = re.compile(r"`((?:[\w.-]+/)?references/[\w.-]+\.md)`")


@pytest.mark.parametrize("name", SKILLS)
def test_reference_links_exist(name):
    d, p = _skill_md(name)
    text = p.read_text(encoding="utf-8")
    refs = set(LINK_RE.findall(text))
    # Backticked own-skill paths (no dir prefix) must exist too.
    refs |= {r for r in CODE_REF_RE.findall(text) if r.startswith("references/")}
    missing = [r for r in sorted(refs) if not (d / r).is_file()]
    assert not missing, f"{name}: missing referenced files {missing}"


@pytest.mark.parametrize("name", SKILLS)
def test_no_project_data_leak(name):
    d = _skill_dir(name)
    hits = []
    for f in d.rglob("*"):
        if not f.is_file() or ".git" in f.relative_to(d).parts:
            continue
        try:
            text = f.read_bytes().decode("utf-8", errors="ignore")
        except OSError:
            continue
        for s in LEAK_STRINGS:
            if s in text:
                hits.append(f"{f.relative_to(ROOT)}: {s}")
    assert not hits, "project-data leak: " + "; ".join(hits)


@pytest.mark.parametrize("name", SKILLS)
def test_no_forbidden_workflow_refs(name):
    d = _skill_dir(name)
    hits = []
    for f in d.rglob("*"):
        if not f.is_file() or ".git" in f.relative_to(d).parts:
            continue
        text = f.read_bytes().decode("utf-8", errors="ignore")
        for i, line in enumerate(text.splitlines(), 1):
            m = FORBIDDEN.search(line)
            if m:
                hits.append(f"{f.relative_to(ROOT)}:{i}: {m.group(0)}")
    assert not hits, "forbidden workflow reference: " + "; ".join(hits)
