# Changelog

## 0.4.0 (2026-10-06)

- 新技能 `medfig-schematic`：研究设计图、模型 / 网络架构图这类示意图，由生图模型（ChatGPT 网页版等）绘制。本技能写英文提示词，用户贴进生图模型、把出图发回，技能评估后写下一轮提示词，逐轮迭代到用户满意。生成图是草稿，真实影像和终稿在 Illustrator 里完成。
  - `schematic.yaml` 规格：色板、全部标签原文、允许的设计数字、影像空位、禁用代号。结构事实（层数、维度、各阶段训练哪些模块）从代码核对。
  - 默认画风：流程行用实色浅底方块和约 2 pt 箭头；模型行用克制的 3D（薄片、张量立方体、统一斜投影），并画训练阶段线和符号图例。用户给参考图时以参考图为准。
  - `prompt_check.py`：加引号的文字必须是规格标签；色值必须在色板里；不得出现结果数字、内部代号、开发史词和中文；影像位必须声明为空框；完整模式要求写明尺寸和 TEXT RULES，局部修改模式要求写明"其余保持不变"；没有给路径的箭头会提示。
  - `round_pack.py`：存档上一轮出图，从 `roundN.md` 抽出 `prompt.txt`，收集要上传的图，并自动检查提示词。
  - `image_check.py`：检查比例和分辨率、偏离色板的颜色（浅色调不计入）；按色相找到类别色，报告颜色漂移（例如要求 `#0072B2`，画成了亮蓝）和灰度可分性，并区分"色板本身灰度接近"和"画漂后接近"。
  - 迭代经验（提示词写法、迭代规则、和顶刊示意图的常见差距）和逐项评估清单。
- `medfig-suite`、`medfig-plan`、`medfig-render` 把示意图路由到 `medfig-schematic`；`install.py` 一起安装。
- figkit 导出：PDF 里的栅格图一律写成 8 位 DeviceRGB。matplotlib 会把 ≤ 256 色的图存成 /Indexed 调色板，Illustrator 置入后热图变浅、白色标签消失。导出后增加 `pdf_image_issues` 检查。
- figkit 导出：PDF 字体名去掉子集前缀（`ArialMT`，Illustrator 不再报字体缺失）；数学文本用正文字体，不再混入 DejaVu；增加 `pdf_font_issues` 检查。

## 0.3.1 (2026-10-07)

- `medfig-outline` 引用次序闸门：按阅读顺序（Methods → Results），主图、主表、附图、附表各自按首次引用从 1 连续编号，图内 panel 从 a 开始依次首次引用；次序不对时给出"旧 → 新"改号建议。骨架确认时把改号表交给用户，确认后回 medfig-render 改图再写大纲。
- 全覆盖：正文与补充材料的每张图、每个 panel、每张表都必须被引用，不进稿件的写进 `excluded` 并给理由；检查脚本打印 `coverage: N/N`，大纲末尾生成"图表引用清单"表。
- Methods 只能引用设计资产（`design_assets`：数据集表、研究设计图、方法类附表），其余结果在 Results 首次引用；外部绘制、尚未导出的图用 `pending` 声明。
- 大纲不再列出或拷贝绘图 / 表格脚本，代码只列分析代码；每个被引用的图表配一行"图 / 表"，写它在科学上说明什么。
- `medfig-plan`：编号跟正文首次引用走，panel 按叙述顺序从 a 排。

## 0.3.0 (2026-10-05)

- 仓库现在包含依赖技能 `scipilot-medimg-figure-skill`（派生自 Haojae/scipilot-figure-skill @43098dd，MIT），`install.py` 与五个 medfig 技能一起安装，不再需要另外下载。
  - 新增合成数据冒烟测试：影像 panel 渲染与导出、"类别语义不猜""掩膜不缩放"两条拦截、样式 / 导出 / 文件自检。
  - 文档清理：示例键名改为中性名称，README 安装说明改为本仓库。
- 新增仓库级 `requirements.txt`（运行）与 `requirements-dev.txt`（测试），版本固定为测试通过的组合。
- CI 改为 `pip install -r requirements-dev.txt` + `python install.py`，与用户安装方式一致，不再克隆上游。

## 0.2.0 (2026-10-07)

- 新技能 `medfig-outline`：图表定稿后生成 Methods / Results 写作大纲（`写作大纲.docx` + `.md`），并把每个小节引用的图、表、图注和代码拷贝到项目外的分节文件夹。
  - Results 每节标题用一句话概括发现；Methods 不写结果数字。
  - `outline_check.py`：大纲里的每个数对照 `source.json` / 表格回核（按写出的位数四舍五入，支持百分数、分数、带符号值），检查引用的 panel / 表是否存在、每个主图是否被覆盖、禁用词、开发史和项目代号。
- 只呈现主线版本（`medfig-plan/references/mainline_rules.md`，全部技能共用）：早期版本不当对照或补充实验，按内部计划编号组织的分析改成按科学问题组织，图注不逐图写探索性声明。
  - figkit 新增 `qa.DEV_HISTORY`：图内出现 pre-registered、closure、wave-N、earlier version、repair、post-outcome 等词时导出失败；`qa.dev_history_in_text` 供图注 / 表格 / 大纲检查。
  - `medfig-plan` 第 2 步新增必问项"版本与开发史"，规格 §0 写版本清单。
- `medfig-outline` 按论证规划骨架：支持多级小节（训练按阶段拆成 2.3.1、2.3.2 …），Results 5–8 个大节（少于 5 节需写明课题理由）、一节可用多张图；检查脚本报出"一张图一节、两边节数相同"的平铺结构、只有一个小节、要点过少的节；小节文件夹嵌在大节文件夹里。
- `medfig-outline` 写法收紧：大纲是给作者的写作提示，不是数据表。检查脚本限制每节 ≤ 3 段、每段 ≤ 3 条要点、每条 ≤ 70 字且 ≤ 2 个结果数字（区间算一个），不以"引用 Fig …"开头；出处并到段落行末，代码每个角色一行。

## 0.1.0 (2026-10-07)

首个公开版本。

- 四个技能：`medfig-suite`（路由）、`medfig-plan`（规划）、`medfig-render`（单图渲染，内含 figkit 库）、`medfig-orchestrate`（批量出图）。
- figkit：配置、样式、溯源（source.json + SHA-256）、导出与质检闸门（几何、字号、真减号、留白、纯文字 panel、S3 着色、色差、图内文字审计、柱轴截断）。
- 20 个 panel 配方（`medfig-render/examples/gallery/INDEX.md`）。
- 可选 soft 主题（一主多淡、平涂柱、柱顶数值、断轴标记）。
- `figkit.journals` 期刊规格表（Nature、npj、Science、Cell、Elsevier、Medical Image Analysis、IEEE），每条带来源、核对日期和 VERIFIED / ESTIMATED 状态。
- 规划自检脚本 `data_health.py`、`spec_check.py`。
