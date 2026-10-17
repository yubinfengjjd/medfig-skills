# 项目目录约定

作者于 2026-10-14 确认。适用于 medpaper-pipeline 管理的项目，以及在项目根检测到 `PROJECT.md` 的各 medfig 与写作技能。

## 1. 目录结构

```
<项目根>/
├─ PROJECT.md                阶段状态表、目录说明、变更记录（第 3 节）
├─ 口径表.md                 术语、量的定义、关键计数的唯一来源（consistency-guards.md 第 2 节）
├─ 00_plan/                  开题计划（medical-research-plan 产物或作者提供）
├─ 01_analysis/              实验代码与结果（代码接收与整理后的结构，见 code-intake.md）
│  ├─ README.md              总索引：各来源一览、与 00_plan 的对应、待核项
│  ├─ <来源名>/               每个代码来源：README.md、映射表.md、code/、results/、receipts/
│  ├─ <study-id>/            medimg-experiment study（受控结构；结束登记，不搬家）
│  └─ （外部仓库且作者不迁移时：只放 README.md 写明路径与 commit）
├─ 02_figures/               medfig 项目根（git）：figkit.toml、docs/、scripts/、out/
├─ 03_outline/               写作大纲.md / 写作大纲.docx + 分节证据目录
├─ 04_manuscript/            只放当前成稿
│  ├─ 作者决定.md            各写作技能共用的裁决记录（第 4 节）
│  ├─ Methods/               Methods_EN.md、Methods_ZH.md、Methods_EN_ZH.md、Methods_核查说明.md
│  ├─ Legends/               Figure_Legends_{EN,ZH}.md、Supplementary_Figure_Legends_{EN,ZH}.md、
│  │                         Table_Titles_Notes_{EN,ZH}.md、Legends_核查说明.md
│  ├─ Results/               Results_EN.md、Results_ZH.md、Results_EN_ZH.md、Results_核查说明.md
│  ├─ Introduction/          Introduction_EN.md、Introduction_ZH.md、Introduction_EN_ZH.md、Introduction_核查说明.md
│  ├─ Discussion/            Discussion_EN.md、Discussion_ZH.md、Discussion_EN_ZH.md、Discussion_核查说明.md
│  └─ Abstract/              Abstract_EN.md、Abstract_ZH.md、Abstract_EN_ZH.md、Abstract_核查说明.md
├─ 05_final/                 成品 Word：<项目名>_Manuscript_v<N>.docx、<项目名>_Supplementary_v<N>.docx（medical-sci-finalize）
├─ _process/冲突台账.md      全阶段共用的材料冲突记录（consistency-guards.md 第 4 节）
├─ _process/<阶段>/<YYYY-MM-DD>_<描述>/   审查、盲测、裁决书、对照稿
└─ _archive/<YYYY-MM-DD>/<原相对路径>     被替换的旧版本
```

- 文件名固定，不带项目前缀和版本号；版本号只记在 `PROJECT.md`。
- `01_analysis/<来源名>/code/` 内脚本命名 `<两位序号>_<语义名>.<ext>`，序号即运行顺序；脚本内容零改动。
- 映射表.md 必须含“原路径 → 整理后路径”对照（口径表与写作技能的代码出处经它回溯）。
- 数据、模型权重、凭证默认不复制（例外经作者确认后映射表备注“作者批准”）；符号链接一律不复制（源目录中的符号链接作为排除项列入整理方案）。
- 附图图注、附表表注都放 `Legends/`；附图、附表文件本身留在 `02_figures/out/`，不复制。
- 成稿目录不放脚本、缓存、审查记录或对照草稿；这些放 `_process/`。
- `02_figures/` 是独立 git 仓库；medfig-orchestrate 的台账、brief、review 按该技能要求留在 `02_figures/docs/_process/`（git 跟踪），不移到项目根 `_process/`。
- `_process/` 的阶段名用：`plan`、`Intake`、`figures`、`outline`、`Methods`、`Legends`、`Results`、`Introduction`、`Discussion`、`Abstract`、`Finalize`、`References`。例如 `_process/Results/2026-10-14_盲测_R4/`、`_process/Legends/2026-10-14_裁决_R3材料问题.md`。
- Abstract 的 Keywords、Highlights 放在三份语言稿的独立节，不额外增加成稿文件。

