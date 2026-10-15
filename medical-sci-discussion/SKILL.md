---
name: medical-sci-discussion
description: "Use when drafting or revising the Discussion of a medical SCI manuscript after its Methods, Results, figure legends and Introduction are all written, such as 写讨论、Discussion 撰写、SCI 讨论中英对照、修改已有讨论、讨论补文献和 PMID、写局限性. Produces an English Discussion (summary, interpretation, comparison with literature, contribution, limitations and future work, short conclusion) with Chinese parallel text, verified PMID citations, no new results and no claims beyond the evidence, plus a Chinese 核查说明 with a finding-to-discussion map and citation table. Refuses to start until all four prerequisite sections exist. Do not use for Methods, Results, Introduction, Abstract or figure legends (use medical-sci-methods / -results / -introduction / -legends), outline building or drawing figures."
---

# 医学 SCI 讨论写作

依据已完成的 Results、图注、Methods 和 Introduction，撰写或修订英文 Discussion，附中文对照和中文核查说明。Discussion 回到 Introduction 提出的问题，选 2–4 个核心发现深入解释、与最接近的已有研究对比，写明本研究补充了什么，诚实陈述局限并给出可操作的未来方向；不复述 Results，不超越证据。

## 必读材料（每次起草或修订都执行）

不凭技能名称或上次任务的摘要开始写作。按顺序完整读取：

1. [原始提示词](references/original-discussion-prompt.md)：基础角色与写作要求，以及作者确认的改动。
2. [已确认写作规则](references/writing-rules.md)：对原始提示词的细化，冲突时以它为准。
3. [期刊语言与格式规范](references/journal-style.md)：语言、引用格式、期刊层级、篇幅、文件格式。
4. [判断示例](references/examples.md)：只学判断方式，不迁移具体内容。
5. 项目目录下的 `Discussion_作者决定.md`（如存在）：已裁决事项直接沿用。

当前用户指令优先于以上材料，但不能跳过前置检查。

## 工作流程

1. **前置检查（硬门槛）**：确认 Methods、Results、图注、Introduction 四份都存在且完整（规则第 1 节）。缺任一份或有占位未补时，列出缺项（文件、段落）和建议使用的技能，然后停止，不起草任何段落，作者坚持也不写。目标期刊、引用格式缺失不阻塞，记录将采用默认策略。
2. **通读与提取**：读 Introduction 的研究空白与问题、Results 全文与图注、Methods 的设计和数据条件；列出每个研究问题对应的 Results 发现、例外和不利结果（规则第 3 节）。
3. **选重点、搭论证线**：在内部选出 2–4 个核心发现，为每个写好“发现 → 解释 → 依据 → 文献对比 → 含义”；列出局限清单（规则第 7 节）。先拟好核查说明第 3 部分的对应表，再动笔。
4. **建文献池**：先复用 Introduction 和 Methods 已核验的文献，逐条重新核对；不足时按论证需要检索 PubMed 补充（规则第 8 节）。PMID 用 curl 查 Europe PMC REST API，NCBI E-utilities 作备用；DOI 用 Crossref（带 `mailto` 参数）。curl 因 TLS 或证书错误失败时，改用带 OpenSSL 的 Python（urllib）发送同样的请求。读摘要确认支持关系后才放入候选。只提交公开主题词和标识，不提交稿件正文、数据或代码。中间结果放在临时目录。
5. **撰写英文**：默认无小标题，五部分加结论段（规则第 2 节）；推断强度按规则第 4 节，语言按 journal-style 第 1 节。
6. **撰写中文对照**：逐段重组为规范中文，事实、数字、引用、对冲强度与英文一致（规则第 9 节）。
7. **复核**：用本地脚本统计词数和引用数，逐个数字对照 Results 原文，再按下方“交付前检查”逐项确认，写核查说明（规则第 10 节）。

默认在当前会话中完成，不派出子代理。

## 项目约定（检测到 PROJECT.md 时）

从工作目录或材料路径向上查找 `PROJECT.md`。找到时按 medpaper-pipeline 的项目目录约定（`medpaper-pipeline/references/project-layout.md`）和一致性防线（`medpaper-pipeline/references/consistency-guards.md`）执行，用户另行指定的路径优先：

- 前置检查看 `04_manuscript/` 下的 Methods、Legends、Results、Introduction 成稿；`PROJECT.md` 状态表中这四个阶段任一为 `未开始`、`进行中` 或 `需返工` 时，视为前置未完成并停止；为 `待确认` 时可以继续，但在核查说明第 1 部分写明哪些前置稿件尚未经作者确认。
- 默认材料另含 03_outline/ 的大纲、项目根 `口径表.md`、`_process/冲突台账.md`。术语与计数以口径表为准；发现的新冲突登记到冲突台账，核查说明只列台账 ID 和一句摘要。
- 输出到 `04_manuscript/Discussion/`，文件名固定为 Discussion_EN.md、Discussion_ZH.md、Discussion_EN_ZH.md、Discussion_核查说明.md，不加项目前缀或版本号。
- 已有同名成稿时，先把旧文件移到 `_archive/<今天日期>/04_manuscript/Discussion/`，再写新文件；更新 `PROJECT.md` 状态表中 Discussion 一行（技能、状态 `待确认`、版本、日期）并在变更记录追加一行。
- 作者决定读 `04_manuscript/作者决定.md` 的“通用”和“Discussion”两节，代替单独的 `Discussion_作者决定.md`；没有“Discussion”节时在文末新增，新裁决追加到该节。
- 交付前依次运行（用 `python -X utf8` 运行脚本（PATH 上的 `python` 若是 Windows 商店空壳，改用真实解释器的完整路径））：`<medpaper-pipeline>/scripts/consistency_check.py <项目根>`（禁用别名与关键计数，命中项修掉或登记），再运行 `<medpaper-pipeline>/scripts/manuscript_check.py discussion <本稿 EN 文件> --zh <本稿 ZH 文件> --results 04_manuscript/Results/Results_EN.md`，ERROR 先修掉，WARN 逐条在核查说明中说明（脚本口径见 consistency-guards 第 5 节）。
- 审查、盲测、对照稿等过程文件放 `_process/Discussion/<YYYY-MM-DD>_<描述>/`，不放成稿目录。

