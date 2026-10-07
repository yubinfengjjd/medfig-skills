---
name: medfig-plan
description: Use when the user needs to plan a set of medical research figures or tables before any drawing, such as deciding which results become main versus supplementary figures, how many panels each figure has and which chart type each panel uses, arranging panel layout and narrative order, planning main and supplementary tables, or writing a figure-set design spec for a medical imaging or clinical AI paper; also when the user asks 规划整套图表、主图附图怎么分、每个 panel 画什么、图表方案或出图规格. Do not use when only one imaging grid is needed, when a single already-specified chart just needs drawing, or for manuscript prose.
---

# medfig-plan：医学论文整套图表规划

产出一份规格文件 `docs/<YYYY-MM-DD>-figure-set-design.md`：每个 Figure 的 panel 清单（结论、数据、图型、理由、图注要求）、表格清单、口径裁决与来源索引。本技能只做规划，不写绘图代码。

## 硬门槛（HARD GATE）

- 用户明确批准规格之前，不写任何绘图代码、不跑任何出图脚本、不派 render 子代理。
- "批准"指用户对规格文件本身的明确认可（如"规格确认，开始画"）；对单个问题的回答不算批准。
- 规格批准后若要改 panel 结论、图型或主附图归属，先改规格并重新请用户确认，再动代码（D1, E8）。

## 边界与让位

| 情况 | 去向 |
|---|---|
| 只要一张纯影像网格（OCT/CT/MRI/病理拼图） | 直接用 scipilot-medimg-figure-skill |
| 已有明确规格，只画一张图 | medfig-render |
| 已有批准的规格，要批量出多图 | medfig-orchestrate |
| 写正文、摘要、润色 | 不属于本技能 |

## 流程总览

1. 盘点结果资产（派子代理）
2. 向用户提问并裁决口径冲突
3. 逐 panel 规划
4. 表格规划（含口径裁决表、图表来源索引）
5. 规格自检 → 交用户审阅 → 批准后转 medfig-render / medfig-orchestrate

每一步的详细规则在 `references/`：

- `references/panel_rules.md`：panel 字段、版式、panel 数、编码规则
- `references/chart_diversity.md`：结论类型 → 推荐图 / 禁用图 / 降级路径
- `references/table_plan.md`：主表、附表、口径裁决表、来源索引
- `references/spec_template.md`：规格文件模板
- `references/lessons.md`：经验规则（A/D/E 编号）
- `references/mainline_rules.md`：只呈现主线版本——早期版本与开发史不进图、表、图注、写作大纲（全部 medfig 技能共用）

## 第 1 步：盘点结果资产（派子代理）

派一个只读子代理通读项目文档（README、结果说明、口径/reconciliation 文档、已有图注）与结果目录，回交一张清单，主控不自己逐文件翻（保留上下文给规划）：

| 结果 | 文件 | 列 / 数组键 | 单位 | n（写明单位：scans / patients / groups） | 粒度（逐样本 / 汇总行） | 备注 |
|---|---|---|---|---|---|---|

子代理还必须回交：

- 文档间口径冲突清单：同一数字或定义在不同文档里说法不一（例：P 值、区间类型、样本数、方法定义）。每条列出处与原文。
- 缺失项：计划中提到但没有数据文件的结果（not collected / not estimable）。
- 影像资产：原始尺寸、是否经上游重采样、像素间距是否有文档依据、显著图原始量级（A6）。
- 只读约束：结果目录只读，子代理不得写入。

收到清单后，主控抽查 2–3 个关键数字回到源文件核实，再进入第 2 步（D7）。

## 第 2 步：向用户提问并裁决口径

一次问一组，能从盘点中推断的给出默认值让用户确认，不要逐条空问。必问：

