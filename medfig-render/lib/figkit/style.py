"""Journal style on top of scipilot ``setup_style``; palettes come from ``figkit.toml``.

Fixes kept: body text >= 6 pt (inset ticks 5 pt), true minus (setup_style forces
``axes.unicode_minus=False``; we switch it back on and check the font has U+2212).
"""
import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.ft2font import FT2Font

from . import config

DOUBLE, SINGLE = 7.09, 3.46
MIN_FONT_PT = 6.0
INSET_TICK_PT = 5.0
# Okabe-Ito, saturated colours first (S3: data elements must be coloured). Black is kept last for
# auxiliary use only and is NOT part of the data colour cycle.
OKABE_ITO = ["#0072B2", "#D55E00", "#009E73", "#E69F00",
             "#CC79A7", "#56B4E9", "#F0E442", "#000000"]
DATA_CYCLE = [c for c in OKABE_ITO if c != "#000000"]
# auxiliary greys (S3: never for data): reference / diagonal lines, row bands, not-estimable hatching
GREY = "#9A9A9A"        # reference lines, diagonals, hatch edges
DARK_GREY = "#4D4D4D"   # zero lines, "absent" / "n/a" text
BAND = "#EDEDED"        # highlighted-row background band
NA_FILL = "#E6E6E6"     # not-estimable / absent cell fill (hatched)

RC = {"font.size": 6, "axes.labelsize": 6.5, "axes.titlesize": 6.5,
      "xtick.labelsize": 6, "ytick.labelsize": 6, "legend.fontsize": 6,
      "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
      "xtick.major.size": 2.5, "ytick.major.size": 2.5,
      "axes.spines.top": False, "axes.spines.right": False,
      "pdf.fonttype": 42, "svg.fonttype": "none",
      "axes.prop_cycle": mpl.cycler(color=DATA_CYCLE),
      "axes.unicode_minus": True}

# Soft theme (``theme = "soft"`` in figkit.toml; look after senlanke/figures4papers, re-derived here -- that
# repository has no licence, so no code is taken). Key colours: Okabe-Ito minus sky / yellow (their tints
# collide with the blue / orange tints) plus Tol-muted indigo; chosen so that every key colour AND its tint
# stay >= 12 ΔE00 from every other key colour and tint. Data artists use tint face + key edge, so S3 holds.
SOFT_KEYS = ["#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7", "#332288"]
SOFT_TINT = 0.55          # share of white mixed into the face colour
SOFT_HATCHES = ["", "////", "....", "\\\\\\\\", "xxxx", "oo"]  # optional greyscale redundancy (area fills)
# 2026-10-07 ruling (figures4papers look): one saturated emphasis colour for the proposed method, light
# controls, flat bars without edges / hatches, values on the bars, thin dark error bars, truncated value
# axes allowed only with a break mark (qa.bar_baseline_audit), 7 / 6.5 pt text (Nature range 5-7 pt).
SOFT_EMPHASIS = "#3775BA"
# light controls, distinct hues (pastels after figures4papers' palette, re-picked so that every pair is
# >= 12 ΔE00 apart and every one >= 33 from SOFT_EMPHASIS); order = assignment order
SOFT_CONTROLS = ["#F4EEAC", "#D9B9D4", "#DAA87C", "#CFE3CF", "#FBDFE2", "#C9DCEB"]
SOFT_SAT_MIN = 0.05       # soft theme: only near-neutral greys count as achromatic (pastels are colour)
SOFT_RC = {"font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7, "xtick.labelsize": 6.5,
           "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
           "axes.linewidth": 0.8, "xtick.major.width": 0.8, "ytick.major.width": 0.8,
           "xtick.major.size": 3.0, "ytick.major.size": 3.0, "lines.linewidth": 1.2,
           "patch.linewidth": 0.8, "hatch.linewidth": 0.6,
           "errorbar.capsize": 2.0, "legend.frameon": False, "text.usetex": False}
ORDINAL_MAX = 5           # single-hue ordinal levels that stay >= 12 ΔE00 apart
ORDINAL_SOFT = (0.72, -0.35)  # tint / shade ends for flat soft ordinal bars: 4 levels for every SOFT_KEYS hue,
#                              lightest level still >= 13 ΔE00 from white (visible without an edge)
CONTROL_MIN_DE = 4.0      # within a declared control group (style.mark_controls), soft theme only
ERR_COLOUR = DARK_GREY    # soft-theme error bars / break marks (auxiliary, exempt from S3)
_THEME = {"name": "default"}


def tint(c, w=SOFT_TINT):
    """``c`` mixed with ``w`` white: the soft-theme face colour (same hue, lighter)."""
    import numpy as np
    from matplotlib.colors import to_hex, to_rgb
    r = np.array(to_rgb(c))
    return to_hex(r + (1 - r) * w)


