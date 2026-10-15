"""Deterministic pre-delivery checks for medical-sci-* manuscript sections.

Usage:
  python -X utf8 manuscript_check.py <section> <EN.md> [--zh ZH.md] [--results Results_EN.md] [--json]
  section: methods | legends | results | introduction | discussion | abstract

Checks the countable rules written in each skill's writing-rules / journal-style: word count,
sentence length, banned words, template-phrase frequency, citation format, PMID threshold, EN/ZH
PMID and number parity, numbers against Results, figure-panel letter case.
ERROR = rule violation to fix; WARN = judgment call, record the decision in the 核查说明.
Exit code 1 if any ERROR. Argument quality, citation support and factual correctness are not checked.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

E, W = "ERROR", "WARN"

# (level, rule id, regex, max allowed occurrences, message); max 0 = any occurrence is a hit
COMMON = [
    (E, "numeric-citation", r"\[\d+(?:\s*[,–-]\s*\d+)*\]", 0, "数字式引用；改为 (PMID: …)"),
    (E, "hype", r"\b(?:novel|unprecedented|breakthrough|groundbreaking|paradigm-shifting|for the first time)\b", 0,
     "宣传性或首次性用语"),
    (W, "british-spelling", r"\b(?:tumour|oedema|haemorrhage|modelling|centre|colour|analys(?:e|ed|ing)|randomised|"
     r"normalised|behaviour|labelled|optimise[sd]?|generalis\w+)\b", 0, "非美式拼写（专有名称、引用题名除外）"),
    (W, "engineering-term", r"\b(?:audit\w*|ledger|firewall|frozen endpoint|seed-0)\b", 0, "工程或内部词汇"),
]

PROFILES = {
    "abstract": dict(words=(None, 250, E), sent=(40, 50, E), rules=[
        (E, "overclaim", r"\b(?:prove[sd]?|proven|clearly|undoubtedly|clinically deployable)\b", 0,
         "摘要结论强度超越证据"),
        (E, "abstract-reference", r"(?:PMID|DOI|URL|arXiv)\s*:|\b(?:Fig\.|Figure|Table)\s*S?\d|\[citation needed\]", 0,
         "摘要默认不带引用、图表号或引用占位"),
    ]),
    "methods": dict(words=(2500, 3000, W), sent=(40, 50, W), rules=[]),
    "legends": dict(words=None, legend_words=150, sent=(35, 45, E), rules=[
        (E, "comparison-word", r"\b(?:superior|outperform\w*|favou?r(?:s|ed)?|advantage)\b", 0,
         "比较方向词；改为 positive/negative 或写出数值"),
        (W, "disclaimer", r"\b(?:do(?:es)? not establish|not significant overall|not clinical)\b", 0, "通用免责句"),
    ]),
    "results": dict(words=(3500, 4000, W), sent=(45, 55, E), long_share=0.05, rules=[
        (E, "sentence-opener", r"(?:^|(?<=[.!?]\s))(?:First|Then|Next|Finally|Moreover|Furthermore|In addition|"
         r"Notably|Interestingly|Importantly)\b", 0, "句首串联或强调词"),
        (E, "section-number", r"\bSection \d|\d\.\d+ ?节|上一节", 0, "正文出现节号"),
        # 风格上限：规则写得较死，实际交付稿可能因体量自然超出，按警告报告，由作者定夺
        (W, "therefore-family", r"\b(?:therefore|thus|consequently)\b", 6, "therefore/thus/consequently 全文 ≤6"),
        (W, "rather-than", r"\brather than\b", 6, "rather than 全文 ≤6"),
        (W, "coexisted", r"\bcoexist(?:ed|s)?\b", 3, "coexisted 同一词 ≤3"),
        (W, "accompanied", r"\baccompanied\b", 3, "accompanied 同一词 ≤3"),
        (W, "separating", r"\bseparating\b", 3, "separating 同一词 ≤3"),
    ]),
    "introduction": dict(words=(None, 1000, E), sent=(40, 50, E), min_pmid=10, rules=[
        (E, "to-our-knowledge", r"\bto our knowledge\b", 1, "“to our knowledge” 全文 ≤1"),
        (E, "negative-gap", r"\b(?:do|does|did) not (?:establish|show|demonstrate|determine)\b|\bcannot\b|\bneither\b", 2,
         "否定式空白句 ≤2"),
        (E, "no-study-has", r"\bno (?:previous |prior )?stud(?:y|ies) ha(?:s|ve)\b", 0, "无法核验的“no study has”"),
        (E, "scope-disclaimer", r"\bwithout implying\b|\b(?:outside|beyond) (?:the |this )?(?:study's |present )?scope\b", 1,
         "免责式范围声明全文 ≤1"),
        (E, "roadmap", r"\b(?:rest|remainder) of this (?:paper|article)\b|\bis organized as follows\b", 0, "路标式结构说明"),
        (W, "result-verb", r"\bwe (?:show|demonstrate|reveal|confirm|establish)\b", 0, "可能提前披露结果"),
    ]),
    "discussion": dict(words=(800, 1500, W), sent=(40, 50, E), rules=[
        (E, "overclaim", r"\b(?:prove[sd]?|proven|clearly|undoubtedly)\b", 0, "超越证据的强度词"),
        (W, "confirm", r"\bconfirm(?:s|ed)? (?:that|our)\b", 0, "confirm 指本研究假设时改为 support/indicate"),
        (E, "to-our-knowledge", r"\bto our knowledge\b", 1, "“to our knowledge” 全文 ≤1"),
        (E, "agrees-with", r"\bagree(?:s|d)? with\b", 2, "agrees with ≤2"),
        (E, "extends", r"\bextend(?:s|ed)?\b", 2, "extends ≤2"),
        (E, "consistent-with", r"\b(?:is|are|was|were) consistent with\b", 2, "is consistent with ≤2"),
        (E, "contrasts-with", r"\bcontrast(?:s|ed)? with\b", 2, "contrasts with ≤2"),
        (E, "would-test", r"\bwould (?:test|distinguish|address|clarify|determine|separate)\b", 3, "检验建议 ≤3"),
        (E, "negative-boundary", r"\b(?:does|do|did) not (?:imply|establish|identify|mean|indicate|demonstrate|prove|"
         r"ensure|guarantee|represent)\b|\bcannot be (?:assumed|interpreted|attributed|extended|treated|inferred)\b|"
         r"\bpreclude[sd]?\b", 5, "否定式限定全文 ≤5"),
        (E, "empty-future", r"\bfurther (?:studies|research|work) (?:is|are) (?:needed|warranted|required)\b", 0,
         "空泛的未来方向"),
        (E, "section-mention", r"\b(?:the|our) (?:Introduction|Methods|Results)\b|\bin the (?:Methods|Results) section\b", 0,
         "正文提及其他章节"),
        (E, "we-found-opener", r"(?:^|(?<=[.!?]\s))(?:We found|Our (?:results|findings))\b", 4,
         "以 We found / Our results 开头 ≤4"),
        (W, "citation-needed", r"\[citation needed\]", 0, "引用缺口，须列入核查说明第 1 部分"),
    ]),
}
CITE_IN_PARENS = re.compile(r"[(（][^()（）]*?(?:PMID|DOI|URL|arXiv)\s*:[^()（）]*[)）]")
FIG_REF = re.compile(r"[(（][^()（）]*?(?:Fig\.|Figure|Table|Supplementary|图\s*\d|表\s*\d|补充图)[^()（）]*[)）]")
PMID = re.compile(r"PMID:\s*(\d+)")
BAD_PMID = re.compile(r"PMID:\s*(?!\d{6,9}\b)\S+|PMID\s+\d|PMID：")
NUM = re.compile(r"(?<![\w.])[−-]?\d+(?:,\d{3})*(?:\.\d+)?%?")
PANEL = re.compile(r"\b(?:Fig\.|Figure|Supplementary Fig\.)\s*S?\d+([A-Ha-h])\b")


def strip_md(text):
    """Body text only: drop headings, emphasis markers and table lines."""
    lines = [l for l in text.replace("\r\n", "\n").split("\n") if not l.lstrip().startswith(("#", "|"))]
    return re.sub(r"\*\*|__", "", "\n".join(lines))


def words_of(text):
    t = CITE_IN_PARENS.sub(" ", FIG_REF.sub(" ", text))
    t = re.sub(r"\((?:[a-h](?:[–-][a-h])?)\)", " ", t)  # 段落级/panel 标签不算词
    return len(t.split())


def sentences(text):
    out = []
    for para in [p for p in text.split("\n") if p.strip()]:
        p = CITE_IN_PARENS.sub("", FIG_REF.sub("", para))
        p = re.sub(r"\b(?:e\.g|i\.e|et al|vs|Fig|approx|Dr|No)\.", lambda m: m.group(0)[:-1], p)
        out += [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(“\"])", p) if s.strip()]
    return out


def numbers(text):
    t = CITE_IN_PARENS.sub(" ", FIG_REF.sub(" ", text))
    return [n.replace("−", "-").replace(",", "") for n in NUM.findall(t)]


def abstract_numbers(text):
    """Chinese prose may touch a signed number; ASCII identifiers may not."""
    t = CITE_IN_PARENS.sub(" ", FIG_REF.sub(" ", text))
    found = re.findall(r"(?<![A-Za-z0-9_.])[−-]?\d+(?:,\d{3})*(?:\.\d+)?%?", t)
    return [n.replace("−", "-").replace(",", "") for n in found]


def abstract_body(text):
    """Exclude ancillary sections from abstract length; keep them for claim checks."""
    return re.split(r"^#{1,6}\s*(?:Keywords|Highlights|关键词|研究亮点|亮点)\s*#*\s*$", text,
                    maxsplit=1, flags=re.M | re.I)[0]


def check(section, en_path, zh_path=None, results_path=None, abstract_limit=250, allow_abstract_references=False):
    prof = PROFILES[section]
    raw = Path(en_path).read_text(encoding="utf-8-sig")
    body = strip_md(abstract_body(raw) if section == "abstract" else raw)
    claims = strip_md(raw) if section == "abstract" else body
    out = []

    def add(level, rule, msg, ctx=""):
        out.append({"level": level, "rule": rule, "msg": msg, "context": ctx[:160]})

    # length
    if section == "legends":
        for leg in re.split(r"\n(?=\*\*(?:Supplementary )?(?:Figure|Table) )", raw.replace("\r\n", "\n")):
            m = re.match(r"\*\*((?:Supplementary )?(?:Figure|Table) S?\d+)", leg)
            if m and m.group(1).split()[-2] != "Table" and words_of(leg) > prof["legend_words"]:
                add(W, "legend-length", f"{m.group(1)} 英文 {words_of(leg)} 词，超过 {prof['legend_words']}")
        if re.search(r"\n\s*\n\*\*(?:Supplementary )?(?:Figure|Table)", raw.replace("\r\n", "\n")):
            add(E, "legend-blank-line", "图注之间有空行")
    else:
        n = words_of(body)
        lo, hi, lvl = prof["words"]
        if section == "abstract":
            hi = abstract_limit
        if (lo and n < lo) or (hi and n > hi):
            add(lvl, "word-count", f"英文正文 {n} 词，目标 {lo or '—'}–{hi}")
    # sentence length
    soft, hard, lvl = prof["sent"]
    sents = sentences(body)
    long_ = [s for s in sents if len(s.split()) > soft]
    for s in sents:
        if len(s.split()) > hard:
            add(lvl, "sentence-hard", f"单句 {len(s.split())} 词，超过硬上限 {hard}", s)
    if "long_share" in prof and sents and len(long_) / len(sents) > prof["long_share"]:
        add(E, "sentence-share", f"超过 {soft} 词的句子占 {len(long_)}/{len(sents)}，超过 {prof['long_share']:.0%}")
    # phrase rules
    for level, rule, pat, mx, msg in COMMON + prof["rules"]:
        if section == "abstract" and rule == "abstract-reference" and allow_abstract_references:
            continue
        hits = [m for m in re.finditer(pat, claims, re.I if rule not in ("sentence-opener", "we-found-opener") else 0)]
        if len(hits) > mx:
            ctx = "; ".join(claims[max(0, h.start() - 30):h.end() + 30].replace("\n", " ") for h in hits[:3])
            add(level, rule, f"{msg}（{len(hits)} 处）", ctx)
    # citations
    for m in BAD_PMID.finditer(claims):
        add(E, "pmid-format", "PMID 格式应为 (PMID: 12345678)", claims[max(0, m.start() - 20):m.end() + 20])
    pmids = PMID.findall(claims)
    if prof.get("min_pmid") and len(set(pmids)) < prof["min_pmid"]:
        add(E, "pmid-count", f"不同 PMID {len(set(pmids))} 篇，少于 {prof['min_pmid']}")
    dup = [p for p, c in Counter(pmids).items() if c > 1]
    if dup and section in ("introduction", "discussion"):
        add(W, "pmid-repeat", f"同一 PMID 重复引用：{', '.join(dup)}（一般只在最相关处引一次）")
    # panel letter case
    cases = Counter("upper" if c.isupper() else "lower" for c in PANEL.findall(body))
    if len(cases) > 1:
        add(W, "panel-case", f"图 panel 字母大小写混用：{dict(cases)}（应与 Results / 图面一致）")
    # EN/ZH parity
    if zh_path:
        zh = strip_md(Path(zh_path).read_text(encoding="utf-8-sig"))
        a, b = Counter(pmids), Counter(PMID.findall(zh))
        if a != b:
            add(E, "zh-pmid", f"中英 PMID 不一致：仅英文 {sorted((a - b).elements())}，仅中文 {sorted((b - a).elements())}")
        extract_numbers = abstract_numbers if section == "abstract" else numbers
        ne = Counter(x for x in extract_numbers(claims) if re.search(r"[.%]|\d{3,}", x))
        nz = Counter(x for x in extract_numbers(zh) if re.search(r"[.%]|\d{3,}", x))
        if ne - nz:
            add(W, "zh-number", f"英文有、中文无的数字：{sorted((ne - nz).elements())[:12]}")
        if section == "abstract" and nz - ne:
            add(W, "en-number", f"中文有、英文无的数字：{sorted((nz - ne).elements())[:12]}")
        if re.search(r"\((?:PMID|DOI)", zh):
            add(E, "zh-paren", "中文稿引用应用全角括号（PMID: …）")
    # numbers against Results
    if results_path and section in ("discussion", "introduction", "abstract"):
        extract_numbers = abstract_numbers if section == "abstract" else numbers
        res = set(extract_numbers(strip_md(Path(results_path).read_text(encoding="utf-8-sig"))))
        cand = [x for x in extract_numbers(claims) if re.search(r"[.%]", x)]
        miss = sorted({x for x in cand if x not in res and (section == "abstract" or x.lstrip("-") not in res)})
        if section == "introduction" and cand:
            add(W, "intro-number", f"引言出现小数或百分比，确认不是本研究结果：{cand[:10]}")
        elif miss:
            add(E, "number-not-in-results", f"Results 中找不到的数字：{miss}（他人文献数字须在核查说明注明出处）")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("section", choices=sorted(PROFILES))
    ap.add_argument("en")
    ap.add_argument("--zh")
    ap.add_argument("--results")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-words", type=int, default=250, help="Abstract body word limit (default 250)")
    ap.add_argument("--allow-abstract-references", action="store_true", help="Only when author/journal explicitly requires abstract references")
    a = ap.parse_args()
    if a.max_words < 1:
        ap.error("--max-words must be positive")
    res = check(a.section, a.en, a.zh, a.results, a.max_words, a.allow_abstract_references)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        for r in res:
            print(f"[{r['level']}] {r['rule']}: {r['msg']}" + (f"  …{r['context']}…" if r["context"] else ""))
        print(f"{sum(r['level'] == E for r in res)} error(s), {sum(r['level'] == W for r in res)} warning(s)")
    sys.exit(1 if any(r["level"] == E for r in res) else 0)


if __name__ == "__main__":
    main()
