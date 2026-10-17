---
name: medical-sci-legends
description: Use when drafting or revising figure legends, supplementary figure legends, or table titles and footnotes for a medical SCI manuscript from the outline, the rendered figures, detailed captions, source data and tables, such as 写图注、Figure Legend、附图图注、表格标题和表注、图注中英对照、修改已有图注、按大纲和成图写 legend. Produces concise English legends with Chinese parallel text, descriptive titles, panel-by-panel or merged-panel descriptions and a brief end note. Do not use for Results or Methods prose (use medical-sci-results / medical-sci-methods), outline building or drawing figures.
---

# 医学 SCI 图注与表注写作

依据大纲、成图、详细图注、源数据和表格，撰写或修订主图图注、附图图注及表格标题与表注，输出英文正式稿和中文对照。图注精炼：每个 panel 说清比较了什么、图上看到了什么，以及图面直接支持的有限含义；不复述 Results、不写方法流程、不过度解读。

## 必读材料（每次起草或修订都执行）

不凭技能名称或上次任务的摘要开始写作。用 Read 按顺序完整读取：

1. [原始提示词](references/original-legend-prompt.md)：基础角色与写作要求。
2. [已确认写作规则](references/writing-rules.md)：对原始提示词的细化，冲突时以它为准。
3. [期刊语言与格式规范](references/journal-style.md)：编号、数值、缩写、句式、篇幅。
4. [判断示例](references/examples.md)：只学判断方式，不迁移具体内容。
5. 项目目录下的 `Legends_作者决定.md`（如存在）：已裁决事项直接沿用。

当前用户指令优先于以上材料。不读取 Results 稿（规则第 1 节）。

## 工作流程

1. **定位**：读大纲的 Results 部分和图表引用清单，确定本次范围（全部、主图、附图、表格或指定图号）；修订模式下读入用户提供的已有图注。记下每张图在大纲中的“图 / 表”说明和措辞边界。大纲标记"待交付"的图也要在项目内检索是否存在成图（见规则第 1 节），存在就写。
2. **读图**：对每张图用 Read 打开成图 PNG，逐 panel 记录字母、图形与比较对象、可见的分布/趋势/差异、图内标注的数值和符号；再读详细图注和源数据，只取对象定义和数字（规则第 1 节）。表格读 md 或 csv。
3. **核对**：图注要写的每个数字都在成图标注、源数据或表格中找到出处，统一小数位；大纲、详细图注与成图不一致时按规则第 1、9 节处理。
4. **分组**：逐图决定哪些 panel 独立描述、哪些合并为 `(A–C)`、`(B, D)`（规则第 4 节）。
5. **撰写英文**：描述性标题 → 各描述单元 1–2 句（最多 4 句），融合图形对象、图上证据和有限含义 → 尾注（符号与颜色、统计量含义、措辞边界限定、缩写）（规则第 2–7 节）。
6. **撰写中文对照**：逐图重组为规范中文，事实、数值、限定、编号和合并范围与英文一致（规则第 8 节）。
7. **复核**：按下方“交付前检查”逐项确认，再按规则第 9 节决定是否输出核查说明。

默认在当前对话中完成，不派出子代理。用户明确要求并行时除外。

## 项目约定（检测到 PROJECT.md 时）

从工作目录或材料路径向上查找 `PROJECT.md`。找到时按 medpaper-pipeline 的项目目录约定（`medpaper-pipeline/references/project-layout.md`）执行，用户另行指定的路径优先：

- 默认材料：03_outline/ 的大纲、02_figures/out/ 的成图、详细图注、源数据与表格、04_manuscript/Methods/Methods_EN.md。
- 输出到 `04_manuscript/Legends/`，文件名固定为 Figure_Legends_{EN,ZH}.md、Supplementary_Figure_Legends_{EN,ZH}.md、Table_Titles_Notes_{EN,ZH}.md、Legends_核查说明.md，不加项目前缀或版本号。
- 已有同名成稿时，先把旧文件移到 `_archive/<今天日期>/04_manuscript/Legends/`，再写新文件；更新 `PROJECT.md` 状态表中 Legends 一行（状态 `待确认`、版本、日期）并在变更记录追加一行。
- 作者决定读 `04_manuscript/作者决定.md` 的“通用”和“Legends”两节，代替单独的 `Legends_作者决定.md`；新裁决追加到“Legends”节。
- 审查、盲测、对照稿等过程文件放 `_process/Legends/<YYYY-MM-DD>_<描述>/`，不放成稿目录。

没有 `PROJECT.md` 时保持下文原有行为，不新建它。

## 一致性防线（检测到 PROJECT.md 时）

按 `medpaper-pipeline/references/consistency-guards.md` 执行：

- 写作前读项目根的 `口径表.md`：术语用规范名，不用禁用别名；量的定义和关键计数照口径表写。图表标签与规范名不同时，在图注或正文中括注对应（如“目标标签拟合参照（图中 R2 (oracle)）”）。
- 材料冲突按统一权威顺序取舍：代码与回执 > source.json 数值与 definitions > 成图图面 > Methods > 详细图注 > 大纲与规格叙述 > 已写成的下游稿件。本技能其他章节中与此冲突的取舍规定，以此为准。
- 写每个 panel 前先读该图 `source.json` 的 `definitions` 字段（medfig-render 按代码写入）；没有这个字段时按本技能规则第 10 节回代码核对，并登记到台账，请上游补上该字段。
- 发现冲突时登记到 `_process/冲突台账.md`（写明双方原文、出处、源头阶段和应改的上游文件）。事实类（有代码或数据作证：拟合分区、符号、计数、分组、量的定义、panel 字母）先把被改文件备份到 `_archive/<日期>/`，再直接修改上游文件和已受影响的下游文件，同步口径表；口径类（措辞强弱、结论范围、术语选择）和图面类只登记，等阶段关口由作者裁决。
- 核查说明的“需作者裁决事项”只列台账 ID 和一句摘要；台账中已修复或已裁决的事项不重复上报。
- 交付前依次运行（用 `python -X utf8` 运行脚本（PATH 上的 `python` 若是 Windows 商店空壳，改用真实解释器的完整路径））：`<medpaper-pipeline>/scripts/consistency_check.py <项目根>`（禁用别名与关键计数，命中项修掉或登记），再运行 `<medpaper-pipeline>/scripts/manuscript_check.py legends <本稿 EN 文件> --zh <本稿 ZH 文件>`，ERROR 先修掉，WARN 逐条在核查说明中说明（脚本口径见 consistency-guards 第 5 节）。

