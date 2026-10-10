# Changelog

## 0.6.2 (2026-10-11)

`medfig-outline` 分节代码归档：

- 各小节 `code/` 里拷贝分析代码的原文件（含标"推测"的），按文件名平铺，同名文件保留各自的相对路径；不再生成 `code.md` 清单（路径与"推测"标注在大纲"相关代码"里）。
- `outline.yaml` 新增 `code_roots`：上游分析仓库不在项目根下时，`code` 路径按这些目录依次查找（替换未实现的 `upstream_root`）。
- `outline_check.py` 新闸门：`code` 列出的路径（`TODO` 除外）必须能找到。

## 0.6.1 (2026-10-08)

小多图编排（S8）：

- `medfig-plan`：新规则 S8。同一 panel 的分面格优先一行；放不下时最后一行居中，不左对齐留空位。各格图例相同时只画一次，逐格数值用同色文字。与相邻分面 panel 按同一组队列 / 类别分面时列对齐。
- `medfig-render`：`layout.small_multiples` 末行默认居中、`ncols` 不超过格数；`curves.roc_mean_sd` / `pr_mean_sd` 新增 `legend`、`linestyle` 参数；新函数 `curves.shared_key`（整个分面 panel 一份图例）、`curves.value_block`（格内同色数值）。导出新增两道闸门：`qa.facet_balance`（分面行左右留白差 > 10% panel 宽，或独占一段的 panel 偏向一侧）、`qa.repeated_legend`（多格重复同一份图例）。`roc_grid.py` 配方改成一行 + 共享图例。

## 0.6.0 (2026-10-08)

主图性能曲线与多病例影像矩阵：

- `medfig-plan`：新增两条硬规则。S7：主图报告判别性能且有逐样本分数时，必须至少有一个曲线 panel（ROC；类别不平衡时加 PR），图例写 AUC；没有逐样本分数时在规格里写 `curve_exempt` 和理由。S6：展示病例的影像 panel 按类别 / 队列分组并排，每组一行代表图 + 叠加、一个每组 ≥ 12 例的共享色阶热图矩阵、一行局部放大；病例按组内对 / 错分层、固定 seed 随机抽取，必须含错例，不按置信度或外观挑选（`case_selection` 字段，单例示意图写 `exempt:` 理由）。`spec_check.py` 检查这两条。
- `medfig-render`：新配方 `case_matrix.py`（分组分层病例矩阵）；新函数 `stats.stratified_cases`（分层随机选例，返回写进 provenance 的 `case_selection` 记录；某层不够数直接报错）、`imaging.crop_window`（以热图质心为中心的确定性裁剪窗）、`imaging.case_tiles`（同宽高比小图精确排布、共用色阶、错例色框，不留 letterbox）；`Reader.external` 支持 `.npz`。
- `medfig-outline`：图的 `source.json` 里有 `case_selection` 时，`outline_check.py` 要求 Methods 写出选例规则与 seed；写法说明补充曲线 panel 与病例矩阵的结果句要点。

## 0.5.1 (2026-10-06)

`medfig-illustrator` 代码审查后的修复：

- 质量门禁不再依赖作者本机文件：`skill_validation` 原本调用 `~/.codex/skills/.system/skill-creator/scripts/quick_validate.py`，别的机器上这一步必然失败。改为技能自带的 `scripts/validate_skill.py`（只用标准库），并且多检查一项：frontmatter 的 `name` 必须等于目录名。
- `svg_live_text.py fix` 修正属性写法：`font-family="'ArialMT'"` 原本会变成 `'ArialMT', ''Arial MT'', sans-serif`（引号被当成字体名的一部分，回退字体名也错了）。现在先去掉引号再解析，并整体替换已有的 `font-weight` / `font-style` 属性，避免出现重复属性（那是无效 XML）。`style=` 写法的结果不变：对已交付的 SVG 重跑一遍，逐字节相同。
- Python 解析：`CELL_LCT_PYTHON` 原本只要装了 `py` 启动器就会被忽略，与文档写的顺序不符。现在显式设置的值优先；它不存在或缺少 Pillow / fontTools 时直接报 `PYTHON_OVERRIDE_UNUSABLE`，不再静默换用别的解释器。去掉了写死的 `D:\anaconda\python.exe` 候选路径；README 补充了设置方法。
- `illustrator_com.ps1`：去掉"for this machine; untested upstream"的注释，写明最低支持版本是 CC 2019（23.x），并说明在线质量门禁是在 23.0.2 上验证的。
- 新增在线测试 `tests/test_artboard_resize.ps1`，并加入 `run_quality_gates.ps1 -IncludeIllustrator`。它只在自己新建的临时文档里操作，覆盖四种情况：放大时左上角不动、拒绝缩小、拒绝非法尺寸、本任务根组已存在时拒绝调整。
- `test_canvas_and_text.py` 从 13 个测试增加到 19 个：覆盖属性写法的三种情况，以及 `validate_skill` 的接受和拒绝路径。

## 0.5.0 (2026-10-06)

- 新技能 `medfig-illustrator`：把已有的参考图 1:1 复刻成可编辑矢量，并在用户**已经打开**的 Illustrator 文档里原生绘制——不新建、不关窗、不动文档里原有对象。技能只改名字，内容与此前的 `cell-lct` 一致；脚本文件名（`run_cell_lct.ps1` 等）和 `CELL_LCT_*` 标识符保持不变，播放代码零改动。
  - 全本地重建：先把参考图拆成 scene / text 清单，再用真实 SVG 图元加可编辑 `<text>` 拼出整张图，不用图像描摹、不嵌参考位图。
  - 画之前跑 `layout_guard.py`：文字重叠、容器溢出、内边距不足全部拦住并给出带 `action` / `before` / `after` 的修复记录。
  - 画完跑原生复核：按 Illustrator 真实 `visibleBounds` 再查一遍文字与文字、连接线、箭头、图标、边框的碰撞；字体族和字重按语义解析，不接受 Black / Narrow 之类静默替换。
  - 交付三件套 AI / SVG / PNG 出自同一个单画板文档，`verify_delivery_bundle.ps1` 核对画板数、画布尺寸、活字数量与内容、栅格残留、空白 PNG、SVG 重渲染差异。
  - 文字永远是字体，不是锚点对象：SVG 导出关闭字体子集化，`svg_live_text.py` 再补 CSS 字体回退并审计，出现 `<font>/<glyph>` 轮廓即阻止交付。
  - 画布自动放大：摆进画板后最小文字会低于 8 pt 时，先把画板原地放大（只放大不缩小，且只在本任务还没画东西时改），再开始画；想保留原画布用 `-NoArtboardResize`，此时字号检查会如实报失败。
  - 用户明确要求时可以把原始影像作为资产嵌入（`-AllowRaster`，只接受本地 PNG/JPG/TIF，拒绝 data URI 和 URL）；参考图本身永远不嵌入。
- `medfig-suite` 分支 B、决策表、下游输入清单和 `references/routing.md` 增加 `medfig-illustrator` 路由；`medfig-plan`、`medfig-render` 各加一条边界说明；`install.py` 一起安装。

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
