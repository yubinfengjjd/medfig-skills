---
name: medical-sci-introduction
description: "Use when drafting or revising the Introduction of a medical SCI manuscript after its Methods, Results and figure legends are written, such as 写引言、Introduction 撰写、SCI 引言中英对照、修改已有引言、补引言文献和 PMID. Produces an English Introduction (background, literature review, research gap, contribution, significance) with Chinese parallel text, verified PMID citations (≥10, ≥5 in the review) without disclosing any results, plus a Chinese 核查说明 with compliance notes and a citation verification table. Do not use for Methods, Results, Discussion, Abstract or figure legends (use medical-sci-methods / medical-sci-results / medical-sci-legends), outline building or drawing figures."
---

# 医学 SCI 引言写作

依据已完成的大纲、Methods、Results 和图注，撰写或修订英文 Introduction，附中文对照和中文核查说明。引言从研究背景逐步聚焦到研究空白，再引出本研究的问题、做法与意义；每条引用都经过公开数据库核验，正文不出现任何结果。

## 必读材料（每次起草或修订都执行）

不凭技能名称或上次任务的摘要开始写作。按顺序完整读取：

1. [原始提示词](references/original-introduction-prompt.md)：基础角色与写作要求，以及作者确认的改动。
2. [已确认写作规则](references/writing-rules.md)：对原始提示词的细化，冲突时以它为准。
3. [期刊语言与格式规范](references/journal-style.md)：语言、引用格式、期刊层级、篇幅、文件格式。
4. [判断示例](references/examples.md)：只学判断方式，不迁移具体内容。
5. 项目目录下的 `Introduction_作者决定.md`（如存在）：已裁决事项直接沿用。

当前用户指令优先于以上材料。

## 工作流程

1. **前置检查**：确认 Methods、Results 和图注都已写完（规则第 1 节）。缺任一份时先告诉作者并建议补齐；作者要求继续才往下做。同时记录目标期刊是否指定，未指定则采用默认策略。
2. **提取研究要素**：从大纲和 Methods 提取研究领域、临床问题、数据与设计、方法、研究问题和措辞边界；从 Results 和图注只核对每个研究问题都有对应分析，不摘取数字或结论（规则第 1、3 节）。
3. **建文献池**：收集手稿已有引用的 PMID，逐条核对；不足时按论证需要检索 PubMed 补充（规则第 5 节）。PMID 用 curl 查 Europe PMC REST API，NCBI E-utilities 作备用；DOI 用 Crossref（带 `mailto` 参数）。curl 因 TLS 或证书错误失败时，改用带 OpenSSL 的 Python（urllib）发送同样的请求。读摘要确认支持关系后才放入候选。只提交公开主题词和标识，不提交稿件正文、数据或代码。中间结果放在临时目录。
4. **搭论证线**：先在内部列出五个层次各自的论点和对应引用（规则第 2 节），确认研究空白有依据、本研究的问题与 Results 实际分析一一对应（规则第 4 节）、PMID 数量达到门槛。
5. **撰写英文**：4–6 段，无小标题；结果规避按规则第 3 节，措辞按规则第 4 节和 journal-style 第 1 节。
6. **撰写中文对照**：逐段重组为规范中文，事实、引用和限定与英文一致（规则第 6 节）。
7. **复核**：用本地脚本统计词数和引用数，再按下方“交付前检查”逐项确认，写核查说明（规则第 7 节）。

默认在当前会话中完成，不派出子代理。

## 项目约定（检测到 PROJECT.md 时）

从工作目录或材料路径向上查找 `PROJECT.md`。找到时按 medpaper-pipeline 的项目目录约定（`medpaper-pipeline/references/project-layout.md`）执行，用户另行指定的路径优先：

- 默认材料：03_outline/ 的大纲、04_manuscript/ 下的 Methods、Legends、Results 成稿。
- 输出到 `04_manuscript/Introduction/`，文件名固定为 Introduction_EN.md、Introduction_ZH.md、Introduction_EN_ZH.md、Introduction_核查说明.md，不加项目前缀或版本号。
- 已有同名成稿时，先把旧文件移到 `_archive/<今天日期>/04_manuscript/Introduction/`，再写新文件；更新 `PROJECT.md` 状态表中 Introduction 一行（状态 `待确认`、版本、日期）并在变更记录追加一行。
- 作者决定读 `04_manuscript/作者决定.md` 的“通用”和“Introduction”两节，代替单独的 `Introduction_作者决定.md`；新裁决追加到“Introduction”节。
- 审查、盲测、对照稿等过程文件放 `_process/Introduction/<YYYY-MM-DD>_<描述>/`，不放成稿目录。

没有 `PROJECT.md` 时保持下文原有行为，不新建它。

## 一致性防线（检测到 PROJECT.md 时）

按 `medpaper-pipeline/references/consistency-guards.md` 执行：

