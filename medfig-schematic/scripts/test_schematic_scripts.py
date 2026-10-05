"""medfig-schematic scripts: schematic_spec, prompt_check, image_check, round_pack. Synthetic spec and images only."""
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import image_check  # noqa: E402
import prompt_check  # noqa: E402
import round_pack  # noqa: E402
import schematic_spec  # noqa: E402

SPEC = {
    "figure": "Fig 1",
    "size": {"width_mm": 180, "aspect": "3:2"},
    "palette": {
        "class": {"A": "#009E73", "B": "#0072B2", "C": "#D55E00"},
        "method": {"accent": "#AA3377"},
        "neutral": {"line": "#4D4D4D", "slot": "#F2F2F2"},
    },
    "distinct_groups": ["class"],
    "labels": {"a": ["Study design", "Training", "External test"],
               "b": ["Model", "Input scan", "12 blocks", "16 concepts"]},
    "allowed_numbers": ["12", "16"],
    "image_slots": ["Input scan"],
    "forbidden_patterns": [r"\bE[0-2]\b"],
    "ignore_quotes": ["frozen"],
}

FULL = """Canvas 180 mm wide, landscape 3:2, white background.
Row a: "Study design". Card "External test". Box "Training". Nothing connects "External test" to "Training".
Row b: "Model". Image slot "Input scan": an empty light-grey rectangle (#F2F2F2), draw nothing inside.
"12 blocks" then "16 concepts" in magenta #AA3377. Arrows dark grey #4D4D4D.
TEXT RULES: English only; only the labels above; no logos, no watermarks.
"""


@pytest.fixture
def spec_file(tmp_path):
    p = tmp_path / "schematic.yaml"
    p.write_text(yaml.safe_dump(SPEC, allow_unicode=True), encoding="utf-8")
    return p


@pytest.fixture
def spec(spec_file):
    return schematic_spec.load(spec_file)


def _errors(issues):
    return [m for lv, m in issues if lv == "ERROR"]


def _warns(issues):
    return [m for lv, m in issues if lv == "WARN"]


# ---------------------------------------------------------------- spec
def test_spec_loads(spec):
    assert spec["aspect"] == pytest.approx(1.5)
    assert spec["colours"]["#009E73"] == "class.A"
    assert "Input scan" in spec["labels_flat"]
    assert schematic_spec.self_check(spec) == []


def test_spec_bad_hex(tmp_path):
    bad = dict(SPEC, palette={"class": {"A": "green"}})
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(schematic_spec.SpecError):
        schematic_spec.load(p)


def test_spec_unknown_distinct_group(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(dict(SPEC, distinct_groups=["nope"])), encoding="utf-8")
    with pytest.raises(schematic_spec.SpecError):
        schematic_spec.load(p)


def test_spec_self_check_result_number_and_slot(tmp_path):
    s = dict(SPEC, labels=["AUC 0.95", "Model"], image_slots=["Missing slot"])
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(s), encoding="utf-8")
    errs = _errors(schematic_spec.self_check(schematic_spec.load(p)))
    assert any("0.95" in e for e in errs)
    assert any("Missing slot" in e for e in errs)


def test_label_numbers_split_dimensions():
    assert schematic_spec.label_numbers("16 × 16 × 768") == ["16", "16", "768"]
    assert schematic_spec.label_numbers("90% target") == ["90%"]
    assert schematic_spec.label_numbers("ViT-B #AA3377") == []


# ---------------------------------------------------------------- prompt_check
def test_full_prompt_clean(spec):
    issues = prompt_check.check(FULL, spec, "full")
    assert _errors(issues) == [], issues


def test_unlisted_label(spec):
    errs = _errors(prompt_check.check(FULL + '\nAdd "Decoder".', spec, "full"))
    assert any('"Decoder"' in e for e in errs)


def test_ignore_quotes(spec):
    assert _errors(prompt_check.check(FULL + '\nMark it "frozen".', spec, "full")) == []


def test_off_palette_colour(spec):
    errs = _errors(prompt_check.check(FULL + "\nStage bars in #4F86F7.", spec, "full"))
    assert any("#4F86F7" in e for e in errs)


