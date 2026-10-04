# Changelog

## 0.2.0 (2026-10-07)

- 新技能 `medfig-outline`：图表定稿后生成 Methods / Results 写作大纲（`写作大纲.docx` + `.md`），并把每个小节引用的图、表、图注和代码拷贝到项目外的分节文件夹。
  - Results 每节标题用一句话概括发现；Methods 不写结果数字。
  - `outline_check.py`：大纲里的每个数对照 `source.json` / 表格回核（按写出的位数四舍五入，支持百分数、分数、带符号值），检查引用的 panel / 表是否存在、每个主图是否被覆盖、禁用词、开发史和项目代号。
- 只呈现主线版本（`medfig-plan/references/mainline_rules.md`，全部技能共用）：早期版本不当对照或补充实验，按内部计划编号组织的分析改成按科学问题组织，图注不逐图写探索性声明。
  - figkit 新增 `qa.DEV_HISTORY`：图内出现 pre-registered、closure、wave-N、earlier version、repair、post-outcome 等词时导出失败；`qa.dev_history_in_text` 供图注 / 表格 / 大纲检查。
  - `medfig-plan` 第 2 步新增必问项"版本与开发史"，规格 §0 写版本清单。
- `medfig-outline` 写法收紧：大纲是给作者的写作提示，不是数据表。检查脚本限制每节 ≤ 3 段、每段 ≤ 3 条要点、每条 ≤ 70 字且 ≤ 2 个结果数字（区间算一个），不以"引用 Fig …"开头；出处并到段落行末，代码每个角色一行。

## 0.1.0 (2026-10-07)

首个公开版本。

- 四个技能：`medfig-suite`（路由）、`medfig-plan`（规划）、`medfig-render`（单图渲染，内含 figkit 库）、`medfig-orchestrate`（批量出图）。
- figkit：配置、样式、溯源（source.json + SHA-256）、导出与质检闸门（几何、字号、真减号、留白、纯文字 panel、S3 着色、色差、图内文字审计、柱轴截断）。
- 20 个 panel 配方（`medfig-render/examples/gallery/INDEX.md`）。
- 可选 soft 主题（一主多淡、平涂柱、柱顶数值、断轴标记）。
- `figkit.journals` 期刊规格表（Nature、npj、Science、Cell、Elsevier、Medical Image Analysis、IEEE），每条带来源、核对日期和 VERIFIED / ESTIMATED 状态。
- 规划自检脚本 `data_health.py`、`spec_check.py`。