1. 目标期刊（决定栏宽、字号下限、panel 标签格式）。
2. 主图数量上限（期刊限制或用户偏好）。
3. 语言：图内文字（默认英文）；规格、图注草稿、交付说明用什么语言。
4. 叙事顺序：主线结论是什么，主图按什么论证顺序排。编号跟正文首次引用走：主图、主表、附图、附表各自按首次引用从 1 编号，图内 panel 按叙述顺序从 a 排（先讲的放 a）；附图、附表按它们在 Results 里首次出现的顺序编号，不按产出顺序（medfig-outline 会检查，不符合就回来改号）。
5. **版本与开发史**：哪一个模型 / 分析版本是主线；哪些早期版本、失败的旧方案、内部开发阶段（如 wave、closure、修复前后）被**丢弃**。丢弃的版本在所有图、表、图注和写作大纲里都不出现，也不当作对照或补充实验（细则见 `references/mainline_rules.md`）；按内部计划组织的分析（如"预注册假设 H1–H5"）改成按它回答的科学问题组织。结果写进规格 §0。
6. 探索性结果去向：探索性结果放主图还是附图。图注和表题里不写"post-outcome exploratory"之类的开发流程说明，探索性质只在稿件 Methods 的统计部分用标准写法交代一次。
7. 示意图处理：研究设计图 / 流程图记为"示意图（外部绘制，本套不出图）"并在规格正文写内容描述，或删除并列入偏离；不渲染占位 panel（S2）。要用生图模型画的交给 medfig-schematic；要按已有参考图 1:1 复刻成可编辑矢量的交给 medfig-illustrator。
8. 口径冲突：把第 1 步冲突清单逐条列出，请用户裁决，或请用户指定一份权威文档，之后一律以它为准（A8）。

用户未答的项写进规格的"待确认"节，不得擅自假定。用户已经回答过的问题不再重复提问。

## 第 3 步：逐 panel 规划

每个 panel 必填五个字段，缺一个就不算规划完成（A1）：

| 字段 | 内容 |
|---|---|
| claim | 一句话结论（这个 panel 让读者相信什么） |
| data | 文件路径（相对数据根）+ 列 / 数组键 + 筛选条件 + 允许的确定性变换 |
| chart | 图型与编码（x / y / 颜色 / marker / 分面） |
| reason | 为什么选这个图型、为什么不选更常见的那个 |
| caption | 图注必须写的：单位、n 及其单位、区间类型与 bootstrap 方式、排除项、限制声明 |
| counterfactual | 结论不成立时这个 panel 会长什么样（例："若无改善，点云落在 y = x 上"）。答不出来，说明 panel 不承载证据：删掉或换数据（思路参考 taoge946/academic-figure-patterns，MIT） |

硬规则：