## 2. 替换与归档

成稿被新版本替换时，按顺序：

1. 把旧文件移到 `_archive/<今天日期>/<原相对路径>`（如 `_archive/2026-10-20/04_manuscript/Methods/Methods_EN.md`）；同一天多次替换时在日期后加 `_2`、`_3`。
2. 写入新文件，文件名不变。
3. 更新 `PROJECT.md` 状态表的版本、日期，并在变更记录追加一行。

不删除旧版本；`_archive/` 只增不改。

## 3. PROJECT.md 格式

```markdown
# <项目名>

## 阶段状态

| # | 阶段 | 技能 | 状态 | 当前产物 | 版本 | 确认日期 | 备注 |
|---|---|---|---|---|---|---|---|
| 0 | 入口检查与代码整理 | — | 完成 | 00_plan/、01_analysis/ | — | 2026-10-01 | |
| 1 | 图表规划 | medfig-plan | 已确认 | 02_figures/docs/2026-10-02-figure-set-design.md | v3 | 2026-10-03 | |
| … | | | | | | | |
| 9 | Discussion | medical-sci-discussion | 未开始 | | | | |
| 10 | Abstract | medical-sci-abstract | 未开始 | | | | |
| 11 | 成品组装与润色 | medical-sci-finalize | 未开始 | 05_final/ | | | |
| 12 | 参考文献收集与注入 | medical-sci-references | 未开始 | 05_final/ | | | |

## 写作目标

- 目标期刊：无/待定
- 目标文献总数：55
- Introduction：≥20
- Introduction 综述层：≥10
- Discussion：≥20
- Methods：≥15

## 目录说明
（每个顶层目录一行；外部仓库、外部数据的绝对路径写在这里）

## 变更记录
- 2026-10-14 Methods v2 → v3：……（旧版 _archive/2026-10-14/04_manuscript/Methods/）
```

写作目标中示例为通用配额；作者可随时修改。缺该小节时按通用配额并在报告中说明；缺个别字段时仅该字段用缺省，格式错误要报告，不静默忽略。Methods 配额只作全稿统计登记项，不给 Methods 技能增加硬性数量规则。Results 仍禁引。统计口径及核验表格式见 [引用配额与统计](citation-quotas.md)。

状态取值：`未开始`、`进行中`、`待确认`、`已确认`、`需返工`。只有作者确认后才写 `已确认`。

## 4. 作者决定.md

```markdown
# 作者决定

## 通用
## Methods
## Legends
## Results
## Introduction
## Discussion
## Abstract
## Finalize
## References
```

- 每条：日期 + 决定 + 依据（对话或裁决书路径）。
- 各写作技能读“通用”和本技能对应的一节；新裁决追加到对应节，不改旧条目，被推翻时在新条目中写明“取代 YYYY-MM-DD 某条”。
- 项目内若还有旧的分技能文件（`Methods_作者决定.md` 等），迁移时并入本文件，原文件移入 `_archive/`。

## 5. 各技能如何识别

技能开始时从工作目录或用户给出的材料路径向上查找 `PROJECT.md`：

- 找到：按本约定确定读写路径，用户另行指定的路径优先；完成后按第 2 节归档并更新状态表。
- 没找到：保持技能原有行为，不新建 `PROJECT.md`（只有 medpaper-pipeline 负责新建）。

## 第12步产物与检查边界

05_final 主稿可为 Zotero 字段版（medical-sci-references 产物），同一命名、版本递增。过程材料位于 `_process/References/<日期>_v<N>/`，作者决定写 `## References`。独立使用不新建PROJECT；作者必须给输出目录和集合。

第11步重建主稿后第12步置需返工。字段版以 check_references.py 为准；finalize 中无References及纯文本引用集合断言不适用，不改 finalize 脚本。上游变更的下游状态传播自然包含12。第12步仍须作者在Word Refresh验收，脚本只标待确认。
