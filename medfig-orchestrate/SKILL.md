---
name: medfig-orchestrate
description: Use when an approved figure-set spec for a medical research paper already exists and the user wants the whole set of figures and tables produced in batch, such as turning the spec into an implementation plan, running one subagent per figure in parallel git worktrees, reviewing each figure task against the spec, keeping a ledger of rulings, re-exporting after merges, running a final whole-set review and writing the delivery note; also when the user says 按规格批量出图、整套图表并行执行、出图台账、逐图审查、终审交付, or resumes a half-finished figure-set run from its ledger.
---

# medfig-orchestrate：规格 → 计划 → 并行执行 → 终审 → 交付

本技能自成一体：主控（controller）按 spec 写计划，每任务派一个子代理实现，逐任务审查，维护台账，最后终审并交付。
子代理契约（brief 内容、审查输入、修复循环、范围复审、breaker、模型分层）全部写在下文"子代理契约"一节，不依赖其他技能。
若本机装有通用的 `subagent-driven-development` 技能，可作为可选参考；与本技能冲突时以本技能为准，尤其三处：
1. 独立任务可在**各自 worktree** 中并行（约 4 个），规则见 `references/parallel_rules.md`。
2. 台账和过程产物放 **git 跟踪的 `docs/_process/`**，不放 git-ignored 目录（经验 D10）。
3. 删 worktree 前必须**先在主分支重导出并核验产物**（经验 B23、D8）。

## 何时用 / 何时不用

用：
- 已有经用户批准的出图规格（通常由 medfig-plan 产出的 `docs/<date>-figure-set-design.md`），要一次产出多张图 + 表。
- 用户要求"按规格把整套图做完""并行出图""给我台账和终审"。

不用（改走别处）：
- 只画一张图 → `medfig-render`。
- 还没有规格、只想规划 panel / 主附图 → `medfig-plan`。
- 只要一张纯影像网格 → `scipilot-medimg-figure-skill`。
- 普通软件功能开发（与出图无关）→ 用通用的开发流程，不用本技能。

## 输入与产物

| 输入 | 说明 |
|---|---|
| 规格 spec | 绑定权威。每 panel 的结论、数据文件与列、图型、完整性限制 |
| 项目根 | 含 `figkit.toml`（medfig-render 的配置）与 git 仓库；没有 git 就先 `git init`，并在台账记一条 Ruling |
| 解释器 | 用户指定的 python，全程固定，写进计划头部 |

| 产物 | 位置 |
|---|---|
| 实施计划 | `docs/<date>-figure-set-plan.md`（模板 `references/plan_template.md`） |
| 台账 | `docs/_process/ledger.md`（格式 `references/ledger_format.md`） |
| brief / report / review | `docs/_process/tasks/task-NN-{brief,report,review-R}.md` |
| 终审与修复报告 | `docs/_process/final-review.md`、`docs/_process/final-fix-report.md` |
| 交付 | `out/DELIVERY.md`（或 `DELIVERY_ZH.md`）+ `out/QA_SUMMARY.md`（模板 `references/delivery_template.md`） |

`out/` 通常 git-ignored（大二进制），所以产物只以"主分支重导出后存在"为准，不以 worktree 里存在为准。

## 两条贯穿全程的硬规则

**Ruling 格式。** 主控替用户做的每个决定都写进台账，一行一条：

```
- Ruling: <决定了什么> — <为什么> — <cost if wrong：判断错了要付出什么>
```

没有 cost-if-wrong 的 Ruling 不算数。交付时逐条列出（见第 7 步）。

**每次派子代理都显式指定 model。** 省略 model 会继承主控会话的（通常最贵的）模型。分层见下文"子代理契约 · 模型分层"；台账的 dispatched 行必须带模型名：`Task 7: dispatched (sonnet), BASE a1b2c3d`。

## 子代理契约（本技能自带，不依赖外部技能）

**模型分层（model tiering）**
- 共享层（figkit 扩展、QA、数值锚点测试）：标准及以上模型；便宜模型批量做共享层曾产出 3 个 Important 缺陷（经验 D12）。
- 单图 implementer：标准模型；brief 里已给出完整代码、只需抄写 + 测试的单文件任务可用最便宜档。
- task reviewer：中档起步，按 diff 大小与风险上调；范围复审：便宜到中档。
- 终审：最强模型。修复第 4–5 轮：比卡住的 implementer 高一档。

