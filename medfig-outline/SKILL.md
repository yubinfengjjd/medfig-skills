---
name: medfig-outline
description: Use when a medical research figure set is finished and the user wants a writing outline for the manuscript Methods and Results built from the final figures, tables and captions, such as which subsections to write, what each paragraph should say, which Fig panels and Tables each paragraph cites, key numbers to report, and which code produced each result; also when the user asks 写作大纲、按图写 Methods 和 Results 的提纲、每节写什么、各小节文件归档. Do not use before the figures are final, for drawing figures, or for writing the full manuscript prose, Introduction or Discussion.
---

# medfig-outline：成品图表 → Methods / Results 写作大纲

输入是已经定稿的整套图表（规格、`source.json`、表格、图注草稿、图脚本）；输出是一份写作大纲（`写作大纲.docx` + 同内容 `写作大纲.md`）和按小节分好的文件夹。大纲只写 Methods 和 Results，不写 Introduction / Discussion，也不写正文成稿。

## 硬门槛（HARD GATE）

- 图表未定稿（还在改图、未交付）时不出大纲，回 medfig-render / medfig-orchestrate。
- **小节划分与图表归属先在对话里给用户确认**，确认后才写要点、生成 docx 和拷贝文件夹。
- 只呈现主线版本：早期版本、修复前模型和开发史不进大纲（`medfig-plan/references/mainline_rules.md`）。

## 第 1 步：盘点

读规格（版本清单、主线、代号对照表）、每张图的 `source.json`（`values` 里的数、`inputs` 的数据文件、`transforms`）、表格（CSV / md）、图注草稿、图脚本与表格脚本路径；有上游分析仓库时记下它的根目录。只读，不改任何项目文件。

## 第 2 步：骨架确认（对话里，一次问清）

给用户一张骨架表（含小节），等确认后再往下走。骨架按论证规划，不按图平铺（细则 `references/outline_format.md` §6）：

- **Methods 按读者复现的顺序**：数据 → 模型结构 → 训练过程 → 评估与统计 → 附加分析。多步骤的过程拆成小节（训练按阶段写成 2.3.1 Stage 1、2.3.2 Stage 2 …；对照与消融单独一小节）。不按图分节。
- **Results 按论证组织**：**5–8 个大节**为宜，每节回答一个问题，按论证顺序排（例如 队列与前端 → 内部性能 → 外部迁移 → 机制 → 解释 → 不确定性）；一节可以用多张图，一张图的不同 panel 可以分到不同节；内容多的大节再分 2–3 个小节。少于 5 节只在课题思路确实需要时才用，并在 `results_fewer_sections_reason` 里写明理由，否则检查脚本报错。不要为了"紧凑"把不同问题合进一节。按内部计划组织的分析（如预注册假设）拆进它回答的科学问题所在的节。
- 两边的节数由内容决定，不要求相等；"Methods 与 Results 节数相同且每节恰好一张图"是平铺的信号，检查脚本会报。
- 只有一个小节就不设小节；每个末级节至少 2 条要点，否则并回上一级。
- 标题：Results 大节**一句话概括发现**（英文）+ 中文副标题，小节可用短标题；措辞不超出数据，标题不放数字。Methods 标题写方法或步骤名。
- 从代码 / 配置推断、没有文档依据的训练细节，在要点后标"（待核）"，并在问题清单里列出。
- 文件夹结构（见第 5 步）：小节文件夹放在大节文件夹里。
- 不确定项（某图归哪节、某分析是否进大纲、训练步骤细节）列成问题，一次问完；已答过的不再问。
- **引用次序与改号表**（细则 `references/outline_format.md` §7）：按骨架的阅读顺序（Methods → Results）排出每个图、表、panel 的首次引用。主图、主表、附图、附表各自从 1 连续编号，同一张图的 panel 从 a 开始依次首次引用。不符合时先看能不能调叙事；叙事顺序更合理就改编号。把"旧 → 新"改号表（含 panel 字母对调）和骨架一起给用户确认。确认后回 medfig-render 改图、重新导出，再写大纲；大纲里的编号与导出文件始终一致。
- **Methods 能引用的资产**：只有设计资产（数据集表 Table 1、研究设计 / 框架图 Fig 1、方法类附表如不可估计项清单），在骨架里列成 `design_assets` 给用户确认。其余结果全部放在 Results 里首次引用。
- 没有被任何一节引用的图、panel、表要么找到它该在的位置，要么列进 `excluded` 并写理由（过程记录、溯源索引这类不进稿件）。一并问用户。

