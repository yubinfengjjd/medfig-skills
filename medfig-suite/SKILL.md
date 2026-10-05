---
name: medfig-suite
description: Use when the user wants a complete set of figures and tables (and the Methods / Results writing outline built from them) for a medical or clinical AI manuscript (整套论文图表, 主图/附图, Figure 1 to N, 结果转成论文图) and it is unclear where to start, or wants to go from analysis results to publication figures that mix medical images with statistical panels (影像 + 统计混排). Also use when choosing between planning a figure set, rendering one planned figure, or batch-producing many figures for a medical paper. Not for a single pure image grid of exported images with masks, contours or heatmaps (scipilot-medimg-figure-skill), not for a schematic or architecture diagram on its own (medfig-schematic), and not for non-medical charts.
---

# medfig-suite — 医学论文图表路由

本技能只做路由：判定任务该交给哪个技能，并列出下游需要的输入。本技能不画图、不写规格、不改任何其他技能的文件。

判定细节、边界例子与失败处理见 [routing.md](references/routing.md)。

## 路由（两条分支，命中即停）

### A. 只要一张纯影像网格 → scipilot-medimg

同时满足才走这条：素材是已导出的 PNG/JPG/TIF 影像，叠加物只有掩膜、轮廓、热力图（Grad-CAM 等）、放大框、箭头、比例尺；没有统计图混排；只有一张，不属于整套规划。直接用 `scipilot-medimg-figure-skill` 的「医学影像 panel 工作流」（JSON spec + `image_panel.py`）。

### B. 其他医学论文图表任务 → medfig 主线

- 还没有图表规格 → `medfig-plan`，产出 `docs/<date>-figure-set-design.md`。
- 规格已定，只画一张图 → `medfig-render`。
- 规格已定，要出多张或整套 → `medfig-orchestrate`（内部逐图调用 medfig-render）。
- 规格与数据或文档口径冲突、已过时 → 回 `medfig-plan` 修规格。
- 图表已定稿，要 Methods / Results 写作大纲或按小节归档文件 → `medfig-outline`。
- 研究设计图、模型 / 网络架构图、流程示意图（用 ChatGPT 等生图模型画）→ `medfig-schematic`。

## 决策表

| 条件 | 去向 |
|---|---|
| 单张纯影像网格（无统计图） | scipilot-medimg-figure-skill |
| 无规格，要整套或单图 | medfig-plan |
| 有规格，一张图 | medfig-render |
| 有规格，多张 / 整套 | medfig-orchestrate |
| 已出图，只要按清单复审 | medfig-orchestrate 的审查清单 |
| 图表定稿，要写作大纲 / 分节归档 | medfig-outline |
| 示意图、研究设计图、网络架构图（生图模型画） | medfig-schematic |
| 非医学图表；用代码直接画示意图 | 不在本套范围，告诉用户 |

## 下游需要的输入

交接前确认这些输入就位；缺了就先问用户或回上一步。

- scipilot-medimg：影像文件路径；掩膜 `{灰度值: 类别名}` 映射及出处；热力图数值含义；有 `pixel_spacing_um` 才画比例尺。
- medfig-plan：结果资产目录（表格 / 数组 / 影像）、相关文档、目标期刊、主图数量意向、图内语言。
- medfig-render：已确认的规格（逐 panel 结论、数据文件与列、图型）、项目根的 `figkit.toml`、输出名与尺寸。
- medfig-orchestrate：已确认的整套规格、git 仓库（用于 worktree 并行）、`figkit.toml`、`docs/_process/` 台账位置。
- medfig-schematic：图的主信息与每行内容、模型代码 / 配置位置（核对结构事实）、色板（`figkit.toml`）、尺寸、参考图（可选）、项目外的工作目录。
- medfig-outline：定稿的规格、`out/figures` 下的 `source.json`、表格、图注草稿、图脚本；可选的上游分析仓库根目录；大纲输出目录（项目外）。

## 红线

- 不修改任何其他技能的文件（包括 scipilot-medimg）。
- 路由不确定时从分支 A 重新判定，不跳步。
- 用户只授权某一步时，只交付这一步的范围。
- 全流程只呈现主线版本：早期版本、修复前模型和开发史不进可视化编排、示意图、图注和写作大纲（`medfig-plan/references/mainline_rules.md`）。