def soft_palette(n):
    """``n`` (<= 6) soft entries {face: tint, edge: key colour}; draw with ``edgecolor=edge`` (S3)."""
    if not 1 <= n <= len(SOFT_KEYS):
        raise ValueError(f"soft_palette: at most {len(SOFT_KEYS)} distinct methods, got {n}; "
                         "group methods or use small multiples")
    return [dict(face=tint(c), edge=c) for c in SOFT_KEYS[:n]]


def _mix(c, t):
    """t > 0: mix with t white (tint); t < 0: mix with -t black (shade)."""
    import numpy as np
    from matplotlib.colors import to_hex, to_rgb
    r = np.array(to_rgb(c))
    return to_hex(r + (1 - r) * t if t >= 0 else r * (1 + t))


def ordinal_gradient(c, n, lo=0.85, hi=-0.45, min_de=12.0):
    """``n`` levels of one hue, light -> dark, for ORDERED categories only (ablation completeness, dose,
    grade). The tint (``lo`` white) -> shade (``-hi`` black) path is sampled at equal CIEDE2000 arc length,
    so adjacent levels are evenly spaced and >= ``min_de`` apart (otherwise ValueError: fewer levels or a
    darker key colour). At most ``ORDINAL_MAX`` levels. Record it on the axes with ``mark_ordinal``."""
    if not 2 <= n <= ORDINAL_MAX:
        raise ValueError(f"ordinal_gradient: 2..{ORDINAL_MAX} levels, got {n} (adjacent levels must stay "
                         f">= {min_de:g} ΔE00 apart; bin the variable or use a sequential colormap)")
    import numpy as np
    path = [_mix(c, t) for t in np.linspace(lo, hi, 400)]
    arc = np.concatenate([[0.0], np.cumsum([delta_e(a, b) for a, b in zip(path, path[1:])])])
    out = [path[int(np.argmin(np.abs(arc - x)))] for x in np.linspace(0, arc[-1], n)]
    worst = min(delta_e(a, b) for a, b in zip(out, out[1:]))
    if worst < min_de:
        raise ValueError(f"ordinal_gradient: {c} gives adjacent levels only {worst:.1f} ΔE00 apart at n={n}; "
                         "use fewer levels or a darker key colour")
    return out


def mark_ordinal(ax, levels):
    """Declare that ``ax`` encodes an ordered variable with the single-hue ``levels`` (documentation for
    readers of the figure code and the gallery; the palette-clash gate still applies to every pair)."""
    ax._figkit_ordinal = list(levels)
    return ax


def soft_controls(n, kind="pastel", hue=SOFT_EMPHASIS):
    """``n`` light control colours for the soft theme. ``kind="pastel"``: distinct light hues
    (``SOFT_CONTROLS``, figures4papers style 1); ``kind="gradient"``: one hue light -> mid, <= 4 steps at equal
    ΔE00 (style 2; adjacent steps are ~6-9 ΔE00, so declare them with ``mark_controls``). Pair with ``SOFT_EMPHASIS``."""
    if kind == "pastel":
        if not 1 <= n <= len(SOFT_CONTROLS):
            raise ValueError(f"soft_controls: at most {len(SOFT_CONTROLS)} pastel controls, got {n}")
        return SOFT_CONTROLS[:n]
    if kind == "gradient":
        if not 1 <= n <= 4:  # 5+ single-hue steps fall below 4 ΔE00 or run into SOFT_EMPHASIS
            raise ValueError(f"soft_controls: at most 4 gradient controls, got {n}; use kind='pastel' (<= 6)")
        import numpy as np
        if n == 1:
            return [_mix(hue, 0.7)]
        path = [_mix(hue, t) for t in np.linspace(0.8, 0.3, 300)]  # light -> mid, sampled at equal ΔE00
        arc = np.concatenate([[0.0], np.cumsum([delta_e(a, b) for a, b in zip(path, path[1:])])])
        return [path[int(np.argmin(np.abs(arc - x)))] for x in np.linspace(0, arc[-1], n)]
    raise ValueError(f"soft_controls: kind must be 'pastel' or 'gradient', got {kind!r}")


def mark_controls(ax, colors):
    """Declare ``colors`` as one control group on ``ax``: under the soft theme the palette-clash gate
    compares them with each other at ``CONTROL_MIN_DE`` (they are meant to look alike); every control vs
    every other colour still needs the full threshold."""
    from matplotlib.colors import to_hex
    ax._figkit_controls = {to_hex(c) for c in colors}
    return ax