- 写作前读项目根的 `口径表.md`：术语用规范名，不用禁用别名；量的定义和关键计数照口径表写。图表标签与规范名不同时，在图注或正文中括注对应（如“目标标签拟合参照（图中 R2 (oracle)）”）。
- 材料冲突按统一权威顺序取舍：代码与回执 > source.json 数值与 definitions > 成图图面 > Methods > 详细图注 > 大纲与规格叙述 > 已写成的下游稿件。本技能其他章节中与此冲突的取舍规定，以此为准。
- 研究问题和设计描述中的术语一律取口径表的规范名；引用口径表关键计数时照抄规范写法。
- 发现冲突时登记到 `_process/冲突台账.md`（写明双方原文、出处、源头阶段和应改的上游文件）。事实类（有代码或数据作证：拟合分区、符号、计数、分组、量的定义、panel 字母）先把被改文件备份到 `_archive/<日期>/`，再直接修改上游文件和已受影响的下游文件，同步口径表；口径类（措辞强弱、结论范围、术语选择）和图面类只登记，等阶段关口由作者裁决。
- 核查说明的“需作者裁决事项”只列台账 ID 和一句摘要；台账中已修复或已裁决的事项不重复上报。
- 交付前依次运行（用 `python -X utf8` 运行脚本（PATH 上的 `python` 若是 Windows 商店空壳，改用真实解释器的完整路径））：`<medpaper-pipeline>/scripts/consistency_check.py <项目根>`（禁用别名与关键计数，命中项修掉或登记），再运行 `<medpaper-pipeline>/scripts/manuscript_check.py introduction <本稿 EN 文件> --zh <本稿 ZH 文件> --results 04_manuscript/Results/Results_EN.md`，ERROR 先修掉，WARN 逐条在核查说明中说明（脚本口径见 consistency-guards 第 5 节）。

## 输出

- 单独保存时，输出到用户指定目录：`Introduction_EN.md`、`Introduction_ZH.md`、`Introduction_EN_ZH.md`、`Introduction_核查说明.md`（每次都输出）。
- 只在对话中交付时，先给英文，再给中文，核查说明放在独立说明块。
- 交付时报告英文词数（口径见 journal-style 第 4 节）、PMID 引用总数及综述层次内的 PMID 数、降级引用数，以及需作者裁决的事项条数。
- 不在稿件目录留下处理脚本或检索缓存；不修改技能目录、全局配置、大纲、Methods、Results、图注或数据。

## 交付前检查

- [ ] 前置稿件齐全，或缺失情况已告知作者并写入核查说明第 1 部分。
- [ ] 五个层次（背景、综述、空白、本研究贡献、意义）都出现；4–6 段，无小标题、列表、路标式连接或“本文结构如下”。
- [ ] 设计部分约 150 词以内，没有训练阶段、标签映射、划分规则、比较器清单或评估层级；各项分析已归并为 2–3 个研究问题，没有逐项罗列 Results 目录；没有 Methods 内部构造名。
- [ ] 每个空白句点名所引研究的具体局限；至少一句与最接近的现有方法的具体区别；意义句写明对谁、在哪个环节有用；临床背景引临床或综述来源，核心空白尽量各有 2 篇直接相关引用（不足时如实说明，不凑数）。
- [ ] 否定式空白句（do not establish 等）≤2 处，相邻段落不以同一句式收尾；每个 PMID 紧跟所支持的研究或论断；综述中以作者名开头的句子 ≤1/3。
- [ ] 没有逐段的免责式范围声明（“不意味着临床获益”“不在本研究范围内”等），全文最多 1 句。
- [ ] 段末没有复述性总结句；研究问题中的分析对象与 Results 实际检验的量一致。
- [ ] 没有本研究的数字、方向性结论或 demonstrate/reveal/show that 后接本研究发现；逐句对照过 Results 稿，没有借来的数字或判断。
- [ ] 引言提出的每个问题都有 Results 中的对应分析；没有材料之外的研究问题、方法、结论或 Discussion 层面的推测。
- [ ] 研究空白由所引研究的局限推出，或有检索记录支撑；没有 no study has ever、novel、first、breakthrough 等表述，“to our knowledge”最多一处且有检索依据。
- [ ] 带已核验 PMID 的不同文献 ≥10 篇，综述层次内 ≥5 篇；每条 PMID 的题名、第一作者、期刊、年份已核对，摘要支持所引论断；背景数字与所引摘要一致。
- [ ] 引用格式为纯文本 `(PMID: …)`；确无 PMID 的按 DOI > 出版页 URL > arXiv 降级并列入核查说明；没有占位、猜测或未核验的标识。
- [ ] 没有写影响因子或分区；没有声称符合某具体期刊的要求（用户未指定时）。
- [ ] 英文 ≤1,000 词（或更严格的期刊限制），单句不超过 50 词；美式拼写；术语和缩写与 Methods 一致；没有内部标识或工程词汇。
- [ ] 中文对照按中文语序重组，事实、引用、限定与英文一致，引用用全角括号。
- [ ] 核查说明四部分齐全：需作者裁决事项、逐条合规说明（含目标期刊策略）、引用核验表（含 PMID 计数）、检索记录。
