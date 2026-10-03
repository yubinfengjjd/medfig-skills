"""figkit.journals: every entry has a source, a check date and a status; figsize respects width and max height;
house font floor (6 pt) holds even where a venue allows 5 pt."""
import pytest

from figkit import journals, style


def test_every_entry_documented():
    for k, j in journals.JOURNALS.items():
        assert j.key == k and j.status in ("VERIFIED", "ESTIMATED") and j.source and j.checked
        assert "single" in j.widths and "double" in j.widths and j.widths["double"] > j.widths["single"]
        if j.status == "ESTIMATED":
            assert any(w in j.source for w in ("403", "not reachable", "confirm")), k  # says why it is estimated


def test_nature_matches_house_sizes():
    n = journals.get("nature")
    assert n.width_in("single") == pytest.approx(89 / 25.4)
    assert style.SINGLE <= n.width_in("single")                            # house single (88 mm) fits
    assert n.width_in("double") == pytest.approx(183 / 25.4)               # house DOUBLE 7.09 in = 180 mm
    assert n.width_in("double") >= style.DOUBLE                            # house double fits Nature
    assert n.figkit_font == style.MIN_FONT_PT  # venue allows 5 pt, figkit keeps its 6 pt floor


def test_aliases_and_figsize():
    assert journals.get("TMI") is journals.get("ieee")
    w, h = journals.get("elsevier").figsize("double", height_mm=150)
    assert w == pytest.approx(190 / 25.4) and h == pytest.approx(150 / 25.4)  # no height cap given
    w, h = journals.get("ieee").figsize("double", height_mm=500)
    assert h == pytest.approx(220 / 25.4)  # capped at max height
    with pytest.raises(KeyError):
        journals.get("lancet")
    with pytest.raises(KeyError):
        journals.get("ieee").width_in("one_half")