def axis_break(ax, axis="y", size=0.025):
    """Break mark (two short parallel slashes) at the origin end of a truncated value axis; required by
    ``qa.bar_baseline_audit`` for bars whose value axis does not start at 0. Auxiliary (dark grey)."""
    import matplotlib.lines as mlines
    d = size
    if axis == "y":
        segs = [([-d, d], [0.02 - d, 0.02 + d]), ([-d, d], [0.055 - d, 0.055 + d])]
    else:
        segs = [([0.02 - d, 0.02 + d], [-d, d]), ([0.055 - d, 0.055 + d], [-d, d])]
    for xs, ys in segs:
        ln = mlines.Line2D(xs, ys, transform=ax.transAxes, color=ERR_COLOUR,
                           linewidth=0.8, clip_on=False, zorder=10)
        aux(ln)
        ln._figkit_break = True
        ax.add_line(ln)
    ax._figkit_axis_break = axis
    return ax


def current_theme():
    return _THEME["name"]


def mm(x):
    return x / 25.4


def _font_has_true_minus():
    path = font_manager.findfont(font_manager.FontProperties(family=mpl.rcParams["font.family"]))
    return 0x2212 in FT2Font(path).get_charmap()


def apply(cfg=None):
    """Apply the journal style from cfg (or the active config); returns the config used."""
    cfg = config.use(config.resolve_cfg(cfg))
    cfg.ensure_scipilot()
    from setup_style import setup_style
    setup_style(journal=cfg.journal, lang="en")
    mpl.rcParams.update(RC)
    theme = getattr(cfg, "theme", "default")
    if theme == "soft":
        mpl.rcParams.update(SOFT_RC)
    _THEME["name"] = theme
    if not _font_has_true_minus():
        raise RuntimeError("style.apply: the active font lacks U+2212 (true minus); "
                           "choose a font such as Arial or DejaVu Sans")
    return cfg


def palette(kind, cfg=None):
    """Palette table ('cohort' / 'class' / ...) from figkit.toml: name -> {color, marker, label, edge}."""
    pals = config.resolve_cfg(cfg).palettes
    if kind not in pals:
        raise KeyError(f"palette {kind!r} not defined in figkit.toml (have {sorted(pals)})")
    return pals[kind]


def aux(*artists):
    """Mark artists (or axes) as auxiliary (reference bands, guides): exempt from the S3 colour audit.
    Returns the artist for a single argument, otherwise the tuple."""
    for a in artists:
        a._figkit_aux = True
    return artists[0] if len(artists) == 1 else artists


def _lab(c):
    """CIELAB (D65) of a matplotlib colour (alpha ignored)."""
    import numpy as np
    from matplotlib.colors import to_rgb
    rgb = np.array(to_rgb(c))
    rgb = np.where(rgb > 0.04045, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = M @ rgb / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.array([116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])])


def delta_e(c1, c2):
    """CIEDE2000 colour difference of two matplotlib colours (alpha ignored). Rough guide for data colours
    in one panel: < 12 reads as the same hue; Okabe-Ito neighbours are >= 21."""
    import numpy as np
    (L1, a1, b1), (L2, a2, b2) = _lab(c1), _lab(c2)
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p, h2p = np.degrees(np.arctan2(b1, a1p)) % 360, np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0:
        dh = 0.0
    elif dh > 180:
        dh -= 360
    elif dh < -180:
        dh += 360
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    if C1p * C2p == 0:
        hm = h1p + h2p
    elif abs(h1p - h2p) <= 180:
        hm = (h1p + h2p) / 2
    else:
        hm = (h1p + h2p + 360) / 2 if h1p + h2p < 360 else (h1p + h2p - 360) / 2
    T = (1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm))
         + 0.32 * np.cos(np.radians(3 * hm + 6)) - 0.20 * np.cos(np.radians(4 * hm - 63)))
    SL = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2)
    SC, SH = 1 + 0.045 * Cmp, 1 + 0.015 * Cmp * T
    RT = (-2 * np.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7))
          * np.sin(np.radians(60 * np.exp(-(((hm - 275) / 25) ** 2)))))
    return float(np.sqrt((dLp / SL) ** 2 + (dCp / SC) ** 2 + (dHp / SH) ** 2
                         + RT * (dCp / SC) * (dHp / SH)))


def _decade(v, _pos=None):
    """'$10^{−k}$' with a true minus (U+2212) for decades, '0' at zero, '' elsewhere (minor ticks)."""
    import math
    if v == 0:
        return "0"
    e = math.log10(abs(v))
    if abs(e - round(e)) > 1e-9:
        return ""
    k = int(round(e))
    sign = "−" if v < 0 else ""
    return f"${sign}10^{{{str(k).replace('-', chr(0x2212))}}}$"


def log_ticks(ax, axis="x"):
    """Log / symlog decade tick labels with a true minus (matplotlib's default writes 10^{-k} with an
    ASCII hyphen, which qa.true_minus rejects). Call after set_xscale / set_yscale."""
    from matplotlib.ticker import FuncFormatter, NullFormatter
    a = ax.xaxis if axis == "x" else ax.yaxis
    a.set_major_formatter(FuncFormatter(_decade))
    a.set_minor_formatter(NullFormatter())
    return ax
