"""Journal figure specifications: one entry per venue, each with its source and verification status.

Format after JRBCH/spiffyplots ``journals.py`` (MIT licence, Copyright (c) 2020-2026 Julian Rossbroich and
spiffyplots contributors); status labels after enesgul23/scientific-figure-skills (MIT). Numbers re-checked
on 2026-10-07:

- VERIFIED: read from the publisher's own page on the check date (quoted in ``source``).
- ESTIMATED: the official page was not reachable from here (HTTP 403); values come from the named
  secondary source and must be confirmed on the publisher's site before submission.

Widths are millimetres. ``font_min`` / ``font_max`` are the publisher's stated text range at final size;
``figkit_font`` is what figkit draws with (never below ``style.MIN_FONT_PT`` = 6 pt, the house floor, even
where a venue allows 5 pt). Journals without their own artwork rules inherit their publisher's entry
(``inherits``).
"""
from dataclasses import dataclass, field

CHECKED = "2026-10-07"
MM_PER_IN = 25.4


@dataclass(frozen=True)
class Journal:
    key: str
    title: str
    status: str                      # VERIFIED | ESTIMATED
    widths: dict                     # name -> mm
    font_min: float = None
    font_max: float = None
    font_family: str = "Arial or Helvetica"
    panel_label: str = None          # e.g. "8 pt bold lowercase"
    line_min_pt: float = None
    dpi_image: int = None
    dpi_line_art: int = None
    max_height_mm: float = None
    formats: str = ""
    source: str = ""
    checked: str = CHECKED
    inherits: str = None
    notes: tuple = field(default_factory=tuple)

    def width_in(self, name="single"):
        if name not in self.widths:
            raise KeyError(f"{self.key}: no {name!r} width (have {sorted(self.widths)})")
        return self.widths[name] / MM_PER_IN

    def figsize(self, name="single", height_mm=None, aspect=0.62):
        """(width, height) in inches for ``name`` width; height from ``height_mm`` or ``aspect`` x width,
        capped at ``max_height_mm``."""
        w = self.width_in(name)
        h = height_mm / MM_PER_IN if height_mm is not None else w * aspect
        if self.max_height_mm is not None:
            h = min(h, self.max_height_mm / MM_PER_IN)
        return (w, h)

    @property
    def figkit_font(self):
        from .style import MIN_FONT_PT
        return max(MIN_FONT_PT, self.font_min or MIN_FONT_PT)


