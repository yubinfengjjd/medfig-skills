---
name: medfig-schematic
description: Use when a medical or clinical AI paper needs a schematic figure, such as a study-design diagram, cohort flow, model or network architecture diagram, training-stage overview or inference / explanation pipeline (Fig 1 类示意图、研究设计图、网络架构图、模型结构图、流程示意图), and the figure is to be drawn by an image-generation model such as ChatGPT / GPT image; covers writing the English prompt, checking it, packaging each round, and evaluating the returned image round by round until the user is satisfied. Do not use for data plots, statistical panels or image grids (medfig-render / scipilot-medimg-figure-skill), for CONSORT diagrams with real patient counts, or for drawing the schematic directly in code.
---

# medfig-schematic：用生图模型画示意图（提示词 → 检查 → 评估 → 下一轮）

本技能不画图。它写英文提示词，用户把提示词贴进生图模型（ChatGPT 网页版等），把出图发回来；本技能检查出图、写评估，再写下一轮提示词，直到用户满意。生成的图是**草稿**：真实影像、终稿字号和矢量化在 Illustrator 里完成。

## 硬门槛（HARD GATE）

- **结构事实先从代码核对。** 模块顺序、分支与汇合、冻结 / 训练的部分、层数和维度，都从模型代码与配置读出，不只信文档或口述。用户的说法和代码冲突时，按代码写，同时把冲突和出处告诉用户，由用户决定（P8）。
- 示意图只放**设计数字**（结构参数、方法设定、阶段编号），不放结果数字、内部代号、开发史和丢弃的旧版本（`medfig-plan/references/mainline_rules.md`）。
- 影像位一律是空框，生成模型不画任何医学影像（P7）。
- 每轮提示词先过 `prompt_check.py`（0 个 ERROR）才交给用户。

## 第 1 步：问清楚（一次问完）

- 图的主信息：读者看完这张图要记住什么（例如"影像 → 可解释中间量 → 决策"）。
- 行数和每行内容（默认三行：a 研究设计 / 队列，b 模型与训练阶段，c 一例推断、解释与不确定性）。
- 生图工具、尺寸（Nature 双栏 180 mm 宽，横版 3:2）、色板（沿用数据图的 `figkit.toml`：类别色、方法色）。
- 有没有参考图；有的话每张管什么（内容还是画法）。没有就用默认画风（`references/style_default.md`）。
- 影像：要哪些空位、比例多少；真实影像由谁、在哪一步贴入。

## 第 2 步：建工作目录和规格

工作目录放在项目之外（例如 `<输出根>/fig1_prompt/`）。写 `schematic.yaml`（`references/spec_format.md`）：色板、全部标签原文、允许出现的数字、影像位、禁用代号。

再从代码读出结构事实，写进 `round1.md` 开头的"结构事实"表（事实 / 出处：配置键或 `文件:函数`）。

## 第 3 步：写提示词（`roundN.md`）

每轮一个 `roundN.md`，内容按这个顺序：

1. 上一轮评估表（第 1 轮没有）：方面 / 结果（通过 / 部分通过 / 不通过）/ 说明。逐项按 `references/evaluation.md`。
2. 用法：新对话还是同一对话；先上传哪些图、每张的用途；再粘贴 `prompt.txt`。
3. 提示词：**唯一一个** ```` ```text ```` 代码块，英文。
4. 中文说明：这一轮改了什么、为什么；和用户说法不一致的地方单独列出。
5. 本轮评估清单（新增项加粗），供出图后打勾。

两种提示词：

- **完整提示词**（第 1 轮、换视觉语言时，开新对话）：全局风格 + 逐行模块 + TEXT RULES。风格块从 `references/style_default.md` 拼，用户给了参考图就按参考图改写。
- **局部修改**（同一对话）：开头写 "Keep everything else exactly as it is. Only make these changes:"，编号列出 ≤ 6 条改动；已通过、不能动的部分点名保护（R2–R4）。

写法要点（细则 `references/prompt_patterns.md`）：标签原样加引号（P2）；箭头写完整路径和绕行方向（P3）；"不连"要明说（P4）；颜色写色值、一色一用途（P5）；数量写清前后分段（R6）。

## 第 4 步：检查并打包

```
python medfig-schematic/scripts/round_pack.py --dir <工作目录> --round N \
    [--prev-output <用户发回的上一轮图>] [--upload <要上传的图> --as <新文件名>] ...