def test_hex_case_insensitive(spec):
    assert _errors(prompt_check.check(FULL.replace("#AA3377", "#aa3377"), spec, "full")) == []


def test_forbidden_code(spec):
    errs = _errors(prompt_check.check(FULL + "\nThis is the E2 endpoint.", spec, "full"))
    assert any("forbidden" in e for e in errs)


def test_result_number_in_quote(tmp_path):
    s = dict(SPEC)
    s["labels"] = dict(SPEC["labels"], c=["AUC 0.95"])
    s["allowed_numbers"] = SPEC["allowed_numbers"]
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(s), encoding="utf-8")
    sp = schematic_spec.load(p)
    errs = _errors(prompt_check.check(FULL + '\n"AUC 0.95"', sp, "full"))
    assert any("design numbers" in e for e in errs)


def test_cjk_rejected(spec):
    errs = _errors(prompt_check.check(FULL + "\n中文说明", spec, "full"))
    assert any("CJK" in e for e in errs)


def test_slot_not_declared_empty(spec):
    text = FULL.replace("an empty light-grey rectangle (#F2F2F2), draw nothing inside", "a rectangle")
    errs = _errors(prompt_check.check(text, spec, "full"))
    assert any("empty" in e for e in errs)


def test_full_needs_size_and_text_rules(spec):
    text = FULL.replace("Canvas 180 mm wide, landscape 3:2, white background.", "").replace("TEXT RULES", "Rules")
    errs = _errors(prompt_check.check(text, spec, "full"))
    assert any("size" in e for e in errs) and any("TEXT RULES" in e for e in errs)


def test_full_missing_label_is_warning(spec):
    text = FULL.replace('Box "Training".', "").replace('to "Training"', "to training")
    issues = prompt_check.check(text, spec, "full")
    assert _errors(issues) == []
    assert any("Training" in w for w in _warns(issues))


def test_edit_mode_needs_keep_clause(spec):
    errs = _errors(prompt_check.check('1. Change "Training" fill.', spec, "edit"))
    assert any("Keep everything else" in e for e in errs)
    ok = "Keep everything else exactly as it is. Only make these changes:\n1. Recolour \"Training\"."
    assert _errors(prompt_check.check(ok, spec, "edit")) == []


def test_edit_mode_too_many_changes(spec):
    body = "Keep everything else exactly as it is. Only make these changes:\n" + "".join(
        f"{i}. Recolour \"Model\".\n" for i in range(1, 9))
    assert any("8 numbered changes" in w for w in _warns(prompt_check.check(body, spec, "edit")))


def test_arrow_without_route(spec):
    warns = _warns(prompt_check.check(FULL + "\nAdd an arrow for the development card.", spec, "full"))
    assert any("route" in w for w in warns)
    routed = FULL + '\nAdd an arrow from "Study design" up and over into "Training".'
    assert not any("route" in w for w in _warns(prompt_check.check(routed, spec, "full")))


def test_banned_word_in_label(tmp_path):
    pytest.importorskip("figkit")
    s = dict(SPEC)
    s["labels"] = dict(SPEC["labels"], c=["validated model"])
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(s), encoding="utf-8")
    errs = _errors(prompt_check.check(FULL + '\n"validated model"', schematic_spec.load(p), "full"))
    assert any("banned" in e for e in errs)


def test_prompt_check_cli(tmp_path, spec_file, capsys):
    p = tmp_path / "prompt.txt"
    p.write_text(FULL, encoding="utf-8")
    assert prompt_check.main([str(p), "--spec", str(spec_file)]) == 0
    p.write_text(FULL + "\n#123456", encoding="utf-8")
    assert prompt_check.main([str(p), "--spec", str(spec_file)]) == 1
    assert "error(s)" in capsys.readouterr().out


# ---------------------------------------------------------------- image_check
def _img(path, w=600, h=400, blocks=None, bg=(255, 255, 255)):
    a = np.full((h, w, 3), bg, dtype=np.uint8)
    for (x0, y0, x1, y1), hx in (blocks or []):
        a[y0:y1, x0:x1] = image_check.hex_rgb(hx).astype(np.uint8)
    Image.fromarray(a).save(path)
    return path


