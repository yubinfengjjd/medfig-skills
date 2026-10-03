"""The single export gate: final size -> QA -> scipilot export_figure + check_figure -> provenance.

Any QA issue or check_figure FAIL raises RuntimeError. Never wrap save() in try/except.
"""
import importlib.util
from pathlib import Path

from . import config, panel, qa

# Test patch points: when set (non-None) they override the tools loaded from cfg.scipilot_scripts.
audit_layout = None
export_figure = None
check_figure = None

# Real scipilot tools, cached per resolved scripts dir so a later config pointing elsewhere re-imports.
_TOOLS = {}


def _import_file(tag, path):
    spec = importlib.util.spec_from_file_location(f"_figkit_scipilot_{tag}_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_tools(cfg):
    """Validate cfg's scipilot dir (always) and return its tools, importing once per resolved path."""
    d = Path(cfg.ensure_scipilot()).resolve()
    key = str(d)
    if key not in _TOOLS:
        tag = len(_TOOLS)
        _TOOLS[key] = {
            "audit_layout": _import_file(tag, d / "visual_qa.py").audit_layout,
            "export_figure": _import_file(tag, d / "export_figure.py").export_figure,
            "check_figure": _import_file(tag, d / "check_figure.py").check_figure,
        }
    t = _TOOLS[key]
    return (audit_layout or t["audit_layout"], export_figure or t["export_figure"],
            check_figure or t["check_figure"])


def _check_panels(fig, name, panels):
    """S4 gate: a figure with data axes must mark its panels, or opt out as a single-panel figure."""
    if panels not in ("marked", "none"):
        raise ValueError(f"{name}: panels must be 'marked' or 'none', got {panels!r}")
    data = [ax for _l, ax in qa._grid_axes(fig)]
    groups = {id(min(qa.twin_group(ax), key=fig.axes.index)) for ax in data}  # twinx/twiny = one panel
    marked = panel.marked_panels(fig)
    if panels == "none":
        if marked:
            raise RuntimeError(f"{name}: panels='none' but {len(marked)} axes are marked with mark_panel")
        if len(groups) > 1:
            raise RuntimeError(f"{name}: panels='none' is only for single-panel figures; found {len(groups)} "
                               "independent data axes -- mark each panel with panel.mark_panel (twinx/twiny "
                               "siblings count as one panel)")
    elif data and not marked:
        raise RuntimeError(f"{name}: S4 FAIL -- {len(data)} data axes but none marked with panel.mark_panel "
                           "(single-panel figure: export.save(..., panels='none'))")


def save(fig, name, prov, kind="main", size=None, cfg=None, dpi=600, panels="marked"):
    """Export ``fig`` to <out_dir>/figures/<kind>/<name>.{pdf,svg,png} (+ grayscale) and source.json,
    plus each ``panel.mark_panel``-ed axes to <out_dir>/panels/<name>/<name>_<id>.{pdf,svg}.

    S4: data axes but no marked panel raises RuntimeError before any file is written. ``panels="none"``
    is the opt-out for single-panel figures only: the composite itself is exported as ``<name>_a``.

    The returned ``files`` / ``panels`` hold absolute paths; source.json records them relative to
    ``cfg.project_root`` (``provenance.portable``)."""
    cfg = config.resolve_cfg(cfg)
    if prov.cfg is None:
        prov.bind(cfg)
    _audit, _export, _check = _load_tools(cfg)
    if size is not None:  # resize first so QA inspects exactly the geometry that is exported
        fig.set_size_inches(*size)
    issues = _audit(fig)
    fails = [m for s, m in issues if s == "FAIL"]
    res = {"audit_layout": issues, "geometry": qa.geometry_audit(fig), "banned": qa.banned_words(fig, cfg),
           "min_font": qa.min_font(fig), "true_minus": qa.true_minus(fig),
           "whitespace": qa.whitespace_audit(fig), "text_only": qa.text_only_panel(fig),
           "colour": qa.colour_audit(fig), "palette": qa.palette_clash(fig, cfg=cfg),
           "figure_text": qa.figure_text_audit(fig, cfg=cfg), "bar_baseline": qa.bar_baseline_audit(fig)}
    prov.set("qa", res)
    bad = {k: v for k, v in res.items() if k != "audit_layout" and v}
    if fails or bad:
        raise RuntimeError(f"{name}: QA failed\n audit_layout FAIL={fails}\n"
                           + "\n".join(f" {k}={v}" for k, v in bad.items()))
    _check_panels(fig, name, panels)
    out =Path(cfg.out_dir) / "figures" / kind
    files = _export(fig, str(out / name), formats=["pdf", "svg", "png"],
                   size_inches=None, dpi=dpi, grayscale_preview=True)
    checks = {}
    for f in files:
        if f.endswith((".pdf", ".svg")) or (f.endswith(".png") and "grayscale" not in f):
            cf_issues, _info = _check(f, min_dpi=300)
            checks[Path(f).name] = cf_issues
            if any(s == "FAIL" for s, _ in cf_issues):
                for w in files:  # never leave a failed export on disk
                    Path(w).unlink(missing_ok=True)
                raise RuntimeError(f"{name}: check_figure FAIL on {f}: {cf_issues}")
    res["check_figure"] = checks
    # S4: every marked panel also standalone (PDF + SVG, composite size, no panel label)
    try:
        recs = (panel.export_whole(fig, name, cfg.out_dir, dpi=dpi) if panels == "none"
                else panel.export_panels(fig, name, cfg.out_dir, dpi=dpi))
    except Exception:
        for w in files:  # no composite without its panels and source.json
            Path(w).unlink(missing_ok=True)
        raise
    # source.json gets portable paths (relative to project_root); the return value keeps absolute ones
    prov.set("panels", [dict(r, pdf=prov.portable(r["pdf"]), svg=prov.portable(r["svg"])) for r in recs])
    prov.set("files", [prov.portable(f) for f in files])
    return {"files": files, "qa": res, "panels": recs, "source": prov.write(out)}