## 输出

- 单独保存时，用 Write 输出到用户指定目录：`Figure_Legends_EN.md`、`Figure_Legends_ZH.md`（主图）；`Supplementary_Figure_Legends_EN.md`、`Supplementary_Figure_Legends_ZH.md`（附图）；`Table_Titles_Notes_EN.md`、`Table_Titles_Notes_ZH.md`（表格，含主表和补充表）。只做部分范围时只输出对应文件。命中触发项时另附 `Legends_核查说明.md`。
- 文件内每个图注或表注一段，彼此之间不留空行；不加文件标题以外的说明文字。
- 只在对话中交付时，先给英文，再给中文，核查说明放在独立说明块。
- 交付时报告每张图的英文词数（口径见 journal-style 第 5 节）、合并了哪些 panel，以及标题或术语相对大纲的改动。
- 不在稿件目录留下处理脚本或缓存；不修改技能目录、全局配置、大纲、成图、表格或数据。

## 交付前检查

- [ ] 散文分号链 0 处（同句 ≥2 个散文分号为 ERROR，结构性分号豁免）；目标平均 18–28 词/句，一般 ≤45 词、硬上限 60 词，>45 词占比 >10% 为 WARN；无连续 ≥3 个 <8 词短句的电报体连跑；WARN 已逐条说明。连接词按逻辑需要使用，不连续三句以上以同一个连接词或短语开头；按 journal-style 的「句长、分号与衔接」复核。

- [ ] 范围内每张图、每张表都有图注或表注；每张图的所有 panel 都被覆盖，字母与成图一致，合并范围准确，中英一致。
- [ ] 标题是描述性名词短语，不是发现句；格式为 `**Figure 2. Title.**`、`**Supplementary Figure S1. Title.**`、`**Table 1. Title.**`。
- [ ] panel 字母大小写与图面一致（本项目成图为小写 a–c）；涉及拟合划分、量的定义或分析归属时，已按规则第 10 节回代码/回执核对，没有照抄详细图注；队列名、指标拼写、表头已与 Methods 名称统一。
- [ ] 每个描述单元 1–2 句、最多 4 句；示意 panel 一句；承担定量比较的 panel 至少有一项具体图上证据或一个关键数字。
- [ ] 没有只写“展示什么”或只写空泛结论的 panel；相邻 panel 不用同一开头或同一动词套路。
- [ ] 同类 panel 已合并；合并后没有逐个重述小图；结论不同的同类 panel 没有被强行合并。
- [ ] 每个数字都能在成图标注、源数据或表格中找到出处，小数位、区间、n、P 值符合 journal-style 第 2 节；每个描述单元一般不超过 3 个数值、2 个带区间估计，多组数值只写范围、极值或例外，没有转述表格；数值格式跟随图面，同图同指标一致。
- [ ] 每张图最多一句独立限定句，限定只来自大纲措辞边界和读图必需的定义；没有 descriptive、do not establish、not significant overall、not clinical 等通用免责句；与本 panel 无关的限定没有重复出现。
- [ ] 没有用 some、several、many 代替具体证据；比较方向没有用 favor、advantage、“偏向”这类词（改写为 positive/negative、“差值为正”）；比较两个量级时写出了这对数字。
- [ ] 每张图英文不超过 150 词，超过时已按 journal-style 第 5 节删减或在交付时说明原因。
- [ ] 图注没有方法流程、抽样规则、计算细节、数据来源、文件名、字段名、色号或绘图参数；颜色和符号只在读图必需时出现在尾注。表注按 writing-rules 第 7 节承载从表体移出的必要方法 / 处理规则 / 口径及不适用说明。
- [ ] 尾注不超过三句，只含需要的项：符号与颜色、误差线或区间含义、n 的单位、显著性标记与检验名称（仅当图中有）、措辞边界限定、缩写；缩写只列本图注中出现的，按出现顺序。
- [ ] 大纲措辞边界中与该图相关的限定都已写入一次；没有 significant（无检验时）、superior、outperformed、因果、机制、临床价值或泛化表述，没有宣传性词汇。
- [ ] 表格标题写内容不写发现；表注说明数值含义、符号占位、必要限定和缩写，并逐项承载 `presentation_trim` 中移出的方法 / 处理规则 / 口径与“未估计 / 不适用”等说明，不重复表头、不解读结果；每张主表 / 附表有正文对应引用证据，支撑论断、引用位置与设计规格 / 大纲清单一致，缺证据已上报；整表移出时有一句数据仓库 / Data Availability 指向，无失效表题占位、虚构链接，后续编号与引用同步。
- [ ] 英文单句硬上限 60 词；美式拼写；术语与 Methods 稿一致；没有规则代号、seed-0、frozen endpoint 等内部标识；中文按中文语序重组，没有直译腔，panel 编号用半角 `(A)`，类别标签与图面一致。
- [ ] 文件内图注之间没有空行；核查说明的五项触发已逐项判断，未输出时已在交付时说明理由。
