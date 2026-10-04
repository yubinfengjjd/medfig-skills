"""medfig-outline scripts: outline_check (numbers / references / wording) and outline_build (docx + md + folders).
Synthetic mini-project only."""
import json
import sys
from pathlib import Path

import pytest
import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import outline_build  # noqa: E402
import outline_check  # noqa: E402


@pytest.fixture
def proj(tmp_path):
    """Mini project: 2 figures with source.json + pdf/png, 1 table, captions, scripts."""
    p = tmp_path / "proj"
    (p / "out/figures/main").mkdir(parents=True)
    (p / "out/tables").mkdir(parents=True)
    (p / "docs/captions").mkdir(parents=True)
    (p / "figures/main").mkdir(parents=True)
    (p / "tables").mkdir()
    for name, vals in {"fig2": {"auc": {"all": 0.98312}, "n": 13859, "panels": [{"id": "a"}, {"id": "b"}]},
                       "fig3": {"recall": {"Edema": 0.9273}, "panels": [{"id": "a"}]}}.items():
        src = {"figure": name, "inputs": [{"path": "data:mainline/tables/x.csv", "sha256": "0" * 64, "rows": 3}],
               "transforms": [], "values": vals}
        (p / f"out/figures/main/{name}.source.json").write_text(json.dumps(src), encoding="utf-8")
        for ext in ("pdf", "png", "svg"):
            (p / f"out/figures/main/{name}.{ext}").write_bytes(b"x")
        (p / f"figures/main/{name}.py").write_text("# script", encoding="utf-8")
    (p / "out/tables/T1.csv").write_text("cohort,unit,bacc_mean\nInternal test,scan,0.9623\nSite B,scan,0.929\n",
                                         encoding="utf-8")
    (p / "out/tables/T1.md").write_text("**T1.** x\n", encoding="utf-8")
    (p / "tables/build_tables.py").write_text("# tables", encoding="utf-8")
    (p / "docs/captions/fig2.md").write_text("## Fig2\n\n**图 2** x\n", encoding="utf-8")
    (p / "docs/captions_zh.md").write_text("## Fig3\n\n**图 3** y\n", encoding="utf-8")
    return p


def _outline(**over):
    o = {
        "project": "demo", "figures_root": "out/figures", "tables_root": "out/tables",
        "captions": ["docs/captions_zh.md", "docs/captions"], "main_figures": ["fig2", "fig3"],
        "methods": [{"id": "2.1", "title": "Cohorts and evaluation", "short": "Cohorts",
                     "focus": [{"topic": "研究设计", "points": ["多中心回顾性研究；三分类（内部代号 E2）"]}],
                     "items": ["T1"], "code": [{"path": "tables/build_tables.py", "role": "表格"}]}],
        "results": [
            {"id": "3.1", "title": "Cohorts separate in the backbone representation", "subtitle": "队列在骨干表示中分开",
             "short": "Domain_shift",
             "paragraphs": [{"label": "第一段", "claim": "骨干层面队列可区分",
                             "points": ["域可辨识性 AUC 约 0.983，n = 13,859"], "cites": ["Fig2a-b", "T1"]}],
             "items": [{"ref": "Fig2a", "what": "PCA"}], "boundaries": ["不写设备因果"],
             "code": [{"path": "figures/main/fig2.py", "role": "绘图"},
                      {"path": "src/eval.py", "role": "计算", "guess": True}]},
            {"id": "3.2", "title": "Edema recall is high internally", "subtitle": "内部 Edema 召回率高",
             "short": "Internal", "paragraphs": [{"label": "第一段", "claim": "召回高",
                                                   "points": ["Edema 召回率 92.7%；内部 BACC 约 0.96"],
                                                   "cites": ["Fig3a", "T1"]}],
             "items": [{"ref": "Fig3a", "what": "recall"}], "code": []}],
        "numbers": [{"text": "0.983", "source": "fig2.source.json:values.auc.all"},
                    {"text": "13,859", "source": "fig2.source.json:values.n"},
                    {"text": "92.7%", "source": "fig3.source.json:values.recall.Edema"},
                    {"text": "0.96", "source": "table:T1.csv:bacc_mean@cohort=Internal test&unit=scan"}],
    }
    o.update(over)
    return o