## 第 3 步：写大纲内容（`outline.yaml`）

按 `references/outline_format.md` 写一份 `outline.yaml`（结构化，脚本据此检查和渲染）。每节：

- Methods：`focus`（写作重点，按主题分块、每块若干要点；**不写结果数字**，样本量写量级或结构）、`foreshadow`（可选，为后文埋的伏笔）、`items`（可选，引用的设计资产 + 一句它交代了什么）、`code`（分析代码，"只作为你脑内映射"）。
- Results：`paragraphs`（第一段 / 第二段 / 第三段，**≤ 3 段**；每段 = 一句结论 + 出处 + ≤ 3 条要点）、`items`（图 / 表：本节首次引用的每个图 / 表一行，写它**在科学上说明什么**，不写怎么画的）、`code`（分析代码）、`boundaries`（措辞边界，≤ 3 条）。
- **写法**：要点是给作者的提示（"点出…""对比…""一句话带过…"），不是待抄的结果句；每条 ≤ 70 字、≤ 2 个结果数字，每段 ≤ 4 个数，其余写"见 Table X"。不以"引用 Fig …"开头，同一开头不反复。细则和改写示例见 `references/outline_format.md` §5，检查脚本按这些限值报错。
- **曲线与病例矩阵**：引用 ROC / PR 曲线 panel 的段落点出 AUC（95% CI 或 mean ± SD）和比较对象；引用病例矩阵的段落点出其中含误判病例。有病例矩阵的图（`values.case_selection`），选例规则（分层、固定 seed 随机、每组例数含误判、候选池）在 Methods 评估 / 统计小节写一条要点，检查脚本会核对 seed 和"随机"。
- Results 的数值写约数 / 区间（"QWK 约 0.64–0.66"），每个数在 `numbers` 里登记出处（`source.json` 的键路径或表格的行列）；Methods 末节（统计）用标准写法交代一次研究的探索性质，其余地方不写。
- 内部代号：正文用描述名，第一次出现可括注代号便于对照原始材料（例如"三分类（内部代号 E2）"）；丢弃版本的名称和开发史词一律不出现。
- 代码：只列产生结果的分析代码（训练、评估、统计），按 `source.json` 的数据文件名匹配上游仓库，标"（推测）"，找不到写 `TODO`。**绘图脚本和表格脚本不列、不拷**：它们只是把结果画出来，不属于方法；大纲引用输出的图 / 表，并说明它的科学意义。

## 第 4 步：检查

```
python medfig-outline/scripts/outline_check.py outline.yaml --project <项目根> [--figkit-toml <toml>]
```

报错即修，直到 0 条：

- 每个登记的数能在对应 `source.json` / 表格里找到（按写出的位数四舍五入一致）；Results 段落里出现的每个数都已登记。
- 引用的每个 Fig panel / Table 真实存在；每个主图至少被一个 Results 节覆盖。
- Methods 的 `focus` 不含结果数字（年份、维度、样本量量级之类用 `allow_numbers` 放行）。
- 引用次序：四个编号序列都按首次引用连续编号，panel 从 a 开始；每个导出的图、panel、表都被引用或列进 `excluded`；Methods 只引用 `design_assets`。次序不对时报出改号建议。
- 有病例矩阵的被引用图：Methods focus 里写了选例规则（含该图 `values.case_selection.seed` 与"随机 / random"）。
- 每个被引用的资产都有一行"图 / 表"说明科学意义；`code` 里没有绘图 / 表格脚本。
- **全覆盖**：正文和补充材料的每张 Fig、每个 panel、每张 Table 都在大纲里被引用。检查脚本最后打印 `coverage: N/N manuscript assets cited`，不是全数就不交付。外部绘制的图（`pending`）也要被引用；导出时没记录 panel 清单的图会报错，因为无法核对 panel 覆盖。
- 禁用词（`qa.banned_in_text`）、开发史（`qa.dev_history_in_text`）、项目代号（`[qa] forbidden_patterns`，括注"内部代号"的位置除外）。