JOURNALS = {
    "nature": Journal(
        key="nature", title="Nature", status="VERIFIED",
        widths={"single": 89.0, "one_half": 120.0, "double": 183.0},
        font_min=5.0, font_max=7.0, font_family="Helvetica or Arial (sans-serif)",
        panel_label="8 pt bold upright lowercase", line_min_pt=0.25, dpi_image=300, max_height_mm=247.0,
        formats="vector AI / EPS / PDF; images PSD / TIFF / JPEG 300-600 dpi; RGB recommended",
        source="https://www.nature.com/nature/for-authors/final-submission (single 89 mm, 1.5 col 120-136 mm, "
               "double 183 mm, page depth 247 mm, text 5-7 pt, labels 8 pt bold, lines 0.25-1 pt)",
        notes=("research-figure-guide.nature.com gives a 170 mm maximum figure height for main figures.",),
    ),
    "npj": Journal(
        key="npj", title="npj journals (Nature Portfolio)", status="ESTIMATED", inherits="nature",
        widths={"single": 89.0, "double": 183.0}, font_min=5.0, font_max=7.0,
        panel_label="8 pt bold lowercase", line_min_pt=0.25, dpi_image=300,
        source="Nature artwork guidance (research-figure-guide.nature.com); the npj Digital Medicine "
               "submission page was not reachable (cookie redirect) -- confirm per journal",
    ),
    "science": Journal(
        key="science", title="Science", status="ESTIMATED",
        widths={"single": 55.0, "double": 120.0, "triple": 183.0}, font_min=6.0, font_max=9.0,
        panel_label="bold uppercase (A, B, C)", line_min_pt=0.28, dpi_image=300, max_height_mm=227.5,
        source="science.org author figure preparation guide (PDF, HTTP 403 here); widths from the 2022 guide "
               "snippet '1 column = 13p8 picas (5.5 cm)'; text range / line weight from JRBCH/spiffyplots",
        notes=("Science uses uppercase panel letters: a deliberate exception to the house lowercase labels.",),
    ),
    "cell": Journal(
        key="cell", title="Cell Press", status="ESTIMATED",
        widths={"single": 85.0, "one_half": 114.0, "double": 174.0}, font_min=6.0, font_max=8.0,
        line_min_pt=0.5, dpi_image=300, dpi_line_art=1000,
        source="cell.com/figureguidelines (HTTP 403 here); widths and 0.5 pt line minimum from the Cell Press "
               "guideline text quoted in SushiLab/omrgc_v2_scripts Cell_Press_Guidelines.R; text range and dpi "
               "from JRBCH/spiffyplots",
        notes=("Some Cell Press titles (e.g. Matter) use other widths (112 mm single column) and Avenir.",),
    ),
    "elsevier": Journal(
        key="elsevier", title="Elsevier (default artwork)", status="VERIFIED",
        widths={"minimal": 30.0, "single": 90.0, "one_half": 140.0, "double": 190.0},
        font_min=6.0, font_max=7.0, line_min_pt=0.25, dpi_image=300, dpi_line_art=1000,
        formats="EPS / PDF vector; TIFF / JPEG; 300 dpi halftone, 500 dpi combination, 1000 dpi line art",
        source="https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/"
               "artwork-sizing (7 pt normal text, >= 6 pt sub / superscript; 30 / 90 / 140 / 190 mm); line width "
               "0.25 pt recommended (artwork FAQ)",
    ),
    "media": Journal(
        key="media", title="Medical Image Analysis (Elsevier)", status="ESTIMATED", inherits="elsevier",
        widths={"single": 90.0, "one_half": 140.0, "double": 190.0}, font_min=6.0, font_max=7.0,
        line_min_pt=0.25, dpi_image=300, dpi_line_art=1000,
        source="Elsevier default artwork instructions; the journal's own guide for authors was not reachable "
               "(HTTP 403) -- confirm journal-specific rules",
    ),
    "ieee": Journal(
        key="ieee", title="IEEE Transactions (incl. IEEE TMI)", status="VERIFIED",
        widths={"single": 88.9, "double": 182.0}, font_min=None, font_max=None,
        font_family="Helvetica, Times New Roman, Arial, Cambria or Symbol (embedded)",
        dpi_image=300, dpi_line_art=600, max_height_mm=220.0,
        formats="PS / EPS / PDF vector, PNG / TIFF raster (JPEG only for author photos)",
        source="https://journals.ieeeauthorcenter.ieee.org/create-your-ieee-journal-article/"
               "create-graphics-for-your-article/resolution-and-size/ (3.5 in / 7.16 in; >300 dpi colour, >600 dpi "
               "line art) and .../file-formatting/ (type ~9-10 pt at full size; max 7.16 x 8.8 in)",
        notes=("IEEE states no minimum font size; its target is ~9-10 pt at full size, larger than the other "
               "venues -- set axis text to 8-9 pt for IEEE figures.",),
    ),
}
ALIASES = {"tmi": "ieee", "ieee-tmi": "ieee", "medical-image-analysis": "media", "npj-digital-medicine": "npj",
           "cell-press": "cell"}


def get(name):
    """Journal entry by key or alias (case-insensitive)."""
    k = str(name).lower()
    k = ALIASES.get(k, k)
    if k not in JOURNALS:
        raise KeyError(f"unknown journal {name!r}; have {sorted(JOURNALS)} (aliases {sorted(ALIASES)})")
    return JOURNALS[k]


def available():
    return sorted(JOURNALS)