- 一 panel 一结论。一个 panel 要说两件事就拆开；说不出结论的 panel 删掉。
- panel 数与版式按论证定，不固定 4 个、不机械 2×2。每张图在标题行写明 panel 数与版式（例："3 panel；a 占左半，b/c 叠右"）（A2, A4）。
- 森林类图（forest / 点 + CI 横排）全套 ≤ 3 处，每处写一句为什么非它不可；其他重复图型也要写理由（A2）。
- x 有序（时间、剂量、阶段、k）才连线；类别 x 不连线。n 很小（如 n ≤ 5 个 seed / 受试者）画点不画柱；零值不画柱，改点图或删除该信息，不做纯文字 panel（A3, S2）。
- 数据撑不起原图型就降级：只有汇总行就画区间 / 点，不重建逐样本分布；取值离散就用分组柱不用 ECDF；只有一个交集就不用 UpSet（A3）。降级写进规格的"偏离"列（E8）。
- 影像 panel：先查原始量级和像素间距再选图（A6）；具体渲染规则交给 scipilot-medimg 与 medfig-render（见 `references/chart_diversity.md` 影像节）。
- **主图性能必须有曲线（硬规则，S7）**：主图里报判别性能（AUC、BACC、accuracy、sensitivity / specificity、recall、F1）且有逐样本分数时，这张图至少有一个曲线 panel：ROC，类别不平衡时再加 PR；图例写 "AUC = x (95% CI a–b)"，多 seed 写 mean ± SD。点估计 / 哑铃图可以作为补充 panel 保留，不能代替曲线。没有逐样本分数时降级为区间点，并在图标题行下写 `curve_exempt：<原因>`。
- **代表性病例影像要密、分组、分层（S6）**：按类别或队列分组并排；每组一行代表性原图 + 叠加，一个多病例图矩阵（每组 ≥ 12 例，全部病例共用一个色阶），一行局部放大。配方 `case_matrix.py`（`imaging.case_tiles` / `imaging.crop_window`）。只放 3–4 例的"代表性病例"会被读成挑图。
- **选例规则先定、写进图注和 source.json（S6）**：在看图像和模型输出之前，按组分层、用固定 seed 随机抽取，每组必须含误判病例；不按置信度或观感挑选。panel 写 `case_selection：` 字段（规则、seed、每组 n 及其中误判数、候选池）。候选池只是可用影像的子集时，图注写明。单病例报告页写 `case_selection：single illustrative case; exempt: <原因>`。选例用 `stats.stratified_cases`，记录写进 `values.case_selection`。
- 不可估计 / 未收集的结果不出图，进附表标 NOT_COLLECTED / not estimable（A5, A7）。
- 逐样本优先（默认偏好，不是硬规则）：有逐样本数据、结论又是关于样本的，主 panel 优先用逐样本图型（分布、ECDF、超越曲线、配对散点），汇总量做旁注或最小 panel；只用点 + CI 时在 reason 里写为什么。配对 / 机制散点先跑 `stats.structure_strength`，不过就换图型（差值分布、表格行），不改结果。
- 反模式（规划时排除）：逐样本数据存在却只画汇总（AP-15）；"什么都没发生"的对照 panel 占满一格，应压成窄条或并入相邻 panel（AP-19）；不承载结论的装饰结构，如无重叠点云上的等高线、无意义的分位带（AP-20）（参考 taoge946/academic-figure-patterns）。
- 红色 / 绿色只用于方向性含义（升 / 降、超过阈值、正 / 负贡献），不当作普通类别色（参考 xiao-yuling/sci-figure）。
- 柱子：默认主题从 0 开始，差异小改点 + 区间；soft 主题可以截断值轴，但必须画断轴标记，并在图注写明起点。显著性写精确 P（`stats.p_text`），不用星号。
- 有序类别（消融完整度、剂量、分级）可用单色相深浅梯度（`style.ordinal_gradient`，2–5 级，相邻 ΔE00 ≥ 12）；无序类别必须用不同色相。
- 主题：figkit.toml `theme = "default"`（默认）或 `"soft"`（一主多淡、平涂、柱顶数值，风格参考 senlanke/figures4papers）；同一套图只用一个主题，写进规格 §2。
- 期刊规格从 `figkit.journals` 取（来源、核对日期、VERIFIED / ESTIMATED）；ESTIMATED 条目投稿前到官网确认，写进规格"待确认"。
- 图内文字只放结果与读图编码：轴名、刻度、类别名、数值、n、图例，以及"实心 = 在集合内""色带 = seed 最小–最大值"这类读图必需的编码说明。免责声明（illustrative / not a clinical report）、方法口径（unweighted、seed-0 calibration、by construction）、结论句、限制声明、交叉引用（Table 6、Fig. 3）一律进图注，不画在图里，也不加图底注释行（`fig.text`）。
- 内部代号不进图：终点 / 假设 / 设计 / 规则编号（E1、H3、R2、D4、Wave-1）、数据列名（fluid_irf）一律换成读者能懂的描述名，规格 §2 写"内部代号 → 图内名称"对照表，并把这些代号和丢弃版本的名称写成 `figkit.toml` 的 `[qa] forbidden_patterns`，导出时硬拦；开发史通用词（wave、closure、repair、pre-registered、earlier version 等）由 figkit 默认拦截。图注同样不写内部代号和开发史。只表示出处的运行编号（"(seed 0)"）进图注；多个 seed 并排比较时才在图里出现 Seed 0/1/2。
- 图内数值按统一精度显示（规格 §2 写明，例如 3 位小数或 3 位有效数字），不出现原始浮点输出（+0.001268）。

图型选择查 `references/chart_diversity.md`；字段与版式细则见 `references/panel_rules.md`。
选定图型后查 medfig-render 的 `examples/gallery/INDEX.md`：有现成配方的 panel，在规格的 chart 列写上配方名和库函数（如 `decision.py` / `curves.decision`），渲染时直接调用，不重新手写。

主附图划分：主图跟主线论证顺序走；附图承载每个主结论背后的细节与稳健性，并在规格中写明"附图 ↔ 主图"对应（A5）。

## 第 4 步：表格规划

按 `references/table_plan.md`：

- 主表 + 附表，每张表写明内容、列、来源文件、输出格式（CSV + Markdown + LaTeX + source.json；Word 交下游）。
- 必备口径裁决表（ST11 式）：每条语义裁决或相对上游的修正，含权威文档、旧 → 新表述、上游文件 SHA-256 变化（A8, E7）。
- 必备图表来源索引（ST12 式）：由全部 source.json 自动生成，列出每个 panel 的输入路径、SHA-256、行数、变换；所有图导出后最后重建（A7）。
- 不可估计 / 未收集清单表，让缺口显式可见。

## 第 5 步：规格自检与用户审阅