```

- 把上一轮出图存为 `round{N-1}_output.png`，把提示词抽成 `roundN_upload/prompt.txt`，复制要上传的图，并自动跑 `prompt_check.py`（完整 / 局部模式按 "Keep everything else" 自动判定）。
- 有 ERROR 就改 `roundN.md` 重新打包，直到显示 `ready`。WARN 逐条看，确实无关的在中文说明里写一句为什么保留。
- 单独检查：`python medfig-schematic/scripts/prompt_check.py prompt.txt --spec schematic.yaml --mode full|edit`。

## 第 5 步：交给用户

告诉用户：开新对话还是在原对话里继续；按顺序上传 `roundN_upload/` 里的哪几张图；粘贴 `prompt.txt`。再说一句这一轮最可能出错的地方，下一轮先查那一项。

## 第 6 步：评估返回的图

1. `python medfig-schematic/scripts/image_check.py <图> --spec schematic.yaml`：比例、分辨率、偏离色板的颜色、类别色是否都出现、灰度可分性。
2. 读图目检，按 `references/evaluation.md`：**先逻辑后美术**（R1）。层数、格子数逐个数。
3. 写进下一轮 `roundN+1.md` 的评估表，回到第 3 步。

用户说"差点意思"但说不清楚时，对照 `references/prompt_patterns.md` 的 S1–S5 找原因，先给用户讲清原因再出下一轮。用户给新参考图时，先分析它为什么好看（实色、粗箭头、模块感……），再决定改哪几行。

## 第 7 步：定稿

逻辑全部通过、美术无"不通过"项、用户确认满意后交付：定稿图路径、最后一轮提示词、结构事实表、Illustrator 待办（贴真实影像；把漂移的类别色改回色板值（R8）；按成品宽度核对字号 ≥ 5–6 pt；需要时重绘为矢量）。规格里这张图的状态仍是"示意图（外部绘制）"，写作大纲里按 `pending` 引用（medfig-outline）。

## 常见借口

| 借口 | 实际 |
|---|---|
| "用户说编码器只在第 2 阶段训练，就这么画" | 先查代码；冲突时按代码画，并请用户裁定，Methods 要和图一致 |
| "再说一遍'补上箭头'就好" | 同一句话第二次也会被忽略；写出完整路径（R5） |
| "这轮顺便把风格也改了" | 逻辑没过就改风格，版式会漂；先逻辑后美术（R1） |
| "模型自己会保持没提到的部分" | 不会；点名保护已通过的行（R3） |
| "加几个结果数字更有说服力" | 示意图只放设计数字；结果在 Results 的图里 |
| "让模型直接画视网膜，省得贴图" | 生成的影像不真实，审稿人看得出；只留空框 |
| "整张图都做成 3D 更高级" | 3D 只给网络和张量；其余行扁平，避免海报感 |
| "出图分辨率低，重新生成一张" | 生成图是草稿，终稿在 Illustrator 里定；分辨率 WARN 正常 |

## 参考文件

- `references/spec_format.md`：`schematic.yaml` 字段与结构事实表
- `references/style_default.md`：默认画风（可拼进提示词的英文块）与理由
- `references/prompt_patterns.md`：提示词写法（P）、迭代（R）、审美差距（S）
- `references/evaluation.md`：出图评估清单、`image_check` 输出的处理、定稿条件
- `medfig-plan/references/mainline_rules.md`：只呈现主线版本（全部 medfig 技能共用）
