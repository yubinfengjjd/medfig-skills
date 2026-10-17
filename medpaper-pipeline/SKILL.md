---
name: medpaper-pipeline
description: Use when the user wants to run or resume the whole medical SCI paper production line in order — figure planning, figure rendering, writing outline, then Methods, figure legends, Results, Introduction, Discussion, Abstract, final Word assembly and polishing — or to set up, check or migrate a paper project's standard directory layout and PROJECT.md status table, such as 从出图到写作按顺序走、论文流水线、下一步该做什么、整理项目目录与代码、新建论文项目、项目进度. Calls the medfig-* and medical-sci-* skills one stage at a time and stops for author confirmation after each stage. Do not use for a single isolated task that one skill already covers (call that skill directly), or for research planning and experiments.
---

# 医学论文出图与写作编排

按固定顺序调用 medfig 出图技能和医学写作技能，每个阶段完成后停下等作者确认；统一项目目录，用 `PROJECT.md` 记录每个阶段的状态和当前产物。本技能只做编排、建目录和维护状态表，不自己画图或写正文。

## 必读材料

用 Read 完整读取 [项目目录约定](references/project-layout.md) 和 [跨阶段一致性防线](references/consistency-guards.md)。各阶段的具体做法以被调用技能的 SKILL.md 为准，本技能不覆盖它们的规则。

## 阶段顺序

| # | 阶段 | 调用技能 | 前置条件 | 产出位置 |
|---|---|---|---|---|
| 0 | 入口检查与代码整理 | — | — | `00_plan/`、`01_analysis/` |
| 1 | 图表规划 | medfig-plan | 0 完成 | `02_figures/docs/` |
| 2 | 示意图（可选） | medfig-schematic / medfig-illustrator | 1 已确认 | `02_figures/out/` |
| 3 | 出图 | medfig-orchestrate（单张用 medfig-render） | 1 已确认 | `02_figures/out/` |
| 4 | 写作大纲 | medfig-outline | 3 已确认 | `03_outline/` |
| 5 | Methods | medical-sci-methods | 4 已确认 | `04_manuscript/Methods/` |
| 6 | 图注 | medical-sci-legends | 3、4 已确认 | `04_manuscript/Legends/` |
| 7 | Results | medical-sci-results | 5、6 已确认 | `04_manuscript/Results/` |
| 8 | Introduction | medical-sci-introduction | 5、6、7 已确认 | `04_manuscript/Introduction/` |
| 9 | Discussion | medical-sci-discussion | 5、6、7、8 已确认 | `04_manuscript/Discussion/` |
| 10 | Abstract | medical-sci-abstract | 5、6、7、8、9 已确认 | `04_manuscript/Abstract/` |
| 11 | 成品组装与润色 | medical-sci-finalize | 5、6、7、8、9、10 已确认 | `05_final/` |
| 12 | 参考文献收集与注入 | medical-sci-references | 11 已确认 | `05_final/` |

- 代码接收与整理在阶段 0 内按 references/code-intake.md 执行；无代码可整理时在备注写“代码整理：不适用”。
- 图注在 Results 之前：Results 技能读图注，图注技能不读 Results。
- Discussion 的前置是硬门槛：medical-sci-discussion 在 Methods、图注、Results、Introduction 任一缺失或为 `未开始`/`进行中`/`需返工` 时拒绝起草，作者坚持也不跳过。
- Abstract 在 Discussion 后面：medical-sci-abstract 要求 Methods、图注、Results、Introduction、Discussion 五类正文完整；任一缺失、实质占位或为 `未开始`/`进行中`/`需返工` 时停止，不交付暂定初稿。流水线正常推进要求 5–9 已确认。
- 开题（medical-research-plan）和实验（medimg-experiment）不在编排内，由作者单独调用；第 0 步只检查它们的产物。实验 study 与外部代码由第 0 步的代码接收与整理子流程核验并登记。
- 第 2 步只在规格中有示意图或架构图时进行；没有就在状态表写“不适用”。

## 工作流程

1. **定位项目**：从工作目录或用户给的路径向上找 `PROJECT.md`。
   - 没有：确认项目名和项目根位置后，按约定第 1 节建目录骨架和 `PROJECT.md`、`04_manuscript/作者决定.md`、空的 `口径表.md` 与 `_process/冲突台账.md`（格式见防线第 2、4 节）。已有材料散落在别处时，先列出“旧路径 → 新路径”的迁移清单请作者确认，确认后复制（不移动、不删除原目录），并在 `PROJECT.md` 目录说明中记下原路径。
   - 有：读状态表，核对表中“当前产物”路径都存在；不一致时先报告，不往下做。
