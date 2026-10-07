"""medfig-plan self-check scripts: data_health (inventory) and spec_check (spec redundancy / completeness)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_health  # noqa: E402
import spec_check  # noqa: E402

FULL = """- claim：{c}
  - data：{d}
  - chart：{ch}
  - reason：r
  - caption：cap
  - counterfactual：cf"""


def _panel(letter, c="X improves", d="data/a.csv · col y", ch="violin + strip；x=g"):
    return f"- **{letter} t**\n  " + FULL.format(c=c, d=d, ch=ch)


def test_spec_check_clean_and_missing_fields():
    good = "### Fig 2 Test\n" + _panel("a") + "\n" + _panel("b", c="Y is calibrated", d="data/b.csv · p") + "\n"
    assert spec_check.check(good) == []
    bad = "### Fig 3\n- **a t**\n  - claim：x\n  - data：d\n  - chart：c\n"
    out = spec_check.check(bad)
    assert len(out) == 1 and "reason" in out[0] and "counterfactual" in out[0]


def test_spec_check_same_claim_same_data_duplicate_letter():
    text = ("### Fig 4\n" + _panel("a") + "\n" + _panel("b") + "\n"  # same claim, same data, same chart
            + _panel("c", c="Z differs", d="data/a.csv · col y", ch="ECDF；x=y") + "\n"  # same data, new chart
            + _panel("c", c="W") + "\n")
    out = spec_check.check(text)
    assert any("same claim" in i for i in out)
    assert any("same data" in i and "'c'" in i for i in out)  # a/b/c share data/a.csv, c uses another chart
    assert any("duplicate panel letter 'c'" in i for i in out)


def test_spec_check_cli_exit_codes(tmp_path):
    p = tmp_path / "spec.md"
    p.write_text("### Fig 2\n" + _panel("a") + "\n", encoding="utf-8")
    assert spec_check.main([str(p)]) == 0
    p.write_text("### Fig 2\n- **a t**\n  - claim：x\n", encoding="utf-8")
    assert spec_check.main([str(p)]) == 1


def test_data_health_findings(tmp_path):
    df = pd.DataFrame(dict(site=["a", "a", "b", "b", "b", "c"], y=[1.0, 1.0, None, 2.0, 3.0, 4.0], k=[7] * 6))
    df = pd.concat([df, df.iloc[[0]]], ignore_index=True)
    p = tmp_path / "t.csv"; df.to_csv(p, index=False)
    out = tmp_path / "health.md"
    (f,) = data_health.main([str(p), "--group", "site", "--out", str(out)])
    assert f["rows"] == 7 and f["duplicate_rows"] == 2 and f["constant_columns"] == ["k"]
    assert f["missing"] == {"y": 1} and f["groups"] == {"a": 3, "b": 3, "c": 1}
    assert any("n < 5" in w for w in f["warnings"])
    text = out.read_text(encoding="utf-8")
    assert "## t.csv" in text and "| y | float64 | 1 |" in text
    assert pd.read_csv(p).shape == (7, 3)  # input untouched


def test_spec_check_main_figure_needs_a_curve():
    perf = _panel("a", c="internal BACC 0.81", ch="dumbbell；x=BACC，y=cohort")
    out = spec_check.check("### Fig 4 Performance\n" + perf + "\n")
    assert len(out) == 1 and "S7" in out[0] and "['a']" in out[0]
    roc = _panel("b", c="model separates classes", d="data/s.npz · probs", ch="ROC mean ± SD；x=1 − specificity")
    assert spec_check.check("### Fig 4 Performance\n" + perf + "\n" + roc + "\n") == []
    pr = _panel("b", c="minority class retained", d="data/s.npz · probs", ch="PR 小多图；x=recall")
    assert spec_check.check("### Fig 4\n" + perf + "\n" + pr + "\n") == []
    exempt = "### Fig 4\n- curve_exempt：only summary rows, no per-sample scores\n" + perf + "\n"
    assert spec_check.check(exempt) == []
    # supplementary figures and non-discrimination curves
    assert spec_check.check("### S6 Performance\n" + perf + "\n") == []
    assert spec_check.check("### Fig S6 Performance\n" + perf + "\n") == []
    tail = _panel("b", c="fewer large errors", d="data/e.csv · err", ch="exceedance curve；log y")
    assert any("S7" in i for i in spec_check.check("### Fig 4\n" + perf + "\n" + tail + "\n"))
    # "PR" must be a word: "PRedicted" does not count as a PR curve
    pred = _panel("b", c="maps align", d="data/m.npz · cam", ch="predicted-class heat；x=w")
    assert any("S7" in i for i in spec_check.check("### Fig 4\n" + perf + "\n" + pred + "\n"))


def _img(sel=None):
    s = _panel("a", c="maps concentrate in the outer retina", d="gallery/*.npz · cam",
               ch="病例矩阵 case_matrix.py；每组 3×6")
    return s + (f"\n  - case_selection：{sel}" if sel is not None else "")


def test_spec_check_case_selection_rules():
    ok = "按类别分层、固定 seed 随机，seed = 20261008；每组 12 例（其中误判 3）；候选池为可用影像子集"
    assert spec_check.check("### Fig 7\n" + _img(ok) + "\n") == []
    assert spec_check.check("### Fig 7\n" + _img("stratified random, seed=7, 12 cases per group incl. "
                                                 "3 misclassified") + "\n") == []
    assert spec_check.check("### Fig 7\n" + _img("single illustrative case; exempt: case report page") + "\n") == []
    out = spec_check.check("### Fig 7\n" + _img() + "\n")
    assert len(out) == 1 and "without case_selection" in out[0]
    out = spec_check.check("### Fig 7\n" + _img("每组 4 例，代表性病例") + "\n")
    assert any("seed" in i for i in out) and any("misclassified" in i for i in out)
    assert any(">= 12 cases per group" in i and "[4]" in i for i in out)
    # supplementary imaging panels follow the same rule; non-imaging panels are untouched
    assert spec_check.check("### S12\n" + _img() + "\n")
    assert spec_check.check("### Fig 2\n" + _panel("a") + "\n") == []
