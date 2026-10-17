"""Smoke and regression tests for consistency_check.py and manuscript_check.py.

Run: python -X utf8 test_checks.py
No network, no project needed: every case builds a throwaway project in a temp directory.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import consistency_check as cc
import manuscript_check as mc

SPEC = """# 口径表

## 1. 术语

| 规范名（EN） | 规范名（ZH） | 禁用别名 | 代码 / 图表标签 | 定义与出处 |
|---|---|---|---|---|
| target-label-fitted reference | 目标标签拟合参照 | oracle 上限 | R2 | 定义 |

## 3. 关键计数

| 对象 | 数值 | 出处 | 规范写法 |
|---|---|---|---|
| OCTID 扫描 / 临床组 | 261 / 260 | T2.md | “261 张扫描、260 个临床组，扫描级与组级数值相同” |
"""


def make_project(files):
    tmp = Path(tempfile.mkdtemp(prefix="mdcheck_"))
    (tmp / "口径表.md").write_text(SPEC, encoding="utf-8")
    for rel, text in files.items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return tmp


class CountCheck(unittest.TestCase):
    def test_drift_flagged(self):
        p = make_project({"04_manuscript/Results/R.md": "OCTID had 259 scans in 260 clinical groups.\n"})
        w = cc.check_counts(p)
        self.assertTrue(any(x["rule"] == "count-manuscript" for x in w), w)

    def test_correct_silent(self):
        p = make_project({"04_manuscript/Results/R.md": "OCTID had 261 scans in 260 clinical groups.\n",
                          "T2.md": "OCTID: 261 scans, 260 clinical groups.\n"})
        self.assertEqual(cc.check_counts(p), [])

    def test_source_substring_not_enough(self):
        # 261 只在 12610 里出现 → 仍应报“未在出处文件中找到”（子串不算数）
        p = make_project({"04_manuscript/Results/R.md": "Nothing here.\n",
                          "T2.md": "size 12610 and 0.2601\n"})
        msgs = [x["msg"] for x in cc.check_counts(p) if x["rule"] == "count-source"]
        self.assertTrue(any("261" in m for m in msgs), msgs)

    def test_source_prefers_non_archive(self):
        p = make_project({"04_manuscript/Results/R.md": "Nothing here.\n",
                          "_process/old/T2.md": "stale: 999 scans\n",
                          "T2.md": "fresh: 261 scans, 260 clinical groups\n"})
        self.assertFalse([x for x in cc.check_counts(p) if x["rule"] == "count-source"])
        # 只有 _process 副本时也应找到，而不是静默跳过
        p2 = make_project({"04_manuscript/Results/R.md": "Nothing here.\n",
                           "_process/old/T2.md": "stale: 999 scans\n"})
        msgs = [x["msg"] for x in cc.check_counts(p2) if x["rule"] == "count-source"]
        self.assertTrue(any("261" in m for m in msgs), msgs)

    def test_lost_decimal(self):
        p = make_project({"04_manuscript/Results/R.md": "value 00053 lower; DOI (DOI: 10.1109/CVPR.2019.00949).\n"})
        rules = [x["rule"] for x in cc.check_counts(p)]
        self.assertIn("lost-decimal", rules)
        p2 = make_project({"04_manuscript/Results/R.md": "value 0.0053 lower.\n"})
        self.assertNotIn("lost-decimal", [x["rule"] for x in cc.check_counts(p2)])

    def test_alias_hit_and_skip(self):
        p = make_project({"04_manuscript/Results/R.md": "called the oracle 上限 here\n"})
        self.assertEqual(len(cc.scan(p)), 1)
        p2 = make_project({"04_manuscript/Results/R.md": "不是 oracle 上限\n"})
        self.assertEqual(cc.scan(p2), [])


class ManuscriptChecks(unittest.TestCase):
    def test_words_ignore_panel_labels(self):
        self.assertEqual(mc.words_of("(a) one two (b) three (a–c) four"), 4)

    def test_sentence_hard_cap(self):
        en = make_project({"D.md": "**Figure 1. Title.** (a) " + "word " * 61 + "end.\n"}) / "D.md"
        res = mc.check("legends", en)
        self.assertTrue(any(r["rule"] == "sentence-hard" and r["level"] == mc.E for r in res), res)

    def test_template_cap(self):
        en = make_project({"D.md": "## Discussion\nThis agrees with prior work. That agrees with it. It also agrees with that. X may differ.\n"}) / "D.md"
        res = mc.check("discussion", en)
        self.assertTrue(any(r["rule"] == "agrees-with" and r["level"] == mc.E for r in res), res)

    def test_number_not_in_results(self):
        proj = make_project({"D.md": "## Discussion\nCoverage reached 0.123 in this cohort.\n",
                             "R.md": "## Results\nCoverage reached 0.456 in this cohort.\n"})
        res = mc.check("discussion", proj / "D.md", results_path=str(proj / "R.md"))
        self.assertTrue(any(r["rule"] == "number-not-in-results" for r in res), res)

    def test_zh_pmid_parity(self):
        proj = make_project({"EN.md": "## Discussion\nPrior work (PMID: 12345678) showed X.\n",
                             "ZH.md": "## 讨论\n既往研究（PMID: 12345678）显示 X。\n",
                             "ZH2.md": "## 讨论\n既往研究显示 X。\n"})
        ok = mc.check("discussion", proj / "EN.md", zh_path=str(proj / "ZH.md"))
        self.assertFalse(any(r["rule"] == "zh-pmid" for r in ok), ok)
        bad = mc.check("discussion", proj / "EN.md", zh_path=str(proj / "ZH2.md"))
        self.assertTrue(any(r["rule"] == "zh-pmid" for r in bad), bad)


if __name__ == "__main__":
    unittest.main(verbosity=2)
