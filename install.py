#!/usr/bin/env python3
"""Install the seven medfig-* skills and their dependency skill scipilot-medimg-figure-skill (stdlib only).

Copies ONLY medfig-suite, medfig-plan, medfig-render, medfig-orchestrate, medfig-outline, medfig-schematic,
medfig-illustrator and
scipilot-medimg-figure-skill (medfig-render calls its scripts/).
Existing installs are moved to a timestamped backup before being replaced;
nothing is ever deleted. After copying, every file is SHA-256 verified
against the source and a `.medfig_install.json` stamp is written.

Usage:
    python install.py [--target DIR ...] [--dry-run] [--update]
    python install.py --uninstall [--target DIR ...]
    python install.py --verify [--target DIR ...]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parent
SKILLS = ("medfig-suite", "medfig-plan", "medfig-render", "medfig-orchestrate", "medfig-outline", "medfig-schematic",
          "medfig-illustrator", "scipilot-medimg-figure-skill")
STAMP = ".medfig_install.json"

EXCLUDED_DIR_NAMES = {"__pycache__", ".pytest_cache", ".git"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
# Generated dirs: any `out` / `data` dir below an `examples` dir.
EXAMPLE_GENERATED = {"out", "data"}


def default_targets() -> list[Path]:
    home = Path.home()
    return [home / ".claude" / "skills", home / ".codex" / "skills"]


def is_excluded(rel_parts: tuple[str, ...]) -> bool:
    """True if a path (relative to a skill dir) must not be installed."""
    if rel_parts and rel_parts[-1] == STAMP:
        return True
    for i, part in enumerate(rel_parts):
        if part in EXCLUDED_DIR_NAMES:
            return True
        if part in EXAMPLE_GENERATED and "examples" in rel_parts[:i] and i < len(rel_parts) - 1:
            return True
    return Path(rel_parts[-1]).suffix in EXCLUDED_SUFFIXES if rel_parts else False


def iter_files(skill_dir: Path) -> list[str]:
    """Sorted posix relative paths of all non-excluded files in skill_dir."""
    out = []
    for f in skill_dir.rglob("*"):
        if not f.is_file():
            continue
        rel = f.relative_to(skill_dir)
        if is_excluded(rel.parts):
            continue
        out.append(rel.as_posix())
    return sorted(out)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest(skill_dir: Path) -> dict[str, str]:
    return {rel: sha256_file(skill_dir / rel) for rel in iter_files(skill_dir)}


def manifest_hash(man: dict[str, str]) -> str:
    h = hashlib.sha256()
    for rel in sorted(man):
        h.update(f"{rel}\t{man[rel]}\n".encode("utf-8"))
    return h.hexdigest()


def verify(src_skill: Path, dest_skill: Path) -> list[str]:
    """Return a list of problems (empty == installed tree matches source)."""
    if not dest_skill.is_dir():
        return [f"missing install dir {dest_skill}"]
    src_man, dst_man = manifest(src_skill), manifest(dest_skill)
    problems = []
    for rel in sorted(set(src_man) | set(dst_man)):
        if rel not in dst_man:
            problems.append(f"missing: {rel}")
        elif rel not in src_man:
            problems.append(f"unexpected: {rel}")
        elif src_man[rel] != dst_man[rel]:
            problems.append(f"hash mismatch: {rel}")
    return problems


def git_version(root: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    v = r.stdout.strip()
    return v if r.returncode == 0 and v else "unknown"


def read_stamp(dest_skill: Path) -> dict | None:
    try:
        return json.loads((dest_skill / STAMP).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def target_label(target: Path) -> str:
    """e.g. ~/.claude/skills -> 'claude-skills'."""
    parts = [p.lstrip(".") for p in (target.parent.name, target.name) if p]
    return "-".join(p for p in parts if p) or "target"


class Installer:
    def __init__(self, targets, backup_root: Path, src_root: Path = SRC_ROOT,
                 dry_run: bool = False, log=print):
        self.src_root = src_root
        self.targets = [Path(t).expanduser().resolve() for t in targets]
        src = Path(src_root).resolve()
        for t in self.targets:
            # installing into (or above) the source tree would move the source skills into the backup
            if t == src or src.is_relative_to(t) or t.is_relative_to(src):
                raise SystemExit(f"ERROR: target {t} is the source repo {src} or overlaps it; "
                                 "pass a skills root outside the repo (e.g. ~/.claude/skills)")
        self.dry_run = dry_run
        self.log = log
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        base = Path(backup_root).expanduser() / f"medfig_{ts}"
        cand, n = base, 1
        while cand.exists():
            cand, n = base.with_name(f"{base.name}_{n}"), n + 1
        self.backup_dir = cand
        self.labels = {}
        for t in self.targets:
            lab, n = target_label(t), 1
            while lab in self.labels.values():
                lab, n = f"{target_label(t)}-{n}", n + 1
            self.labels[t] = lab
        self.failures: list[str] = []
        self.backups: list[Path] = []

    # -- helpers ---------------------------------------------------------
    def _src(self, skill: str) -> Path:
        d = self.src_root / skill
        if not (d / "SKILL.md").is_file():
            raise SystemExit(f"ERROR: source skill not found: {d}")
        return d

    def _backup(self, target: Path, skill: str) -> Path:
        dest = self.backup_dir / self.labels[target] / skill
        if self.dry_run:
            self.log(f"  [dry-run] would back up {target / skill} -> {dest}")
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(target / skill), str(dest))
            self.log(f"  backup: {target / skill} -> {dest}")
        self.backups.append(dest)
        return dest

    # -- actions ---------------------------------------------------------
    def install(self, update: bool = False) -> int:
        version = git_version(self.src_root)
        self.log(f"source: {self.src_root} (version {version})")
        self.log(f"targets: {', '.join(str(t) for t in self.targets)}")
        self.log(f"backup dir (if needed): {self.backup_dir}")
        for target in self.targets:
            self.log(f"target {target}:")
            for skill in SKILLS:
                self._install_one(target, skill, version, update)
        return self._finish()

    def _install_one(self, target: Path, skill: str, version: str, update: bool):
        src = self._src(skill)
        src_man = manifest(src)
        src_hash = manifest_hash(src_man)
        dest = target / skill
        if dest.exists():
            if update:
                stamp = read_stamp(dest)
                if (stamp and stamp.get("manifest_hash") == src_hash
                        and not verify(src, dest)):
                    self.log(f"  {skill}: up to date ({src_hash[:12]}), skipped")
                    return
            self._backup(target, skill)
        if self.dry_run:
            self.log(f"  [dry-run] would copy {src} -> {dest} ({len(src_man)} files)")
            return
        for rel in src_man:
            out = dest / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src / rel, out)
        problems = verify(src, dest)
        if problems:
            self.failures += [f"{dest}: {p}" for p in problems]
            self.log(f"  {skill}: VERIFY FAILED ({len(problems)} problems)")
            return
        stamp = {
            "skill": skill,
            "version": version,
            "timestamp": _dt.datetime.now().isoformat(timespec="seconds"),
            "file_count": len(src_man),
            "manifest_hash": src_hash,
        }
        (dest / STAMP).write_text(json.dumps(stamp, indent=2) + "\n", encoding="utf-8")
        self.log(f"  {skill}: installed {len(src_man)} files, sha256 verified ({src_hash[:12]})")

    def uninstall(self) -> int:
        self.log(f"backup dir: {self.backup_dir}")
        for target in self.targets:
            self.log(f"target {target}:")
            for skill in SKILLS:
                if (target / skill).exists():
                    self._backup(target, skill)
                else:
                    self.log(f"  {skill}: not installed")
        return self._finish()

    def verify_all(self) -> int:
        for target in self.targets:
            self.log(f"target {target}:")
            for skill in SKILLS:
                problems = verify(self._src(skill), target / skill)
                if problems:
                    self.failures += [f"{target / skill}: {p}" for p in problems]
                    self.log(f"  {skill}: FAILED ({len(problems)} problems)")
                else:
                    self.log(f"  {skill}: ok")
        return self._finish()

    def _finish(self) -> int:
        if self.backups:
            verb = "planned" if self.dry_run else "created"
            self.log(f"backups {verb}: {len(self.backups)} under {self.backup_dir}")
        if self.failures:
            self.log("VERIFICATION FAILURES:")
            for f in self.failures:
                self.log(f"  {f}")
            return 1
        if self.dry_run:
            self.log("dry-run: nothing changed")
        return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Install the medfig-* skills.")
    p.add_argument("--target", action="append", type=Path,
                   help="skill root to install into (repeatable; default "
                        "~/.claude/skills and ~/.codex/skills)")
    p.add_argument("--backup-root", type=Path, default=Path.home() / "skill_backups",
                   help="where backups go (default ~/skill_backups)")
    p.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--update", action="store_true",
                      help="only reinstall skills whose manifest hash differs")
    mode.add_argument("--uninstall", action="store_true",
                      help="move installed medfig-* dirs to backup (never deletes)")
    mode.add_argument("--verify", action="store_true",
                      help="only verify installed trees against the source")
    a = p.parse_args(argv)
    inst = Installer(a.target or default_targets(), a.backup_root, dry_run=a.dry_run)
    if a.verify:
        return inst.verify_all()
    if a.uninstall:
        return inst.uninstall()
    return inst.install(update=a.update)


if __name__ == "__main__":
    sys.exit(main())