**implementer brief（写进 `docs/_process/tasks/task-NN-brief.md`）** 含：本任务在项目中的位置（一行）；spec 段落与该任务的完整要求（精确数值、文件名、prov 键名只写在 brief 里）；前序任务的接口与已做裁决；主控对歧义的裁决；文件所有权；report 路径与回报约定。dispatch 消息只给 brief 路径 + 上述前序接口 + report 路径，不贴历史。
implementer 不得再派子代理（包括 reviewer）。回报写进 `task-NN-report.md`（做了什么、测试命令与输出、commit、**Named risks**），只回四种状态之一：DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED。NEEDS_CONTEXT → 补上下文重派；BLOCKED → 补上下文、换更强模型、拆小任务，或 Ruling 修正计划后重派，不许原样重试。

**reviewer 输入**：brief 路径、report 路径、review package（`git log --oneline BASE..HEAD`、`git diff --stat`、`git diff -U10` 写进一个文件）、spec 中绑定本任务的原文、`references/review_checklist.md`。BASE 是派发前记录的 sha，不用 `HEAD~1`。不在 prompt 里预判结论（不写"不要标记 X"）。reviewer 报"无法从 diff 核实"的项，由主控亲自查清。

**修复循环（fix loop，≤ 5 轮）**：spec ❌、任何 Critical / Important、或主控确认的无法核实项触发。一轮 = 一次修复 + 一次范围复审。
- 第 1–3 轮：续用原 implementer，原样发送未决问题。
- 第 4–5 轮：派新 implementer、更强模型，告知"前任已尝试 N 次，读 report 了解经过"。
- 每轮 implementer 重跑覆盖改动的测试，把修复报告追加到同一 report；报告里没有测试名、命令、输出就不派复审。
- 台账：`Task N: fix round R/5 (X addressed, Y open; commits a..b)`。
- Minor 不进循环，记 `minor (deferred)`；与计划原文冲突的发现由主控 Ruling 后再处理。

**范围复审（scoped re-review）**：review package 只取 FIX_BASE..HEAD；逐条判 ADDRESSED / NOT ADDRESSED，只报修复 diff 里的新破坏；范围外的观察记 deferred minor，不延长循环。

**breaker（第 5 轮后仍有未决项）**：停止派发，主控逐条裁决并写台账——
- reviewer 有误或可争议 / 真问题但无下游依赖：`Task N: parked — <finding> — Ruling: <why> — <cost if wrong>`；
- 真问题且后续任务依赖：选最小的解阻改动，`Task N: Ruling: <finding> — <决定与理由> — <cost if wrong>`，带进下一个 dispatch。
只在到达上限时裁决；每条裁决都是台账行，禁止静默丢弃。

## 流程总览

```
spec ─▶ 1 计划 + 冲突扫描 ─▶ 2 并行派发（≈4 worktree）─▶ 3 逐任务审查 ≤5 轮
      ─▶ 4 合并 → 主分支重导出 → 核验 → 删 worktree ─▶（循环至全部任务）
      ─▶ 7 终审 → 一次修复 → 一次范围复审 → 交付
   5 子代理失联处理、6 过程产物持久化 贯穿全程
```

## 第 1 步：规格 → 实施计划 + 冲突扫描（pre-flight）

按 `references/plan_template.md` 写计划：
- **共享层任务在前**：figkit 扩展、数值锚点测试（number-anchor tests，先对源数据核一次再冻结为测试）、公共图注/术语表。锚点测试绿了才派逐图任务（经验 D1、D13）。
- **逐图任务在后**：每图写清数据文件与列、变换、GridSpec 参数、必须断言的数（写进 `prov.values`），绘图代码留给执行期。
- 依赖全部图的任务（图表来源索引 ST12 式表、QA_SUMMARY）排最后，并注明"合并后在主分支重建"。
- 计划末尾自检：spec 覆盖、偏离、占位符、接口一致性。

开跑前做**冲突扫描**，结果是一张表写进台账，不是一句"扫描干净"（经验 D2）：
- 每对共享文件/接口的任务一行：谁产出、谁消费、发现了什么。
- 每个任务一行：它自己的测试与代码是否一致、创建的文件与后续触碰的文件是否一致。
- 出图项目必查：QA 审计与 panel 标签是否会误报；是否有数据在只读根之外（需白名单读取）；是否有任务依赖全部图；项目是不是 git 仓库；两个任务是否写同一图注文件。

每条发现当场 Ruling（spec 为准），再派第一个任务。

## 第 2 步：派发（每任务一个子代理，≈4 个并行 worktree）