CLASS_BLOCKS = [((10, 10, 60, 60), "#009E73"), ((70, 10, 120, 60), "#0072B2"), ((130, 10, 180, 60), "#D55E00"),
                ((10, 100, 200, 160), "#AA3377")]


def test_image_clean(tmp_path, spec):
    p = _img(tmp_path / "ok.png", 1536, 1024, [((x0 * 2, y0 * 2, x1 * 2, y1 * 2), c)
                                                  for (x0, y0, x1, y1), c in CLASS_BLOCKS])
    size, px = image_check.load_pixels(p)
    issues, rep = image_check.analyse(size, px, spec)
    assert _errors(issues) == []
    assert rep["aspect"] == pytest.approx(1.5)
    assert set(rep["distinct_L"]) == {"class.A", "class.B", "class.C"}
    assert not any("off the palette" in w for w in _warns(issues))
    assert any("dpi" in w for w in _warns(issues))      # 1536 px at 180 mm < 300 dpi: draft


def test_image_wrong_aspect(tmp_path, spec):
    p = _img(tmp_path / "sq.png", 500, 500, CLASS_BLOCKS)
    errs = _errors(image_check.analyse(*image_check.load_pixels(p), spec)[0])
    assert any("aspect" in e for e in errs)


def test_image_off_palette_and_missing_class(tmp_path, spec):
    blocks = [((10, 10, 300, 300), "#4F86F7"), ((310, 10, 360, 60), "#009E73")]
    p = _img(tmp_path / "off.png", 600, 400, blocks)
    issues, rep = image_check.analyse(*image_check.load_pixels(p), spec)
    warns = _warns(issues)
    assert any("off the palette" in w for w in warns)
    assert rep["off_palette_top"]
    assert any("class.B" in w and "not found" in w for w in warns)


def test_image_colour_drift(tmp_path, spec):
    # class B requested #0072B2, drawn as a brighter blue (what image models typically return)
    blocks = [((10, 10, 60, 60), "#009E73"), ((70, 10, 120, 60), "#5190FB"), ((130, 10, 180, 60), "#D55E00")]
    p = _img(tmp_path / "drift.png", 600, 400, blocks)
    issues, rep = image_check.analyse(*image_check.load_pixels(p), spec)
    assert rep["distinct_measured"]["class.B"]["measured"] == "#5190FB"
    assert any("class.B" in w and "drawn as" in w for w in _warns(issues))
    assert not any("class.A" in w and "drawn as" in w for w in _warns(issues))


def test_image_tints_are_on_palette(tmp_path, spec):
    # light fills of palette colours (mixed with white) are not off-palette
    tint = lambda hx, a: "#%02X%02X%02X" % tuple(int(255 + a * (c - 255)) for c in image_check.hex_rgb(hx))
    blocks = CLASS_BLOCKS + [((200, 100, 400, 300), tint("#AA3377", 0.3)), ((410, 100, 590, 300), tint("#0072B2", 0.5))]
    p = _img(tmp_path / "tint.png", 600, 400, blocks)
    issues, rep = image_check.analyse(*image_check.load_pixels(p), spec)
    assert rep.get("off_palette_share", 0) < 0.01
    assert not any("off the palette" in w for w in _warns(issues))


def test_image_greyscale_palette_vs_drift(tmp_path):
    # palette pair close in L* (A/B) -> "already in the palette"; distinct palette pair drawn close -> "drift"
    s = dict(SPEC, palette={"class": {"A": "#E69F00", "B": "#56B4E9", "C": "#0072B2"}, "neutral": {"line": "#4D4D4D"}})
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(s), encoding="utf-8")
    sp = schematic_spec.load(p)
    img = _img(tmp_path / "g.png", 600, 400, [((10, 10, 100, 100), "#E69F00"), ((110, 10, 200, 100), "#56B4E9"),
                                              ((210, 10, 300, 100), "#3FA0F4")])
    warns = [w for w in _warns(image_check.analyse(*image_check.load_pixels(img), sp)[0]) if "greyscale" in w]
    assert any("class.A and class.B" in w and "already in the palette" in w for w in warns)
    assert any("class.B and class.C" in w and "drift" in w for w in warns)


