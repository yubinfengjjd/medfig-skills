"""Layout helpers for image grids."""


def image_width_ratios(shapes):
    """Column width ratios for images of shape (H, W): proportional to W/H so equal-height images fill
    their columns (pass as ``gridspec_kw={"width_ratios": ...}``)."""
    out = []
    for h, w in shapes:
        if h <= 0 or w <= 0:
            raise ValueError(f"image shape must be positive (H, W), got {(h, w)}")
        out.append(w / h)
    return out


def small_multiples(fig, n, ncols, cell_in=1.6, legend_rows=0.0, gs=None, sharex=True, sharey=True,
                    last_row="center"):
    """Grid of ``n`` square data cells (e.g. one ROC per cohort), ``ncols`` per row.

    Facet rule (medfig-plan S8): prefer one row (``ncols = n``) when the cells fit the page width; otherwise
    an incomplete last row is centred (``last_row="center"``, default), never left-aligned with a blank
    trailing slot. ``last_row="left"`` only when the caller fills the empty slots with data panels.
    ``cell_in``: cell edge in inches (with one ``curves.shared_key`` and per-cell ``curves.value_block``,
    1.2 in is enough; a full per-cell 3-entry legend at 6 pt needs >= 1.6 in). ``legend_rows`` adds that
    many legend lines of headroom (inches ~0.1 each) to the suggested height. ``gs``: an existing
    SubplotSpec to subdivide. Returns (axes list, suggested (width, height) in inches)."""
    if n < 1 or ncols < 1:
        raise ValueError("small_multiples needs n >= 1 and ncols >= 1")
    if last_row not in ("center", "left"):
        raise ValueError(f"last_row must be 'center' or 'left', got {last_row!r}")
    ncols = min(ncols, n)
    nrows = -(-n // ncols)
    rem = n - (nrows - 1) * ncols
    # half-cell resolution so a centred short row can be offset by half a cell
    sub = gs.subgridspec(nrows, 2 * ncols) if gs is not None else fig.add_gridspec(nrows, 2 * ncols)
    axes, first = [], None
    for i in range(n):
        r, c = divmod(i, ncols)
        off = (ncols - rem) if (r == nrows - 1 and rem < ncols and last_row == "center") else 0
        kw = {}
        if first is not None:
            if sharex:
                kw["sharex"] = first
            if sharey:
                kw["sharey"] = first
        ax = fig.add_subplot(sub[r, off + 2 * c: off + 2 * c + 2], **kw)
        ax.set_box_aspect(1)
        first = first or ax
        axes.append(ax)
    size = (ncols * (cell_in + 0.35), nrows * (cell_in + 0.35 + 0.1 * legend_rows))
    return axes, size
