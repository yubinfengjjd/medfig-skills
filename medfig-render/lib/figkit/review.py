"""Review contact sheet: exported figure PNGs, one per page, for visual sign-off.

The file name lives in a header band ABOVE the image, separated by a rule, never on the image; the image
area itself carries no added text (``check`` asserts that). Optional before / after pairs stack the two
versions with "Before" / "After" in the same header band. Review material only -- not a figure export.
"""
from pathlib import Path

HEADER_IN = 0.35  # header band height (inches)


def _page(pdf, title, images, width_in=8.27):
    import matplotlib.image as mimage
    import matplotlib.pyplot as plt
    arrs = [mimage.imread(str(p)) for p in images]
    heights = [width_in * a.shape[0] / a.shape[1] for a in arrs]
    fig = plt.figure(figsize=(width_in, HEADER_IN + sum(heights) + 0.1 * (len(arrs) - 1)))
    H = fig.get_figheight()
    head = fig.add_axes([0, 1 - HEADER_IN / H, 1, HEADER_IN / H])
    head.set_axis_off()
    head.text(0.01, 0.5, title, ha="left", va="center", fontsize=9, color="#4D4D4D")
    head.axhline(0.02, color="#9A9A9A", linewidth=0.6)
    y = 1 - HEADER_IN / H
    img_axes = []
    for a, h in zip(arrs, heights):
        y -= h / H
        ax = fig.add_axes([0, y, 1, h / H])
        ax.imshow(a)
        ax.set_axis_off()
        img_axes.append(ax)
        y -= 0.1 / H
    pdf.savefig(fig)
    plt.close(fig)
    return img_axes


def check_image_axes_clean(img_axes):
    """No text drawn on any image area (the file name belongs in the header band)."""
    bad = [t.get_text() for ax in img_axes for t in ax.texts]
    if bad:
        raise RuntimeError(f"review sheet: text on the image area {bad}")


def contact_sheet(out_pdf, pages):
    """``pages``: list of (title, [png, ...]) -> one PDF page each (title in the header band, images
    stacked below). Returns the PDF path."""
    from matplotlib.backends.backend_pdf import PdfPages
    out_pdf = Path(out_pdf)
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(out_pdf) as pdf:
        for title, images in pages:
            check_image_axes_clean(_page(pdf, title, [Path(p) for p in images]))
    return out_pdf
