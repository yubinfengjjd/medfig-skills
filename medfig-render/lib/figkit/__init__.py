"""figkit: de-projectized figure toolkit (config, io, provenance, style, qa, export, layout, panel).

All paths come from the project's ``figkit.toml`` via ``figkit.config.load(path)``.
"""
from . import config, provenance, io, qa, style, export, layout, panel  # noqa: F401

__all__ = ["config", "provenance", "io", "qa", "style", "export", "layout", "panel"]
