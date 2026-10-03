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


def small_multiples(fig, n, ncols, cell_in=1.6, legend_rows=0.0, gs=None, sharex=True, sharey=True):
    """Grid of ``n`` square data cells (e.g. one ROC per cohort), ``ncols`` per row.

    ``cell_in``: cell edge in inches -- at 6 pt a "model (AUC = mean ± SD)" legend with 3 entries needs
    >= 1.6 in (a 1-in cell overlaps). ``legend_rows`` adds that many legend lines of headroom (inches
    ~0.1 each) to the suggested height. ``gs``: an existing SubplotSpec to subdivide. Returns
    (axes list, suggested (width, height) in inches). Cells beyond ``n`` are not created."""
    if n < 1 or ncols < 1:
        raise ValueError("small_multiples needs n >= 1 and ncols >= 1")
    nrows = -(-n // ncols)
    sub = (gs.subgridspec(nrows, ncols) if gs is not None else fig.add_gridspec(nrows, ncols))
    axes, first = [], None
    for i in range(n):
        kw = {}
        if first is not None:
            if sharex:
                kw["sharex"] = first
            if sharey:
                kw["sharey"] = first
        ax = fig.add_subplot(sub[i // ncols, i % ncols], **kw)
        ax.set_box_aspect(1)
        first = first or ax
        axes.append(ax)
    size = (ncols * (cell_in + 0.35), nrows * (cell_in + 0.35 + 0.1 * legend_rows))
    return axes, size