2. **确定本次阶段**：作者点名阶段时直接用；只说“下一步”时取状态表中第一个未确认的阶段。检查前置条件，不满足时说明缺什么，建议先做哪一步；作者坚持跳过时在备注栏记下。
3. **入口检查（阶段 0）**：确认 `00_plan/` 有研究计划或作者给的研究问题说明，`01_analysis/` 有结果资产或指向外部仓库的 README。缺了就告诉作者，不代写。代码与结果尚未整理时，按 references/code-intake.md 执行代码接收与整理（读思路 → 盘点 → 整理方案 → 作者确认 → 拷贝整理 → 登记）；无代码可整理时在备注写“代码整理：不适用”。
4. **调用阶段技能**：阶段 5（Methods）、8（Introduction）、9（Discussion）都须把项目根 `PROJECT.md` 的“写作目标”小节原文及项目根路径交给被调技能；缺少时明确传入通用缺省：全稿 55、Introduction ≥20（综述层 ≥10）、Discussion ≥20、Methods ≥15，并在报告中说明。作者可随时修改登记值；Methods 配额仅用于全稿统计，不给 Methods 技能增加数量规则。配额是软门槛，检索穷尽仍不足时如实报告实际 vs 目标、缺口及检索主题，请作者提供或确认，不凑数、不因此停工。统计和核验表约定见 [引用配额与统计](references/citation-quotas.md)。
   用 Skill 调用该阶段的技能，把项目约定下的材料路径和输出路径一并交给它；按该技能自己的流程做完，包括它要求的确认节点。
5. **收尾**：核对产物落在约定目录、文件名正确；被替换的旧版已按约定第 2 节归档；过程文件在 `_process/<阶段>/`。运行 `python -X utf8 scripts/consistency_check.py <项目根>`（防线第 5 节；禁用别名、关键计数、疑似丢失小数点，以及各节/全稿已核验引用统计与配额缺口），命中项在本阶段修掉或登记到 `_process/冲突台账.md`；本阶段的写作技能还会各自运行 `scripts/manuscript_check.py <章节> …`，其 ERROR 清零、WARN 已说明后才能收尾。把被调用技能核查说明中的新冲突并入台账（防线第 4 节）。把状态表该行更新为 `待确认`，写入当前产物、版本和备注。
6. **关口裁决与汇报**：报告本阶段产物路径、一致性检查结果、台账中本阶段新增的 `待裁决` 条目（逐条列 ID、双方原文与建议），以及下一阶段及其前置条件。作者逐条裁决后，先改上游文件，再改本阶段，同步 `口径表.md` 和 `作者决定.md`（防线第 6 节）。`待裁决` 清零（或作者标 `暂缓`）后才能把状态改为 `已确认`；作者要求返工时改为 `需返工` 并回到第 4 步。

作者说“连续跑到 X”时，阶段之间不再停下，但任何阶段出现待裁决事项、材料冲突或失败时仍立即停下。

## 规则

- 一次只推进一个阶段，除非作者明确要求连续跑。
- 不改被调用技能的规则；它们与本约定冲突时，以被调用技能的硬性要求为准（如 medfig-orchestrate 台账留在 `02_figures/docs/_process/`、medfig-outline 输出必须在 medfig 项目根之外），并在 `PROJECT.md` 备注中说明。
- 作者裁决写入 `04_manuscript/作者决定.md` 的对应节（约定第 4 节）；涉及术语、量的定义或计数的裁决同时写入 `口径表.md`。
- 材料冲突按防线第 1 节的权威顺序取舍：代码与回执 > source.json 数值与 definitions > 成图图面 > Methods > 详细图注 > 大纲与规格叙述 > 下游成稿。
- 上游阶段返工（如重出某张图）后，把依赖它的下游阶段改为 `需返工`，并在汇报中列出受影响的阶段。
- 不删除任何文件；替换一律先归档。不修改技能目录或全局配置。

## 第12步参考文献

第11步作者确认后运行 medical-sci-references：只收集主稿引用到 Zotero，生成原生字段版新版本主稿；第12行先待确认，作者 Word Refresh 验收后才能已确认。计划下一阶段时，11已确认且12未确认就取12；旧PROJECT缺12行时补“未开始”，不得把不存在的阶段视为已完成。

第11步重新组装或上游返工影响主稿时，第12行置“需返工”。字段版主稿由 check_references.py 验收；check_finalize.py 的“无References/纯文本引用标识集合一致”断言在第12步之后不再适用，不改 finalize 脚本。Zotero 由作者保持运行，探测连续3次失败（间隔5秒）则记录连接待办并继续离线准备，不启动、重启或关闭 Zotero。

## 交付前检查

- [ ] 散文分号链 0 处（同句 ≥2 个散文分号为 ERROR，结构性分号豁免）；目标平均 18–28 词/句，一般 ≤45 词、硬上限 60 词，>45 词占比 >10% 为 WARN；无连续 ≥3 个 <8 词短句的电报体连跑；WARN 已逐条说明。连接词按逻辑需要使用，不连续三句以上以同一个连接词或短语开头；按各阶段技能 journal-style 的「句长、分号与衔接」复核。