- 用 `scripts/new_worktree.py` 为任务 N 从 master HEAD 建 worktree + 分支（幂等：已存在则报告，不报错；默认分支叫 main 时加 `--base main`）：
  `python scripts/new_worktree.py --repo <主checkout> --task N --wt-root <dir>`，
  输出 JSON 的 `base_sha` 就是该任务的 BASE，写进台账 dispatched 行。
- 一波约 4 个；共享层稳定前不开并行波。
- **文件所有权**：每任务只写自己名下的脚本、测试、图注文件（图注按图拆分为 `docs/captions/<fig>.md`）。并行任务不改共享库；需要的 helper 先在本地复制，合并时由主控提升进共享库。共享文件（台账、汇总图注、QA_SUMMARY）只由主控写，或每任务一个分节、只追加自己的分节。完整规则见 `references/parallel_rules.md`。
- brief 与 dispatch 内容按上文"子代理契约"。
- 用户做出的决定要**同时**写进台账和 brief 文件，不能只发消息给正在跑的子代理（消息可能晚到，经验 D9）。
- implementer 的 report 必须有 "Named risks" 一节；DONE_WITH_CONCERNS 的风险原样交给 reviewer（经验 D4）。

## 第 3 步：逐任务审查（spec + quality），修复 ≤ 5 轮

- 每个任务完成后派 task reviewer，两个结论都要：spec compliance 与 task quality。reviewer 按 `references/review_checklist.md` 逐项过，输入见"子代理契约"。
- **spec 高于 brief**：reviewer 对照 spec 审，不只对照 brief；brief 与 spec 冲突时以 spec 为准，写一条 Ruling（经验 B19）。有理由的偏离（尺寸、换行、改编码）也写 Ruling，并进交付的"偏离"清单。
- **主控核实后才采纳**：implementer 的说法和 reviewer 的建议都不直接采纳。涉及数字、n、队列重叠、图注事实的，主控回源数据重算一次，把核实结果写进台账（如 `Task 12: controller verified caption facts from source: …`）。建议与数据不符就驳回并写 Ruling（经验 D7）。
- 修复循环、范围复审、breaker 按"子代理契约"执行（≤ 5 轮；1–3 续用原 implementer，4–5 换更强模型）。
- 复审要看测试本身，不只看"已修复"的说法；首轮修复出现过空测试（经验 D5）。
- Minor：便宜且后续任务要依赖的并进本轮；同一文件后续任务会碰的，带进下个 dispatch；其余记 `minor (deferred)`，留给 minors 批次或终审分诊（经验 D6）。
- 主控不亲自改代码，改动都走子代理 + 复审。

## 第 4 步：合并 → 主分支重导出 → 核验 → 删 worktree

`out/` 通常 git-ignored，worktree 里的导出不会随合并进入主目录（经验 B23、D8）。每次合并后按顺序做：

1. 在主 checkout 合并任务分支（`git merge --no-ff taskN`），合并共享文件的分节。
2. 把并行期间本地复制的 helper 提升进共享库（或记 deferred minor），跑全量测试。
3. 用 `scripts/reexport_check.py` 在**主 checkout** 重跑本任务的图脚本并核验产物：
   `python scripts/reexport_check.py --root <主checkout> --python <解释器> figures/fig3.py=out/figures/main/fig3.pdf,out/figures/main/fig3.svg,out/figures/main/fig3.png,out/figures/main/fig3.source.json,out/panels/fig3/fig3_a.pdf,out/panels/fig3/fig3_a.svg,out/panels/fig3/fig3_b.pdf,out/panels/fig3/fig3_b.svg`（附图把 `main` 换成 `supp`，即 `export.save` 的 `kind`）
   预期产物必须包含每个 panel 的独立导出 `out/panels/<fig>/<fig>_<panel>.pdf`（与 .svg；尺寸同组图中该 panel，不带 a/b/c 序号，spec §9 S4）。
   退出码 0 才算通过；1 = 脚本失败 / 产物缺失 / 产物未被本次重写（stale）；2 = root 是 linked worktree 或参数错。
4. 通过后才 `git worktree remove` 并删分支；台账写 `Task N: complete (commits a..b, merged <sha>, review clean; re-exported figN on master)`。
5. 依赖全部图的索引表、QA_SUMMARY 在最后一次合并后于主分支重建。

## 第 5 步：子代理失联与额度问题

