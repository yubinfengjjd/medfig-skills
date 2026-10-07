"""The single export gate: final size -> QA -> scipilot export_figure + check_figure -> provenance.

Any QA issue or check_figure FAIL raises RuntimeError. Never wrap save() in try/except.
"""
import contextlib
import importlib.util
import re
from pathlib import Path

import matplotlib as mpl
from PIL import Image as PILImage

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


@contextlib.contextmanager
def pdf_rgb_images():
    """Write every raster image in a PDF as 8-bit DeviceRGB (PNG predictor), never as an indexed palette.

    matplotlib's PDF backend stores images with <= 256 colours as /Indexed with 1/2/4/8 bits per pixel
    (heatmaps, masks, confusion matrices). Viewers decode that correctly, but Adobe Illustrator mis-reads
    those palette images when a PDF is embedded: the cells turn near-white and white labels on them vanish.
    This replaces ``PdfFile._writeImg`` for the duration of the block with the backend's own RGB path."""
    from matplotlib.backends import backend_pdf as bp
    orig = getattr(bp.PdfFile, "_writeImg", None)
    if orig is None:
        raise RuntimeError("matplotlib PdfFile._writeImg not found; pdf_rgb_images needs updating for this "
                           f"matplotlib {mpl.__version__}")

    def _write_img_rgb(self, data, id, smask=None):
        height, width, channels = data.shape
        obj = {"Type": bp.Name("XObject"), "Subtype": bp.Name("Image"), "Width": width, "Height": height,
               "ColorSpace": bp.Name({1: "DeviceGray", 3: "DeviceRGB"}[channels]), "BitsPerComponent": 8}
        if smask:
            obj["SMask"] = smask
        png = None
        if mpl.rcParams["pdf.compression"]:
            img = PILImage.fromarray(data.squeeze(axis=-1) if channels == 1 else data)
            png_data, _, _ = self._writePng(img)
            png = {"Predictor": 10, "Colors": channels, "Columns": width}
        self.beginStream(id, self.reserveObject("length of image stream"), obj, png=png)
        self.currentstream.write(png_data if png else data.tobytes())
        self.endStream()

    bp.PdfFile._writeImg = _write_img_rgb
    try:
        yield
    finally:
        bp.PdfFile._writeImg = orig


@contextlib.contextmanager
def pdf_plain_font_names():
    """Write embedded fonts under their real PostScript name (``ArialMT``), without the subset tag.

    matplotlib names every subsetted TrueType font ``ABCDEF+ArialMT``. Adobe Illustrator opens such a PDF
    with the tagged name as a missing font (the installed Arial is not matched), so every text object has to
    be re-mapped by hand. The glyph subset is still embedded; only the /BaseFont and /FontName change.
    This replaces ``PdfFile._get_subsetted_psname`` for the duration of the block."""
    from matplotlib.backends import backend_pdf as bp
    orig = getattr(bp.PdfFile, "_get_subsetted_psname", None)
    if orig is None:
        raise RuntimeError("matplotlib PdfFile._get_subsetted_psname not found; pdf_plain_font_names needs "
                           f"updating for this matplotlib {mpl.__version__}")
    bp.PdfFile._get_subsetted_psname = lambda self, ps_name, charmap: ps_name
    try:
        yield
    finally:
        bp.PdfFile._get_subsetted_psname = orig


@contextlib.contextmanager
def pdf_illustrator_safe():
    """Both Illustrator workarounds: RGB-only images and untagged font names."""
    with pdf_rgb_images(), pdf_plain_font_names():
        yield


_SUBSET_TAG = re.compile(rb"/(?:BaseFont|FontName)\s*/([A-Z]{6}\+[^\s/<>\[\]()]+)")


def pdf_font_issues(path):
    """Embedded fonts whose name carries a subset tag (``ABCDEF+ArialMT``): Illustrator reports them missing."""
    with open(path, "rb") as fh:
        data = fh.read()
    if not data.startswith(b"%PDF-"):
        return []  # not a PDF (test stand-in); check_figure owns validity
    names = sorted({m.group(1).decode("latin-1") for m in _SUBSET_TAG.finditer(data)})
    out = [f"font {n}: subset-tagged name (Illustrator shows it as a missing font)" for n in names]
    fallback = (b"DejaVu", b"cmr", b"cmmi", b"cmsy", b"cmex", b"STIX")
    fonts = {m.group(1) for m in _BASEFONT.finditer(data)}
    stray = sorted(f.decode("latin-1") for f in fonts if f.startswith(fallback))
    if len(stray) == len(fonts):
        stray = []  # the fallback IS the body font (no Arial on this machine): nothing mixed in
    out += [f"font {n}: fallback font embedded next to the body font (mathtext or a missing glyph); "
            "Illustrator reports it missing -- keep math in the body font (style.RC mathtext.*)" for n in stray]
    return out