没有 `PROJECT.md` 时保持下文原有行为，不新建它。

## 输出

- 单独保存时，输出到用户指定目录：`Discussion_EN.md`、`Discussion_ZH.md`、`Discussion_EN_ZH.md`、`Discussion_核查说明.md`（每次都输出）。
- 只在会话中交付时，先给英文，再给中文，核查说明放在独立说明块。
- 交付时报告英文词数（口径见 journal-style 第 4 节）、展开讨论的核心发现数、局限条数、引用总数及 PMID 数、降级引用数、`[citation needed]` 数，以及需作者裁决的事项条数。
- 前置检查未通过时，只输出缺项清单，不生成任何稿件文件。
- 不在稿件目录留下处理脚本或检索缓存；不修改技能目录、全局配置、大纲、Methods、Results、图注、Introduction 或数据（项目约定下按一致性防线修复事实类冲突除外）。

## 交付前检查

- [ ] Methods、Results、图注、Introduction 四份齐全且无占位；否则未起草。
- [ ] 五部分（总结、解释、文献对比、贡献、局限与未来方向）都出现，加 2–4 句结论段；默认无小标题；结论段没有新内容、新引用或新数字。
- [ ] 总结段一句回到 Introduction 的问题，不重复 Introduction 背景，约 200 词以内。
- [ ] 只展开 2–4 个核心发现；Introduction 的每个研究问题都有回应；与主要结论相反的发现、例外队列至少一句如实讨论。
- [ ] 每段最多 1–2 个数字；Discussion 中每个数字与 Results 原文一致，没有 Results 以外的结果、换算或趋势表述。
- [ ] 每个解释句能指出依据（本研究分析或 PMID）；无依据的只写成假设并说明需要什么检验；没有无依据的机制。
- [ ] 每个核心发现段（含最差队列等例外）至少有 1 句给出候选原因的真正解释，不只是换说法重述；复述 Results 的句子不超过约三分之一，次要分析不顺带搬入；否定式限定句每段 ≤1、全文 ≤5。
- [ ] 每处文献比较让读者看出是一致、不同还是扩展；agrees with / extends / is consistent with / contrasts with 各 ≤2 次，“扩展”只用于对方检验过子集的情况；转述他人发现不超过其摘要强度；没有为凑对话新引的弱关联文献。
- [ ] 解释段末没有泛化复述句，以 Together / therefore 收尾的段落 ≤1；First/Second 式路标只用于局限段。
- [ ] “would test / distinguish”式检验建议 ≤3 处；正文不提及其他章节（the Introduction / Methods / Results）。
- [ ] 没有 prove、confirm（本研究假设）、establish、for the first time、novel、clearly；没有观察性设计下的因果和定位动词；对冲不叠用；“to our knowledge”最多一处。
- [ ] 每个核心发现至少一处与最接近已有研究的具体比较（对方条件与发现、本研究不同之处、可核对的可能原因）；没有笼统的 “consistent with previous studies”；只比较定义一致的数字。
- [ ] 贡献与 Introduction 的空白一一对应，写明对谁、在哪个环节有用；临床意义没有材料不支持的外推，“需前瞻验证”只写一次。
- [ ] 局限 ≥3 条，按影响排序，每条写明影响哪个结论及本研究的应对或未来方向；覆盖设计、样本或数据、分析方法中的至少两类；不利结果没有回避；没有无依据的 “robust” 找补；没有 “further studies are needed” 式空话。
- [ ] 每条 PMID 的题名、第一作者、期刊、年份已核对，摘要支持所引论断；他人的数字出自所引文献；PMID 紧跟所支持的研究；`[citation needed]` 只在检索后确无可核实文献时使用并列入核查说明。
- [ ] 引用格式为纯文本 `(PMID: …)`；降级引用按 DOI > URL > arXiv；没有影响因子或分区；没有声称符合某具体期刊（用户未指定时）。
- [ ] 英文约 800–1,500 词（或更严格的期刊限制），单句不超过 50 词；美式拼写；术语、缩写、模型和队列名称与 Methods、Results、口径表一致；没有内部标识或工程词汇。
- [ ] 中文对照按中文语序重组，事实、数字、引用、对冲强度与英文一致，引用用全角括号。
- [ ] 核查说明五部分齐全：需作者裁决事项、合规说明、发现—讨论对应表（含数字核对）、引用核验表、检索记录。