- 标记进度前先查证据：report 文件在不在、分支上有没有 commit。只有口头"完成"不算。
- 子代理沉默或消失：查状态（列出活着的子代理、看 report 与 git log）；无回报 → 用同一个 brief 重派，台账写 `Task N: re-review lost (agent gone); re-dispatched`。接手的写 `takeover k`。
- 等待时用有界等待（5–10 分钟一段），每段之间对账一次活着的子代理，不要无限静等。
- 遇到 **403、insufficient balance / 余额不足、配额耗尽**：立即停止派发，不重试、不换号，告诉用户当前台账位置和卡在哪个任务。这属于需要用户处理的外部问题。
- 其余停下来问用户的情形只有：不可逆/破坏性操作、安全敏感操作、要改上游只读数据或他人仓库、科学层面的重设计（改 panel 的论证方式）、领域术语源数据里没有。

## 第 6 步：台账与过程产物持久化

- 台账 `docs/_process/ledger.md`、brief、report、review、终审、修复报告全部放在 **git 跟踪**的 `docs/_process/`，随任务 commit；不要放进 git-ignored 目录（经验 D10：曾因 `.gitignore = *` 丢掉全部 brief 和 review）。
- 台账只由主控写；并行子代理不写台账，只写自己的 report（经验 D3：并行追加造成重复行）。
- 台账首行写身份：`# medfig ledger — plan: <计划路径>`。上下文压缩后以台账 + `git log` 为准恢复，已有 `complete` 行的任务不重派。
- 行格式、状态词、示例见 `references/ledger_format.md`。

## 第 7 步：终审 → 一次修复 → 一次范围复审 → 交付

1. **终审**（最强模型）：输入全分支 review package、spec、台账中所有 deferred minor 与 parked 行、`references/review_checklist.md`。格式见 `references/ledger_format.md` 的"终审报告"一节：分 pass（库 / 主图 / 附图 / 表与图注）、每个 pass 写清读了多少（"targeted pass，未逐行读完"要如实写）、checked-and-clean 列表带 file:line、Critical / Important / Minor 各带具体修法、deferred minor 分诊（must-fix / verified fixed / acceptable）、结论（经验 D13、D14）。
   终审必做：所有图注里同一队列的 n 交叉对照；禁用词表只有一份；所有图重跑一次。
2. **一次统一修复**：一个子代理拿完整问题清单，逐条回 DONE / REJECTED / SKIPPED + 理由 + 验证（测试数、所有脚本退出 0、QA 汇总已更新）。REJECTED 需主控回源核实并写 Ruling。
3. **一次范围复审**：只审修复区间。残留项按 breaker 规则裁决，不开第二轮修复。
4. **交付**（模板 `references/delivery_template.md`）：
   - `DELIVERY` 说明：目录、每图每表的科学作用、复跑命令、相对规格的偏离、已知局限。
   - `QA_SUMMARY`：逐图 QA 结果与测试数。
   - **全部裁决清单**：把台账里每一条 `Ruling:` 按时间顺序列出，每条带 cost if wrong；一条不漏。
   - **目视检查清单（eye-check）**：自动 QA 只查几何与文字，PNG 必须由用户亲眼看；列出文件路径与每张要看的重点（拉伸、色阶、重叠、灰度可读性、panel 留白是否过多、数据图元是否有彩色）。

## 常见借口

| 借口 | 事实 |
|---|---|
| "worktree 里已经导出过了" | `out/` 不进 git，合并后主目录里没有；以 reexport_check 退出 0 为准 |
| "brief 就是这么写的" | spec 是绑定权威，brief 只是转述 |
| "reviewer 说要改，就改" | 先回源数据核实；错的建议照样驳回 |
| "子代理大概还在跑" | 查 report 与 commit；没有就重派 |
| "余额不足，换个模型再试" | 停下告诉用户 |
| "这个决定很小，不用写 Ruling" | 没写进台账的决定，用户看不到也改不了 |
| "过程文件放 git-ignored 的草稿目录就行" | git-ignored 目录会丢；放 `docs/_process/` |

## 参考文件

- `references/plan_template.md`：实施计划模板（共享层 + 逐图任务 + 冲突扫描表）
- `references/parallel_rules.md`：并行 worktree、文件所有权、共享文件分节追加、合并顺序
- `references/review_checklist.md`：出图审查清单（供本技能的 task reviewer 与终审使用，可单独交给审查子代理）
- `references/ledger_format.md`：台账行格式、Ruling 格式、终审与修复报告格式
- `references/delivery_template.md`：DELIVERY / QA_SUMMARY / 裁决清单 / 目视清单模板
- `scripts/new_worktree.py`、`scripts/reexport_check.py`：见第 2、4 步