按 `references/spec_template.md` 写成 `docs/<YYYY-MM-DD>-figure-set-design.md`，状态行写"待用户审阅"。交出前逐项自检：

1. 占位扫描：无 TBD / TODO / "适当的图"之类空话；每个 panel 五字段齐全。
2. 矛盾扫描：同一数字、定义、n 在规格各处一致，且与口径裁决表一致。
3. 歧义扫描：每个 data 字段能唯一定位到文件与列；变换写明且确定性。
4. 范围扫描：主图数 ≤ 用户上限；森林类 ≤ 3 处且每处有理由；每个结果要么有 panel、要么有表、要么在"不出图"清单里写明原因。
5. 措辞扫描：图注要求里包含限制声明，不写开发史和逐图的探索性声明（探索性质只在稿件 Methods 交代一次，`references/mainline_rules.md`），不使用禁用词（validated、superior、clinical benefit、diagnostic、clinically proven、deployment 等；项目可在 `figkit.toml` 的 `[qa]` 用 `banned_extra` 追加、`banned_allow` 放行默认词）（E1–E6）。
5a. 数据与冗余自检：运行 `python medfig-plan/scripts/data_health.py <数据文件...>` 生成数据体检单（缺失、重复行、每组 n、常数列），把发现写进规格 §1；规格写完后运行 `python medfig-plan/scripts/spec_check.py <规格.md>`：同一图内两个 panel 的 claim 相同、同一份 data 画两种 chart、缺字段（含 counterfactual）都会报出来，逐条处理或在 reason 里说明。
5b. 图内文字扫描：每个 panel 的 chart 字段里写的图内文字（标题、轴名、图例、注释）只含结果与读图编码；没有免责声明、口径、结论句、交叉引用和内部代号；代号对照表覆盖规格里出现的每个代号。
5c. 版本扫描：没有任何 panel、表或图注用到 §0 版本清单里的丢弃项；没有按内部计划编号组织的行（`references/mainline_rules.md`）。
5d. 曲线与选例扫描：每张报判别性能的主图有 ROC / PR 曲线 panel，否则写了 `curve_exempt`；每个病例影像 panel 有 `case_selection`（seed、每组 ≥ 12 例、含误判、候选池），单病例页写明 exempt。`spec_check.py` 会报这两类缺项。
6. 偏离清单：所有降级、合并、删除、示意图外部绘制都列出（E8）。
7. 样式扫描（S1–S7，见 `references/panel_rules.md` §6）：影像列 width_ratios 按图像宽高比、左右留白 ≤ 15%；无纯文字 panel；每 panel 数据图元有 Okabe-Ito 色且方法色不撞队列色；每 panel 写明 panel_file（单独 PDF（必需）+ SVG，无 a/b/c）；ROC 为共同 FPR 网格 mean ± SD 样式；S6 病例矩阵与选例、S7 主图曲线。

然后把规格路径交给用户，列出"待确认"项，等待明确批准。用户提出修改就改规格、重新自检、再次请审，直到批准。

## 批准后的下一步

- 只画其中一张图：转 medfig-render（按规格逐 panel 实现，统一经 `export.save` 导出）。
- 整套出图：转 medfig-orchestrate（规格 → 实施计划 → 并行子代理 → 审查 → 交付）。
- 纯影像网格 panel：由 medfig-render 调用 scipilot-medimg-figure-skill 的影像规则。

## 常见错误

| 错误 | 纠正 |
|---|---|
| 每张图都 4 个 panel、2×2 | 按论证定 panel 数与版式 |
| 到处是森林图 | 全套 ≤ 3 处，其余按 chart_diversity 选 |
| n = 3 画柱 + 误差棒 | 画点，标 n |
| 汇总表硬画小提琴 / ridgeline | 降级为区间点，并写进偏离 |
| 主图性能只有点估计 / 哑铃图，ROC 放在附图 | 主图加 ROC（不平衡加 PR）曲线 panel；点估计留作补充 |
| 影像只放 3–4 个"代表性病例" | 分组 × 每组 ≥ 12 例的分层矩阵，固定 seed 分层随机、含误判 |
| 显著图原始量级接近数值噪声仍逐图归一化展示 | 不展示，换可信的图，图注说明原因 |
| 口径冲突自行选一个 | 交用户裁决或指定权威文档，写进口径裁决表 |
| 规格还没批准就开始写脚本 | 违反硬门槛，停下 |
