"""Read-only loaders. Every path is checked against ``data_root`` (or the external whitelist)
before anything is opened, and every read registers path (portable, see ``provenance.portable``), SHA-256 and row count."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


class Reader:
    def __init__(self, prov, cfg=None):
        self.prov = prov
        self.cfg = config.resolve_cfg(cfg)
        if prov.cfg is None:
            prov.bind(self.cfg)  # input paths are recorded relative to project_root

    def path(self, rel):
        """Resolve ``rel`` under data_root; raise ValueError on escape (nothing is read)."""
        root = self.cfg.data_root
        p = Path(str(rel)).expanduser()
        p = (p if p.is_absolute() else root / p).resolve()
        if root.resolve() not in p.parents:
            raise ValueError(f"path escapes data_root {root}: {rel}")
        return p

    def _reg(self, p, rows):
        self.prov.add_input(p, sha256(p), rows)

    def csv(self, rel, **kw):
        p = self.path(rel); df = pd.read_csv(p, **kw)
        self._reg(p, len(df)); return df

    def parquet(self, rel, columns=None):
        p = self.path(rel); df = pd.read_parquet(p, columns=columns)
        self._reg(p, len(df)); return df

    def npz(self, rel):
        """rows = number of arrays in the archive."""
        p = self.path(rel); z = np.load(p, allow_pickle=False)
        self._reg(p, len(z.files)); return z

    def json(self, rel, rows=None):
        """rows: None -> 1 (one document) or a callable obj -> int."""
        p = self.path(rel); obj = json.loads(p.read_text(encoding="utf-8"))
        self._reg(p, 1 if rows is None else int(rows(obj))); return obj

    def text(self, rel):
        """Plain text file; rows = number of lines."""
        p = self.path(rel); txt = p.read_text(encoding="utf-8")
        self._reg(p, len(txt.splitlines())); return txt

    def ledger(self, file, key):
        """JSONL records under data_root/ledger/ whose 'key' equals ``key``; blank lines skipped."""
        p = self.path(Path("ledger") / file)
        with open(p, encoding="utf-8") as f:
            recs = [r for r in (json.loads(s) for s in f if s.strip()) if r.get("key") == key]
        self._reg(p, len(recs)); return recs

    def external(self, path):
        """Read .csv/.json/.md/.txt from a whitelisted ``external_dirs`` entry only.

        Relative paths resolve against the first whitelisted dir."""
        dirs = [Path(d).resolve() for d in self.cfg.external_dirs]
        if not dirs:
            raise ValueError(f"external read refused (no external_dirs whitelisted): {path}")
        p = Path(str(path)).expanduser()
        p = (p if p.is_absolute() else dirs[0] / p).resolve()
        if not any(d in p.parents for d in dirs):
            raise ValueError(f"external path outside whitelisted external_dirs {dirs}: {path}")
        suffix = p.suffix.lower()
        if suffix == ".csv":
            obj = pd.read_csv(p); rows = len(obj)
        elif suffix == ".json":
            obj = json.loads(p.read_text(encoding="utf-8"))
            rows = len(obj) if isinstance(obj, (list, dict)) else 1
        elif suffix in (".md", ".txt"):
            obj = p.read_text(encoding="utf-8"); rows = len(obj.splitlines())
        else:
            raise ValueError(f"unsupported external file type: {p.suffix}")
        self._reg(p, rows); return obj
