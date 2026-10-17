---
name: medical-sci-methods
description: "Use when drafting, continuing or revising the Methods section of a medical SCI manuscript from an author-confirmed outline plus the actual analysis code, configuration and execution receipts, such as 医学方法部分写作、Methods 中英对照、按节续写“下一节”、修改已有 Methods 稿、把分析脚本转写成论文方法. Produces English Methods with paragraph-level Chinese parallel text, verified PMID citations and a 核查说明 when triggered. Do not use for building the outline itself (use medfig-outline), for Results, Discussion or figure legends, or for figure work."
---

# 医学 SCI Methods 写作

依据作者确认的主线和实际执行证据，撰写或修订正式英文 Methods，默认附逐段中文对照。正文只描述已实施且与主线相关的方法，并交代每项分析的目的。研究管理状态、未实施计划、实现层质控和空泛导航不进入正文。

## 必读材料（每次起草、修订或续写都执行）

不凭技能名称或上次任务的摘要开始写作。按顺序完整读取：

1. [原始提示词](references/original-methods-prompt.md)：基础角色与写作要求。
2. [已确认写作规则](references/writing-rules.md)：对原始提示词的细化，冲突时以它为准。各条规则的唯一出处都在这里。
3. [期刊语言与格式规范](references/journal-style.md)：拼写、缩写、引用格式、标准方法免引、软件与伦理声明、篇幅。
4. [判断示例](references/examples.md)：只学习判断方式，不迁移具体内容。
5. [ARS 写作质量指导摘录](references/ars-style-excerpt.md)：文风自查提示，摘自 academic-research-skills v3.23.0（CC BY-NC 4.0）。只读这份摘录，不读相邻 `academic-research-suite` 目录中的旧版 ARS，不启动 ARS 的整篇论文流水线，也不派出子代理。
6. 项目材料目录下的 `Methods_作者决定.md`（如存在）：作者已做的决定，按规则第 1 节沿用。

当前用户指令优先于以上材料。

## 工作流程

1. **定位**：读取大纲、Figure/Table 安排和已完成节段，确定本次范围、父节及对应科学问题。区分大纲中的方法内容和写作管理指令。属于修订任务时，同时读取旧稿和旧核查说明（规则第 8 节）。
2. **映射材料**：阅读相关代码、配置、实际调用和回执，在内部记录每项方法的目的、数据角色、关键参数、工具及来源。核对比例分母、门槛计数对象，以及各模型的训练和拟合范围（规则第 2 节“事实核对”）。发现大纲冲突或范围外分析时，按规则第 1 节处理。
3. **筛选正文**：按规则第 2 节判断每句的准入，按规则第 5 节把实现层质控移出正文。
4. **核验引用**：先判断哪些对象需要引用、哪些属于标准方法免引（journal-style 第 3 节），再逐项核验真实性、支持关系和覆盖（规则第 4 节）。PMID 先查 Europe PMC REST API，NCBI E-utilities 作备用；DOI 用 Crossref，请求带 `mailto` 参数并顺序发送、间隔约 1 秒。每个请求限时；遇到限流（HTTP 429）先等待约 30 秒再重试一次；同一条失败两次即记为“暂未核验”，不阻塞写作。使用正式出版页 URL 的引用，直接打开出版页核对（规则第 4 节）。
5. **撰写**：每项分析以目的句开头，然后写数据、实施和必要参数。先完成英文，再逐段写成规范的中文对照。修订任务按节整段重写，不打补丁。
6. **复核**：对照下方交付前检查逐项确认，再按规则第 7 节的触发清单决定是否输出核查说明。

## 项目约定（检测到 PROJECT.md 时）

从工作目录或材料路径向上查找 `PROJECT.md`。找到时按 medpaper-pipeline 的项目目录约定（`medpaper-pipeline/references/project-layout.md`）执行，用户另行指定的路径优先：

- 默认材料：03_outline/ 的大纲与分节证据、01_analysis/ 和 02_figures/ 中的代码与回执。
- 输出到 `04_manuscript/Methods/`，文件名固定为 Methods_EN.md、Methods_ZH.md、Methods_EN_ZH.md、Methods_核查说明.md，不加项目前缀或版本号。
- 已有同名成稿时，先把旧文件移到 `_archive/<今天日期>/04_manuscript/Methods/`，再写新文件；更新 `PROJECT.md` 状态表中 Methods 一行（状态 `待确认`、版本、日期）并在变更记录追加一行。
- 作者决定读 `04_manuscript/作者决定.md` 的“通用”和“Methods”两节，代替单独的 `Methods_作者决定.md`；新裁决追加到“Methods”节。
- 审查、盲测、对照稿等过程文件放 `_process/Methods/<YYYY-MM-DD>_<描述>/`，不放成稿目录。

没有 `PROJECT.md` 时保持下文原有行为，不新建它。

## 一致性防线（检测到 PROJECT.md 时）

按 `medpaper-pipeline/references/consistency-guards.md` 执行：

