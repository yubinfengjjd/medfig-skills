"""Project configuration read from ``figkit.toml``; no hard-coded paths anywhere in figkit.

Keys (relative paths resolve against the directory holding the toml, then ``project_root``):
  project_root (default "."), data_root (required, read-only), out_dir (default "out"),
  external_dirs (whitelist, default []), journal (default "nature"), theme ("default" | "soft"),
  scipilot_scripts (default DEFAULT_SCIPILOT), [palettes.cohort.*], [palettes.class.*],
  [qa] banned_extra (words added to qa.BANNED) / banned_allow (default words lifted for this project) /
  palette_min_delta_e (CIEDE2000 floor between different data colours in one axes, default qa.PALETTE_MIN_DE) /
  forbidden_patterns (case-sensitive regexes for internal codes that must not appear in figures or tables) /
  caveat_allow (keys of qa.FIGURE_CAVEATS this project may show inside figures).
"""
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib as _toml  # Python >= 3.11
except ModuleNotFoundError:  # pragma: no cover - depends on interpreter
    try:
        import tomli as _toml
    except ModuleNotFoundError:
        _toml = None

DEFAULT_SCIPILOT = "~/.claude/skills/scipilot-medimg-figure-skill/scripts"
_ACTIVE = None


@dataclass
class Config:
    source: Path
    project_root: Path
    data_root: Path
    out_dir: Path
    external_dirs: list = field(default_factory=list)
    journal: str = "nature"
    theme: str = "default"
    palettes: dict = field(default_factory=lambda: {"cohort": {}, "class": {}})
    scipilot_scripts: Path = None
    banned_extra: list = field(default_factory=list)
    banned_allow: list = field(default_factory=list)
    palette_min_delta_e: float = None
    forbidden_patterns: list = field(default_factory=list)
    caveat_allow: list = field(default_factory=list)

    def ensure_scipilot(self):
        """Put the scipilot scripts dir on sys.path; raise a clear error if it is not installed."""
        d = self.scipilot_scripts
        if d is None or not (Path(d) / "setup_style.py").is_file():
            raise FileNotFoundError(
                f"scipilot-medimg-figure-skill scripts not found at {d}. "
                "Please install the scipilot-medimg-figure-skill skill (its scripts/ folder must contain "
                "setup_style.py, export_figure.py, check_figure.py, visual_qa.py), or set "
                f"'scipilot_scripts' in {self.source}.")
        s = str(d)
        if s not in sys.path:
            sys.path.insert(0, s)
        return Path(d)


def _resolve(base, value):
    p = Path(str(value)).expanduser()
    return (p if p.is_absolute() else Path(base) / p).resolve()


def _palettes(raw, source):
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"'palettes' in {source} must be a table with 'cohort' / 'class' sub-tables")
    out = {"cohort": {}, "class": {}}
    for kind, table in raw.items():
        if not isinstance(table, dict) or not all(isinstance(v, dict) for v in table.values()):
            raise ValueError(f"'palettes.{kind}' in {source} must map names to tables (color, marker, ...)")
        out[kind] = {k: dict(v) for k, v in table.items()}
    return out


THEMES = ("default", "soft")


def _theme(v, source):
    """``theme``: "default" (house style) or "soft" (light tint fills + saturated same-hue edges)."""
    if v not in THEMES:
        raise ValueError(f"theme in {source} must be one of {THEMES}, got {v!r}")
    return v


def _qa_words(raw, source):
    """[qa] banned_extra / banned_allow: lists of strings; banned_allow may only name default words."""
    from .qa import BANNED
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"'qa' in {source} must be a table")
    keys = {"banned_extra", "banned_allow", "palette_min_delta_e", "forbidden_patterns", "caveat_allow"}
    unknown = set(raw) - keys
    if unknown:
        raise ValueError(f"[qa] in {source}: unknown keys {sorted(unknown)} (use {' / '.join(sorted(keys))})")
    out = {}
    for key in ("banned_extra", "banned_allow", "forbidden_patterns", "caveat_allow"):
        v = raw.get(key, [])
        if isinstance(v, str) or not isinstance(v, list) or not all(isinstance(w, str) and w.strip() for w in v):
            raise ValueError(f"[qa] {key} in {source} must be a list of non-empty strings")
        out[key] = [w.strip() for w in v]
    defaults = {w.lower() for w in BANNED}
    bad = [w for w in out["banned_allow"] if w.lower() not in defaults]
    if bad:
        raise ValueError(f"[qa] banned_allow in {source}: {bad} not in the default list {BANNED}")
    for pat in out["forbidden_patterns"]:
        try:
            re.compile(pat)
        except re.error as e:
            raise ValueError(f"[qa] forbidden_patterns in {source}: {pat!r} is not a valid regular expression ({e})")
    from .qa import DEV_HISTORY, FIGURE_CAVEATS
    known = {k.lower() for k in FIGURE_CAVEATS} | {k.lower() for k in DEV_HISTORY}
    bad = [w for w in out["caveat_allow"] if w.lower() not in known]
    if bad:
        raise ValueError(f"[qa] caveat_allow in {source}: {bad} not in the default caveat / development-history "
                         f"lists {sorted(FIGURE_CAVEATS) + sorted(DEV_HISTORY)}")
    de = raw.get("palette_min_delta_e")
    if de is not None and (isinstance(de, bool) or not isinstance(de, (int, float)) or not 0 <= de < 100):
        raise ValueError(f"[qa] palette_min_delta_e in {source} must be a number in [0, 100)")
    out["palette_min_delta_e"] = None if de is None else float(de)
    return out


def load(path):
    """Read ``figkit.toml`` and return a :class:`Config`; also makes it the active config."""
    if _toml is None:
        raise ImportError("figkit.config needs Python >= 3.11 (tomllib) or the 'tomli' package")
    src = Path(path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"figkit config not found: {src}")
    with open(src, "rb") as f:
        raw = _toml.load(f)
    if "data_root" not in raw:
        raise ValueError(f"{src}: required key 'data_root' is missing")
    root = _resolve(src.parent, raw.get("project_root", "."))
    ext = raw.get("external_dirs", [])
    if isinstance(ext, str) or not isinstance(ext, list):
        raise ValueError(f"{src}: 'external_dirs' must be a list of paths")
    cfg = Config(
        source=src,
        project_root=root,
        data_root=_resolve(root, raw["data_root"]),
        out_dir=_resolve(root, raw.get("out_dir", "out")),
        external_dirs=[_resolve(root, d) for d in ext],
        journal=str(raw.get("journal", "nature")),
        theme=_theme(raw.get("theme", "default"), src),
        palettes=_palettes(raw.get("palettes"), src),
        scipilot_scripts=_resolve(root, raw.get("scipilot_scripts", DEFAULT_SCIPILOT)),
        **_qa_words(raw.get("qa"), src),
    )
    use(cfg)
    return cfg


def use(cfg):
    """Set (or clear with None) the active config used when a cfg argument is omitted."""
    global _ACTIVE
    _ACTIVE = cfg
    return cfg


def active():
    if _ACTIVE is None:
        raise RuntimeError("no active figkit config: call figkit.config.load('<project>/figkit.toml') first")
    return _ACTIVE


def resolve_cfg(cfg=None):
    return active() if cfg is None else cfg