def test_edit_keep_variants(spec):
    for clause in ("Keep row b EXACTLY as it is. Redraw rows a and c:", "Row b: DO NOT CHANGE.",
                   "Only redraw rows a and c."):
        assert _errors(prompt_check.check(clause + '\n1. Recolour "Model".', spec, "edit")) == [], clause


def test_image_greyscale_clash(tmp_path):
    s = dict(SPEC, palette={"class": {"A": "#E69F00", "B": "#56B4E9"}, "neutral": {"line": "#4D4D4D"}})
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump(s), encoding="utf-8")
    sp = schematic_spec.load(p)
    img = _img(tmp_path / "g.png", 600, 400, [((10, 10, 100, 100), "#E69F00"), ((110, 10, 200, 100), "#56B4E9")])
    warns = _warns(image_check.analyse(*image_check.load_pixels(img), sp)[0])
    assert any("greyscale" in w and "already in the palette" in w for w in warns)


def test_lab_reference_values():
    lab = image_check.rgb_to_lab(np.array([[255, 255, 255], [0, 0, 0], [255, 0, 0]]))
    assert lab[0] == pytest.approx([100, 0, 0], abs=0.1)
    assert lab[1] == pytest.approx([0, 0, 0], abs=0.1)
    assert lab[2] == pytest.approx([53.24, 80.09, 67.20], abs=0.1)


def test_image_check_cli_json(tmp_path, spec_file):
    p = _img(tmp_path / "ok.png", 600, 400, CLASS_BLOCKS)
    out = tmp_path / "r.json"
    assert image_check.main([str(p), "--spec", str(spec_file), "--json", str(out)]) == 0
    assert "issues" in out.read_text(encoding="utf-8")


# ---------------------------------------------------------------- round_pack
def _round(work, n, prompt):
    (work / f"round{n}.md").write_text(f"# Round {n}\n\n```text\n{prompt}```\n\n中文说明\n", encoding="utf-8")


def test_round_pack(tmp_path, spec_file):
    work = spec_file.parent
    _round(work, 2, FULL)
    prev = _img(tmp_path / "gpt.png", 600, 400, CLASS_BLOCKS)
    ref = _img(tmp_path / "ref.png", 300, 200)
    ready, lines = round_pack.pack(work, 2, prev, [(ref, "style_ref.png")])
    assert ready, lines
    assert (work / "round1_output.png").read_bytes() == prev.read_bytes()
    up = work / "round2_upload"
    assert (up / "prompt.txt").read_text(encoding="utf-8").strip() == FULL.strip()
    assert (up / "style_ref.png").is_file()
    assert any("full mode" in l and "new chat" in l for l in lines)


def test_round_pack_edit_mode_and_errors(tmp_path, spec_file):
    work = spec_file.parent
    _round(work, 3, 'Keep everything else exactly as it is. Only make these changes:\n1. Recolour "Model" #123456.\n')
    ready, lines = round_pack.pack(work, 3)
    assert not ready
    assert any("edit mode" in l and "same chat" in l for l in lines)
    assert any("#123456" in l for l in lines)
    assert (work / "round3_upload" / "prompt.txt").is_file()


def test_round_pack_needs_one_block(tmp_path, spec_file):
    work = spec_file.parent
    (work / "round4.md").write_text("no prompt here", encoding="utf-8")
    with pytest.raises(SystemExit):
        round_pack.pack(work, 4)


def test_round_pack_does_not_overwrite(tmp_path, spec_file):
    work = spec_file.parent
    _round(work, 2, FULL)
    (work / "round1_output.png").write_bytes(b"older")
    prev = _img(tmp_path / "gpt.png", 600, 400)
    with pytest.raises(SystemExit):
        round_pack.pack(work, 2, prev)
    assert round_pack.pack(work, 2, prev, force=True)[0]


def test_round_pack_without_spec(tmp_path):
    _round(tmp_path, 1, FULL)
    ready, lines = round_pack.pack(tmp_path, 1)
    assert ready and any("not checked" in l for l in lines)
