"""Provenance record written next to every exported figure as ``<name>.source.json``.

Paths are portable: never absolute, never the user's home. A path inside ``cfg.project_root`` is
recorded relative to it in POSIX form (``data/scores.csv``); a path in a whitelisted external dir
outside the project is ``external:<dir name>/<relpath>``; a data_root / out_dir outside the project
gives ``data:<relpath>`` / ``out:<relpath>``. The top-level ``root`` field is the project_root's
directory name (a tag, not a path). SHA-256 + rows remain the identity of an input.
"""
import json
import time
from pathlib import Path

import numpy as np


def _default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, Path):
        return str(o)
    if isinstance(o, (set, frozenset, tuple)):
        return list(o)
    return str(o)


def _under(p, base):
    try:
        return Path(p).relative_to(base).as_posix()
    except ValueError:
        return None


def external_keys(cfg):
    """{resolved external dir: key}; key = dir name, suffixed ``#<i>`` when names collide."""
    dirs = [Path(d).resolve() for d in cfg.external_dirs]
    names = [d.name for d in dirs]
    return {d: (n if names.count(n) == 1 else f"{n}#{i}") for i, (d, n) in enumerate(zip(dirs, names))}


def portable(path, cfg):
    """Portable form of ``path`` for provenance (see module docstring); relative input is kept as is."""
    p = Path(str(path))
    if not p.is_absolute():
        return p.as_posix()
    p = p.resolve()
    rel = _under(p, Path(cfg.project_root).resolve())
    if rel is not None:
        return rel
    for d, key in external_keys(cfg).items():
        rel = _under(p, d)
        if rel is not None:
            return f"external:{key}/{rel}"
    for tag, base in (("data", cfg.data_root), ("out", cfg.out_dir)):
        rel = _under(p, Path(base).resolve())
        if rel is not None:
            return f"{tag}:{rel}"
    raise ValueError(f"provenance: {p.name} is outside project_root, data_root, out_dir and the "
                     "external whitelist; refusing to record an absolute path")


class Provenance:
    def __init__(self, name, cfg=None):
        self.name, self.inputs, self.transforms, self.values = name, [], [], {}
        self.definitions = {}
        self.cfg = None
        if cfg is not None:
            self.bind(cfg)

    def bind(self, cfg):
        """Attach the project config used to make paths portable (done by io.Reader / export.save)."""
        self.cfg = cfg
        return self

    @property
    def root(self):
        return None if self.cfg is None else Path(self.cfg.project_root).name

    def portable(self, path):
        p = Path(str(path))
        if self.cfg is None:
            if p.is_absolute():
                raise ValueError(f"provenance {self.name!r}: absolute path {p.name} needs a bound config "
                                 "(Provenance(name, cfg) or io.Reader(prov, cfg))")
            return p.as_posix()
        return portable(p, self.cfg)

    def add_input(self, path, sha256, rows):
        self.inputs.append({"path": self.portable(path), "sha256": sha256, "rows": int(rows)})

    def add_transform(self, text):
        self.transforms.append(str(text))

    def set(self, key, value):
        self.values[key] = value

    def define(self, key, text, source, **fields):
        """Record what a derived quantity or comparison condition IS, checked against code or receipts.

        text: one-sentence definition; source: where it was verified (e.g. "wave2.py:189-207" or a
        receipt key). Optional fields: fit_split, eval_split, grouping, scale, analysis. Downstream
        legend and writing steps read this instead of the free-text caption."""
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"provenance {self.name!r}: define({key!r}) needs text as a non-empty string")
        if not isinstance(source, str) or not source.strip():
            # str(None) 会得到 "None"，让未核验的定义看起来有出处（评审 2026-10-14）
            raise ValueError(f"provenance {self.name!r}: define({key!r}) needs source as a non-empty string "
                             "(code lines or a receipt key; None / False / 0 / 空列表 不接受)")
        allowed = {"fit_split", "eval_split", "grouping", "scale", "analysis"}
        extra = set(fields) - allowed
        if extra:
            raise ValueError(f"provenance {self.name!r}: define({key!r}) unknown fields {sorted(extra)}")
        from . import qa  # 局部导入：单独用 Provenance 时不拉起 matplotlib；定义文本与图注同一套禁用词闸门
        hits = qa.banned_in_text(text) + qa.dev_history_in_text(text)
        if hits:
            raise ValueError(f"provenance {self.name!r}: define({key!r}) text contains banned words {hits}")
        self.definitions[key] = {"text": text, "source": source, **fields}

    def write(self, out_dir):
        out = Path(out_dir) / f"{self.name}.source.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        doc = {"figure": self.name, "root": self.root, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
               "inputs": self.inputs, "transforms": self.transforms, "values": self.values}
        if self.definitions:
            doc["definitions"] = self.definitions
        out.write_text(json.dumps(doc, indent=2, default=_default, ensure_ascii=False), encoding="utf-8")
        return out