## 第 5 步：生成与归档

```
python medfig-outline/scripts/outline_build.py outline.yaml --project <项目根> --out <项目根之外的目录>
```

- 大纲末尾附"图表引用清单"表：按编号列出全部主图、主表、附图、附表，以及各自的 panel、首次引用小节、全部引用小节和状态（已引用 / 外部绘制待交付 / 不进稿件：理由）。作者写完正文可以照表逐项核对。
- 生成 `写作大纲.docx`（版式照用户的参考大纲：英文小节标题；Results 加中文副标题一行；"写作重点 / 写作要点 / 图 / 表 / 相关代码 / 措辞边界"作小标题；层级用缩进，Word 打开即可读）和同内容 `写作大纲.md`。
- 按小节**拷贝**（不移动、不改原项目）：

```
<out>/
  写作大纲.docx  写作大纲.md
  2_Methods/2.3_<短名>/2.3.1_<短名>/ …        小节文件夹在大节文件夹里
  3_Results/3.1_<短名>/3.1.2_<短名>/ …
      figures/   该节引用的图（PDF + PNG + source.json）
      tables/    该节引用的表（md + csv + tex）
      captions/  该节相关图的图注草稿
      code/      code.md（分析代码路径清单，含"推测"与 TODO）+ 能找到的分析脚本；不放绘图 / 表格脚本
```

一个文件被几节同时用到时每节各拷一份，每个文件夹单独打开都完整。输出目录必须在项目根之外，已存在时先列出内容再问用户是否覆盖。

## 第 6 步：交付

告诉用户：docx 路径、文件夹路径、每节一行（标题 + 引用了哪些图表）、检查结果（多少个数已回核；引用次序 0 条问题；覆盖 N/N）、本次应用的改号表、`excluded` 清单、TODO 清单（找不到出处的代码、`pending` 的外部绘制图等）。请用户用 Word 打开 docx 目视。

## 常见借口

| 借口 | 实际 |
|---|---|
| "一张主图一节最省事" | 那是图的目录，不是论文的论证；按问题组织，一节可以用多张图 |
| "Methods 和 Results 对称看起来整齐" | 节数由内容决定；训练这类多步过程拆小节，简单的事合并 |
| "数字我记得，不用回核" | 每个数登记出处并由脚本对照 `source.json`，记错一位就会进稿件 |
| "预注册假设单独一节更清楚" | 按内部计划组织会把开发过程写进稿件；按科学问题拆进对应小节 |
| "标题写'X 的结果'就行" | Results 标题要一句话写出发现，读者只看标题也知道结论 |
| "代码找不到就先空着" | 写 `TODO` 并在交付时列出，不要留空或猜一个路径不标"推测" |
| "数字多写几个更完整" | 大纲是提示不是数据表；精确值在图注和表里，大纲只点出正文必须提到的一两个数 |
| "每个队列都列出来才不遗漏" | 点出最高 / 最低和范围，逐队列数值交给表格 |
| "panel 顺序在图里已经定了，正文跳着引用也行" | 稿件按首次引用编号，先引 d 再引 a 会被要求返修；调叙事或交换 panel 字母 |
| "大纲里先用新编号，图以后再改" | 编号对不上，作者会照错的图写；先改图、重新导出，再写大纲 |
| "绘图脚本也是代码，列上更完整" | 画图不是方法；写清图 / 表说明什么，代码只列产生结果的分析代码 |
| "Methods 里提一下结果图，读者更好懂" | Methods 只引用设计资产（数据集表、设计图、方法类附表），结果在 Results 首次出现 |

## 参考文件

- `references/outline_format.md`：`outline.yaml` 字段、docx 版式、数字登记写法
- `medfig-plan/references/mainline_rules.md`：只呈现主线版本（全部 medfig 技能共用）