def _write(tmp_path, o):
    f = tmp_path / "outline.yaml"
    f.write_text(yaml.safe_dump(o, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return f


def test_clean_outline_passes(proj, tmp_path):
    assert outline_check.check(_write(tmp_path, _outline()), proj) == []


def test_wrong_number_and_unregistered_number(proj, tmp_path):
    o = _outline()
    o["numbers"][0]["text"] = "0.984"
    o["results"][0]["paragraphs"][0]["points"].append("另一个数 0.55")
    out = outline_check.check(_write(tmp_path, o), proj)
    assert any("0.984" in i and "source value 0.98312" in i for i in out)
    assert any("0.55" in i and "not registered" in i for i in out)


def test_missing_refs_and_uncovered_main_figure(proj, tmp_path):
    o = _outline()
    o["results"][0]["paragraphs"][0]["cites"] = ["Fig2c", "ST99"]
    o["results"][1]["paragraphs"][0]["cites"] = ["T1"]
    o["results"][1]["items"] = []
    out = outline_check.check(_write(tmp_path, o), proj)
    assert any("Fig2c" in i for i in out) and any("ST99" in i for i in out)
    assert any("fig3" in i and "not covered" in i for i in out)


def test_methods_focus_has_no_result_numbers(proj, tmp_path):
    o = _outline()
    o["methods"][0]["focus"][0]["points"].append("AUC 达到 0.98")
    out = outline_check.check(_write(tmp_path, o), proj)
    assert any("Methods 2.1" in i and "0.98" in i for i in out)
    o["methods"][0]["allow_numbers"] = ["0.98"]
    assert not any("Methods 2.1" in i for i in outline_check.check(_write(tmp_path, o), proj))


@pytest.mark.parametrize("text", ["与早期版本相比", "pre-registered hypotheses", "Wave-1 model", "closure analysis",
                                  "预注册假设", "修复后的模型", "validated performance"])
def test_wording_gates(proj, tmp_path, text):
    o = _outline()
    o["results"][0]["paragraphs"][0]["points"].append(text)
    out = outline_check.check(_write(tmp_path, o), proj)
    assert out, text


def test_internal_code_only_inside_code_note(proj, tmp_path):
    toml = tmp_path / "figkit.toml"
    toml.write_text("data_root = \"d\"\n[qa]\nforbidden_patterns = ['\\bE[12]\\b']\n", encoding="utf-8")
    assert outline_check.check(_write(tmp_path, _outline()), proj, figkit_toml=toml) == []  # "（内部代号 E2）" ok
    o = _outline()
    o["results"][0]["paragraphs"][0]["points"].append("E2 头的召回")
    out = outline_check.check(_write(tmp_path, o), proj, figkit_toml=toml)
    assert any("E[12]" in i for i in out)


def test_results_title_must_be_a_finding(proj, tmp_path):
    o = _outline()
    o["results"][0]["title"] = "Results of domain shift"
    o["results"][1]["title"] = "AUC was 0.98 internally"
    out = outline_check.check(_write(tmp_path, o), proj)
    assert any("3.1" in i and "finding" in i for i in out)
    assert any("3.2" in i and "number" in i for i in out)


def test_build_docx_md_and_folders(proj, tmp_path):
    out = tmp_path / "outline_out"
    res = outline_build.build(_write(tmp_path, _outline()), proj, out)
    import docx
    d = docx.Document(res["docx"])
    text = "\n".join(p.text for p in d.paragraphs)
    for s in ("2.1 Cohorts and evaluation", "3.1 Cohorts separate in the backbone representation",
              "（队列在骨干表示中分开）", "写作重点", "写作要点", "第一段", "图 / 表", "相关代码", "措辞边界",
              "src/eval.py（推测）"):
        assert s in text, s
    md = Path(res["md"]).read_text(encoding="utf-8")
    assert "## 3.1 Cohorts separate" in md
    r31 = out / "3_Results/3.1_Domain_shift"
    assert (r31 / "figures/fig2.pdf").is_file() and (r31 / "figures/fig2.source.json").is_file()
    assert (r31 / "tables/T1.csv").is_file() and (r31 / "tables/T1.md").is_file()
    assert (r31 / "captions/fig2.md").is_file() and (r31 / "code/fig2.py").is_file()
    assert "src/eval.py（推测）" in (r31 / "code/code.md").read_text(encoding="utf-8")
    assert (out / "2_Methods/2.1_Cohorts/tables/T1.csv").is_file()
    cap3 = (out / "3_Results/3.2_Internal/captions/fig3.md").read_text(encoding="utf-8")
    assert "图 3" in cap3  # caption section extracted from the combined captions file
    assert (proj / "out/figures/main/fig2.pdf").is_file()  # copies, not moves


def test_build_refuses_output_inside_project(proj, tmp_path):
    with pytest.raises(ValueError, match="outside the project"):
        outline_build.build(_write(tmp_path, _outline()), proj, proj / "outline")


def test_build_refuses_failing_outline(proj, tmp_path):
    o = _outline()
    o["numbers"][0]["text"] = "0.984"
    with pytest.raises(RuntimeError, match="outline_check"):
        outline_build.build(_write(tmp_path, o), proj, tmp_path / "o2")


def test_number_forms():
    m = outline_check._matches
    assert m("1/3", 0.3333333333) and not m("1/3", 0.34)
    assert m("+0.017", 0.017457) and not m("+0.017", -0.017457) and m("−0.019", -0.019026)
    assert m("92.7%", 0.927318) and m("13,859", 13859)
    assert m("0.047", -0.0472, magnitude=True) and not m("0.047", -0.0472)  # "低约 0.047" = magnitude
    assert outline_check.NUM.findall("P = 1/3，差值 +0.00127") == ["1/3", "+0.00127"]
