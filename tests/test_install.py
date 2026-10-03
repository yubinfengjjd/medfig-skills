"""Tests for install.py using fake target roots under tmp_path."""
from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_skills import FORBIDDEN  # noqa: E402

_spec = importlib.util.spec_from_file_location("medfig_install", ROOT / "install.py")
install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install)

SKILLS = install.SKILLS


def snapshot(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob("*") if p.is_file()}


@pytest.fixture
def src(tmp_path):
    """Copy of the four real skills plus junk files that must be excluded."""
    s = tmp_path / "src"
    for name in SKILLS:
        shutil.copytree(ROOT / name, s / name,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    (s / "research").mkdir()
    (s / "research" / "notes.md").write_text("x")
    (s / "docs").mkdir()
    (s / "docs" / "plan.md").write_text("x")
    r = s / "medfig-render"
    (r / "lib" / "figkit" / "__pycache__").mkdir(parents=True, exist_ok=True)
    (r / "lib" / "figkit" / "__pycache__" / "a.cpython-311.pyc").write_bytes(b"\0")
    (r / "lib" / "stray.pyc").write_bytes(b"\0")
    (r / ".pytest_cache").mkdir()
    (r / ".pytest_cache" / "v").write_text("x")
    (r / ".git").mkdir()
    (r / ".git" / "HEAD").write_text("x")
    for gen in ("out", "data"):
        d = r / "examples" / "minimal" / gen / "sub"
        d.mkdir(parents=True)
        (d / "gen.png").write_bytes(b"png")
    return s


@pytest.fixture
def roots(tmp_path):
    a, b = tmp_path / "home" / ".claude" / "skills", tmp_path / "home" / ".codex" / "skills"
    for t in (a, b):
        t.mkdir(parents=True)
        (t / "other-skill").mkdir()
        (t / "other-skill" / "SKILL.md").write_text("keep me")
    return [a, b]


def make(src, roots, tmp_path, **kw):
    return install.Installer(roots, tmp_path / "backups", src_root=src,
                             log=lambda *a: None, **kw)


def test_dry_run_changes_nothing(src, roots, tmp_path):
    make(src, roots, tmp_path).install()  # previous install -> backup would be planned
    before = snapshot(tmp_path / "home")
    lines = []
    inst = install.Installer(roots, tmp_path / "backups", src_root=src,
                             dry_run=True, log=lines.append)
    assert inst.install() == 0
    assert snapshot(tmp_path / "home") == before
    assert not (tmp_path / "backups").exists()
    text = "\n".join(lines)
    assert "would copy" in text and "would back up" in text
    for t in roots:
        assert str(t) in text


def test_install_copies_exactly_four_dirs(src, roots, tmp_path):
    assert make(src, roots, tmp_path).install() == 0
    for t in roots:
        assert sorted(p.name for p in t.iterdir()) == sorted([*SKILLS, "other-skill"])
        assert (t / "other-skill" / "SKILL.md").read_text() == "keep me"
        assert not (t / "research").exists() and not (t / "docs").exists()
        for name in SKILLS:
            stamp = json.loads((t / name / install.STAMP).read_text())
            files = install.iter_files(src / name)
            assert stamp["file_count"] == len(files)
            assert stamp["manifest_hash"] == install.manifest_hash(install.manifest(src / name))
            assert stamp["version"] and stamp["timestamp"]


def test_excluded_files_absent(src, roots, tmp_path):
    make(src, roots, tmp_path).install()
    r = roots[0] / "medfig-render"
    names = {p.name for p in r.rglob("*")}
    assert "__pycache__" not in names and ".pytest_cache" not in names and ".git" not in names
    assert not list(r.rglob("*.pyc"))
    assert not (r / "examples" / "minimal" / "out").exists()
    assert not (r / "examples" / "minimal" / "data").exists()
    assert (r / "examples" / "minimal").is_dir()


def test_exclusion_rules():
    ex = install.is_excluded
    assert ex(("examples", "minimal", "out", "f.png"))
    assert ex(("examples", "data", "x.csv"))
    assert not ex(("lib", "data", "x.csv"))  # only generated dirs under examples
    assert not ex(("examples", "minimal", "data"))  # a file literally named data
    assert ex(("a", "__pycache__", "m.py"))
    assert ex(("m.pyc",))


def test_verify_passes_then_fails_on_tamper(src, roots, tmp_path):
    make(src, roots, tmp_path).install()
    dest = roots[0] / "medfig-plan"
    assert install.verify(src / "medfig-plan", dest) == []
    (dest / "SKILL.md").write_text("tampered", encoding="utf-8")
    probs = install.verify(src / "medfig-plan", dest)
    assert any("hash mismatch: SKILL.md" in p for p in probs)
    assert make(src, roots, tmp_path).verify_all() == 1


def test_copy_failure_gives_nonzero(src, roots, tmp_path, monkeypatch):
    real = install.shutil.copy2

    def bad_copy(a, b):
        real(a, b)
        if Path(b).name == "SKILL.md":
            Path(b).write_text("corrupt")
    monkeypatch.setattr(install.shutil, "copy2", bad_copy)
    assert make(src, roots, tmp_path).install() == 1


def test_backup_on_reinstall(src, roots, tmp_path):
    make(src, roots, tmp_path).install()
    (roots[0] / "medfig-suite" / "marker.txt").write_text("old")
    inst = make(src, roots, tmp_path)
    assert inst.install() == 0
    bk = inst.backup_dir / install.target_label(roots[0]) / "medfig-suite"
    assert (bk / "marker.txt").read_text() == "old"
    assert inst.backup_dir.parent == tmp_path / "backups"
    assert inst.backup_dir.name.startswith("medfig_")
    assert len(inst.backups) == 2 * len(SKILLS)
    assert not (roots[0] / "medfig-suite" / "marker.txt").exists()
    # the two targets get distinct backup subdirs
    assert len({install.target_label(t) for t in roots}) == 2


def test_update_skips_when_unchanged(src, roots, tmp_path):
    make(src, roots, tmp_path).install()
    inst = make(src, roots, tmp_path)
    assert inst.install(update=True) == 0
    assert inst.backups == [] and not inst.backup_dir.exists()
    # change one source file -> only that skill is reinstalled
    (src / "medfig-plan" / "SKILL.md").write_text(
        (src / "medfig-plan" / "SKILL.md").read_text(encoding="utf-8") + "\n", encoding="utf-8")
    inst = make(src, roots, tmp_path)
    assert inst.install(update=True) == 0
    assert {p.name for p in inst.backups} == {"medfig-plan"}
    assert install.verify(src / "medfig-plan", roots[0] / "medfig-plan") == []


def test_uninstall_moves_to_backup(src, roots, tmp_path):
    make(src, roots, tmp_path).install()
    inst = make(src, roots, tmp_path)
    assert inst.uninstall() == 0
    for t in roots:
        assert sorted(p.name for p in t.iterdir()) == ["other-skill"]
        for name in SKILLS:
            assert (inst.backup_dir / inst.labels[t.resolve()] / name / "SKILL.md").is_file()


def test_installed_tree_has_no_forbidden_words(roots, tmp_path):
    # real repo source, as the user would install it
    assert install.Installer(roots, tmp_path / "backups", log=lambda *a: None).install() == 0
    hits = []
    for f in roots[0].rglob("*"):
        if f.is_file() and f.relative_to(roots[0]).parts[0] in SKILLS:
            for i, line in enumerate(f.read_bytes().decode("utf-8", "ignore").splitlines(), 1):
                if FORBIDDEN.search(line):
                    hits.append(f"{f}:{i}")
    assert not hits, hits


def test_repo_files_have_no_forbidden_words():
    for name in ("install.py", "README.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert not FORBIDDEN.search(text), name


def test_cli_dry_run(tmp_path, capsys):
    t = tmp_path / "t"
    rc = install.main(["--dry-run", "--target", str(t), "--backup-root", str(tmp_path / "b")])
    assert rc == 0 and not t.exists()
    out = capsys.readouterr().out
    assert out.count("would copy") == len(SKILLS)


@pytest.mark.parametrize("where", ["same", "parent", "inside"])
def test_target_overlapping_source_refused(src, tmp_path, where):
    t = {"same": src, "parent": src.parent, "inside": src / "medfig-render"}[where]
    before = snapshot(src)
    with pytest.raises(SystemExit, match="overlaps"):
        install.Installer([t], tmp_path / "b", src_root=src)
    assert snapshot(src) == before


def test_cli_refuses_repo_root_target(tmp_path):
    with pytest.raises(SystemExit, match="overlaps"):
        install.main(["--dry-run", "--target", str(ROOT), "--backup-root", str(tmp_path / "b")])
