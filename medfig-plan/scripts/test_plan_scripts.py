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
