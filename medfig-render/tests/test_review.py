"""figkit.review.contact_sheet: file names sit in the header band, never on the image area."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pytest

from figkit import review


def test_contact_sheet_header_outside_image(tmp_path):
    png = tmp_path / "x.png"
    plt.imsave(png, np.random.default_rng(0).uniform(size=(40, 80, 3)))
    from matplotlib.backends.backend_pdf import PdfPages
    with PdfPages(tmp_path / "a.pdf") as pdf:
        axes = review._page(pdf, "x.png", [png])
    assert all(not ax.texts for ax in axes)
    out = review.contact_sheet(tmp_path / "sheet.pdf", [("x.png", [png]), ("before / after", [png, png])])
    assert out.stat().st_size > 0


def test_text_on_image_rejected():
    fig, ax = plt.subplots()
    ax.text(0.1, 0.9, "exceedance", transform=ax.transAxes)
    with pytest.raises(RuntimeError, match="image area"):
        review.check_image_axes_clean([ax])