- 写作前读项目根的 `口径表.md`：术语用规范名，不用禁用别名；量的定义和关键计数照口径表写。图表标签与规范名不同时，在图注或正文中括注对应（如“目标标签拟合参照（图中 R2 (oracle)）”）。
- 材料冲突按统一权威顺序取舍：代码与回执 > source.json 数值与 definitions > 成图图面 > Methods > 详细图注 > 大纲与规格叙述 > 已写成的下游稿件。本技能其他章节中与此冲突的取舍规定，以此为准。
- 量的定义（拟合分区、评估分区、分组变量、尺度）以代码和回执为准写入正文，同时核对口径表第 2 节；口径表缺这一条时，把核实结果作为新条目提交到冲突台账（类型“事实”），不只写在 Methods 里。
- 发现冲突时登记到 `_process/冲突台账.md`（写明双方原文、出处、源头阶段和应改的上游文件）。事实类（有代码或数据作证：拟合分区、符号、计数、分组、量的定义、panel 字母）先把被改文件备份到 `_archive/<日期>/`，再直接修改上游文件和已受影响的下游文件，同步口径表；口径类（措辞强弱、结论范围、术语选择）和图面类只登记，等阶段关口由作者裁决。
- 核查说明的“需作者裁决事项”只列台账 ID 和一句摘要；台账中已修复或已裁决的事项不重复上报。
- 交付前依次运行（用 `python -X utf8` 运行脚本（PATH 上的 `python` 若是 Windows 商店空壳，改用真实解释器的完整路径））：`<medpaper-pipeline>/scripts/consistency_check.py <项目根>`（禁用别名与关键计数，命中项修掉或登记），再运行 `<medpaper-pipeline>/scripts/manuscript_check.py methods <本稿 EN 文件> --zh <本稿 ZH 文件>`，ERROR 先修掉，WARN 逐条在核查说明中说明（脚本口径见 consistency-guards 第 5 节）。

## 输出

- 完整 Methods 按大纲保留父级标题和小节标题，每节一个标题。原始提示词中“整段只有一个标题”，指当前小节只有一个标题。
- 默认格式：先英文正文，再中文对照；单独保存时输出 `Methods_EN.md`、`Methods_ZH.md`、`Methods_EN_ZH.md`，命中触发项时另附 `Methods_核查说明.md`。
- 修订任务在对话中附修订摘要（规则第 8 节）。
- 在对话或指定写作记录中跟踪节段进度，以便“下一节”续写。
- 论文材料和进度记录保存在用户指定的项目目录。不修改全局技能目录以外的配置或全局记忆，也不在稿件目录留下处理脚本。

## 交付前检查

- [ ] 散文分号链 0 处（同句 ≥2 个散文分号为 ERROR，结构性分号豁免）；目标平均 18–28 词/句，一般 ≤45 词、硬上限 60 词，>45 词占比 >10% 为 WARN；无连续 ≥3 个 <8 词短句的电报体连跑；WARN 已逐条说明。连接词按逻辑需要使用，不连续三句以上以同一个连接词或短语开头；按 journal-style 的「句长、分号与衔接」复核。

- [ ] 每项方法都有实际执行依据，且在写作重点范围内；范围冲突已上报。
- [ ] 每个小节或独立分析都有目的句，写法不套单一模板（以 “To …” 开头、或以“分析名词 + assessed/quantified”开头的段落各不超过三分之一，相邻段落首句句式不同）；没有结果、讨论或宣传性评价。
- [ ] 新增的数字和细节只限于帮助理解方法的内容；修订时所有事实句（含旧稿保留句）已逐句回查（规则第 8 节第 5 步）。
- [ ] 没有管理性元叙述、实现层质控、内部编号；具体数据处理和数据角色完整。
- [ ] 每个 n 的计数单位（扫描、眼、受试者、扫描–概念对等）已对照代码确认，含旧稿保留句；Results 要报告的具体量已在 Methods 写明定义。
- [ ] 比例分母、门槛对象、各模型训练和重拟合范围与实际调用一致。
- [ ] 美式拼写统一；缩写首次出现时已定义；模型和工具在使用前已引入；没有工程词汇和斜杠并列。
- [ ] 引用格式按 PMID > DOI > 正式出版页 URL > arXiv（仅限无正式出版版本） 的优先级取纯文本标注，且标识属于所引用的那个版本；标准方法未过度引用；需引用对象无遗漏。
- [ ] 父级标题和小节标题完整；中英文逐段一致；中文按中文学术语序重组，不是逐词直译。
- [ ] 已按 journal-style 第 5 节口径报告英文词数（目标约 2,500–3,000 词，可按叙事需要超出）；超过 3,000 词时已先排查实现细节、结果数字和可改为引表的长枚举。
- [ ] 核查说明的七项触发已逐项判断，且只含规则第 7 节规定的三部分（需裁决事项置前），没有逐句回查表或证据索引；若未输出核查说明，已在交付时说明理由。
- [ ] 已读取作者决定记录（如有）；已裁决事项沿用，未重复上报。