_BASEFONT = re.compile(rb"/BaseFont\s*/(?:[A-Z]{6}\+)?([^\s/<>\[\]()]+)")


def pdf_image_issues(path):
    """Raster images in a PDF that are stored as an indexed palette or below 8 bits per component."""
    try:
        from pypdf import PdfReader
        from pypdf.generic import IndirectObject
    except ImportError:  # pypdf is pinned in requirements.txt; without it the writer patch still applies
        return []

    def r(o):
        return o.get_object() if isinstance(o, IndirectObject) else o

    out, seen = [], set()

    def walk(res, where):
        xobjs = r(r(res).get("/XObject")) if res is not None else None
        for key, v in (xobjs or {}).items():
            x = r(v)
            if id(x) in seen:
                continue
            seen.add(id(x))
            if x.get("/Subtype") == "/Image":
                cs = r(x.get("/ColorSpace"))
                cs0 = str(r(cs[0])) if isinstance(cs, list) else str(cs)
                bpc = int(x.get("/BitsPerComponent", 8))
                if cs0 == "/Indexed" or bpc < 8:
                    out.append(f"{where}{key}: {cs0} {bpc}-bit image (Illustrator mis-renders palette images)")
            elif "/Resources" in x:
                walk(x["/Resources"], f"{where}{key}/")

    with open(path, "rb") as fh:
        if fh.read(5) != b"%PDF-":
            return []  # not a PDF (test stand-in); check_figure owns validity
    try:
        pages = PdfReader(str(path)).pages
        for i, page in enumerate(pages):
            walk(page.get("/Resources"), f"page {i + 1} ")
    except Exception as e:  # damaged PDF: report, do not crash the gate
        return [f"PDF not readable for the image check ({type(e).__name__}: {e})"]
    return out


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
           "figure_text": qa.figure_text_audit(fig, cfg=cfg), "bar_baseline": qa.bar_baseline_audit(fig),
           "facet": qa.facet_balance(fig) + qa.repeated_legend(fig)}
    prov.set("qa", res)
    bad = {k: v for k, v in res.items() if k != "audit_layout" and v}
    if fails or bad:
        raise RuntimeError(f"{name}: QA failed\n audit_layout FAIL={fails}\n"
                           + "\n".join(f" {k}={v}" for k, v in bad.items()))
    _check_panels(fig, name, panels)
    out =Path(cfg.out_dir) / "figures" / kind
    with pdf_illustrator_safe():  # no palette images, no subset-tagged font names (both break Illustrator)
        files = _export(fig, str(out / name), formats=["pdf", "svg", "png"],
                        size_inches=None, dpi=dpi, grayscale_preview=True)
    checks = {}
    for f in files:
        if f.endswith((".pdf", ".svg")) or (f.endswith(".png") and "grayscale" not in f):
            cf_issues, _info = _check(f, min_dpi=300)
            if f.endswith(".pdf") and Path(f).is_file():  # missing files are check_figure's to report
                cf_issues = list(cf_issues) + [("FAIL", m) for m in pdf_image_issues(f) + pdf_font_issues(f)]
            checks[Path(f).name] = cf_issues
            if any(s == "FAIL" for s, _ in cf_issues):
                for w in files:  # never leave a failed export on disk
                    Path(w).unlink(missing_ok=True)
                raise RuntimeError(f"{name}: check_figure FAIL on {f}: {cf_issues}")
    res["check_figure"] = checks
    # S4: every marked panel also standalone (PDF + SVG, composite size, no panel label)
    try:
        with pdf_illustrator_safe():
            recs = (panel.export_whole(fig, name, cfg.out_dir, dpi=dpi) if panels == "none"
                    else panel.export_panels(fig, name, cfg.out_dir, dpi=dpi))
        bad_img = [f"{r['pdf']}: {m}" for r in recs if Path(r["pdf"]).is_file()
                   for m in pdf_image_issues(r["pdf"]) + pdf_font_issues(r["pdf"])]
        if bad_img:
            raise RuntimeError(f"{name}: standalone panel PDF not Illustrator-safe: {bad_img}")
    except Exception:
        for w in files:  # no composite without its panels and source.json
            Path(w).unlink(missing_ok=True)
        raise
    # source.json gets portable paths (relative to project_root); the return value keeps absolute ones
    prov.set("panels", [dict(r, pdf=prov.portable(r["pdf"]), svg=prov.portable(r["svg"])) for r in recs])
    prov.set("files", [prov.portable(f) for f in files])
    return {"files": files, "qa": res, "panels": recs, "source": prov.write(out)}
