# figkit API 参考

由 `medfig-render/lib/figkit/` 源码逐项整理。约定：panel 函数都是 `f(ax, data, ...) -> ax`，画进已有 axes，计算结果挂在 `ax._anchor_<name>` 上供测试与 provenance 使用。`cfg=None` 时使用当前 active config（`config.load` 会自动设为 active）。

导入方式：把 `~/.claude/skills/medfig-render/lib` 放进 `sys.path`，然后 `from figkit import config, export, layout, panel, qa, style`、`from figkit.io import Reader`、`from figkit.provenance import Provenance`、`from figkit.panels import confusion, intervals, dist, curves, heat, imaging`。

## config

| 名称 | 签名 | 用途 |
|---|---|---|
| `DEFAULT_SCIPILOT` | 常量 `"~/.claude/skills/scipilot-medimg-figure-skill/scripts"` | scipilot 脚本目录默认值 |
| `Config` | dataclass：`source, project_root, data_root, out_dir, external_dirs, journal, theme, palettes, scipilot_scripts, banned_extra, banned_allow, forbidden_patterns, caveat_allow, palette_min_delta_e` | 解析后的项目配置 |
| `Config.ensure_scipilot` | `()` -> `Path` | 把 scipilot scripts 加入 `sys.path`；缺 `setup_style.py` 时抛 `FileNotFoundError` 并说明如何安装 |
| `load` | `(path)` -> `Config` | 读 `figkit.toml`（缺 `data_root` 抛 `ValueError`；`[qa]` 只接受 `banned_extra` / `banned_allow` 字符串列表，`banned_allow` 只能列默认词，否则 `ValueError`），并设为 active |
| `use` | `(cfg)` -> `cfg` | 设置或（`None`）清除 active config |
| `active` | `()` -> `Config` | 返回 active config；没有时抛 `RuntimeError` |
| `resolve_cfg` | `(cfg=None)` -> `Config` | `cfg` 或 active config |

Python ≥ 3.11 用 `tomllib`，否则需要 `tomli`。

## io

| 名称 | 签名 | 用途 |
|---|---|---|
| `sha256` | `(p)` -> `str` | 文件 SHA-256 |
| `Reader` | `(prov, cfg=None)` | 只读加载器；每次读取登记 path、SHA-256、行数到 `prov` |
| `Reader.path` | `(rel)` -> `Path` | 解析到 `data_root` 下；逃逸抛 `ValueError`（不读任何内容） |
| `Reader.csv` | `(rel, **kw)` -> `DataFrame` | `pd.read_csv`；rows = 行数 |
| `Reader.parquet` | `(rel, columns=None)` -> `DataFrame` | `pd.read_parquet` |
| `Reader.npz` | `(rel)` -> `NpzFile` | `np.load(allow_pickle=False)`；rows = 数组个数 |
| `Reader.json` | `(rel, rows=None)` -> obj | rows：`None` -> 1，或 `callable(obj) -> int` |
| `Reader.text` | `(rel)` -> `str` | 纯文本；rows = 行数 |
| `Reader.ledger` | `(file, key)` -> `list[dict]` | `data_root/ledger/<file>` 的 JSONL 中 `key` 字段等于 `key` 的记录；跳过空行 |
| `Reader.external` | `(path)` -> obj | 只读白名单 `external_dirs` 内的 `.csv/.json/.md/.txt`；相对路径按第一个白名单目录解析；无白名单或越界抛 `ValueError` |

## provenance

| 名称 | 签名 | 用途 |
|---|---|---|
| `Provenance` | `(name, cfg=None)` | 属性 `name, cfg, inputs, transforms, values`；`Reader(prov, cfg)` 会自动 `bind(cfg)` |
| `bind` | `(cfg)` | 绑定配置，用于把路径写成可移植形式 |
| `add_input` | `(path, sha256, rows)` | 登记输入（Reader 自动调用）；路径记为相对 `project_root` 的 POSIX 路径，外部白名单文件记为 `external:<目录名>/<relpath>`，project 外的 data_root / out_dir 记为 `data:` / `out:` 前缀；其他绝对路径抛 `ValueError`。source.json 中不出现绝对路径或用户目录 |
| `add_transform` | `(text)` | 记录一句可被图注引用的处理说明 |
| `set` | `(key, value)` | 记录图中出现的派生数值（n、AUC、闭合误差、重采样等） |
| `write` | `(out_dir)` -> `Path` | 写 `<out_dir>/<name>.source.json` = {figure, root, created, inputs, transforms, values}（`root` = project_root 目录名）；numpy / Path / set 自动序列化 |

## style

| 名称 | 值 / 签名 | 用途 |
|---|---|---|
| `DOUBLE`, `SINGLE` | `7.09`, `3.46`（英寸） | 双栏 / 单栏宽度 |
| `MIN_FONT_PT`, `INSET_TICK_PT` | `6.0`, `5.0` | 字号下限；5 pt 只允许 inset 刻度 |
| `OKABE_ITO` | 8 色（黑色在最后） | 色盲安全色 |
| `DATA_CYCLE` | `OKABE_ITO` 去掉黑色 | 数据色循环（S3），也是 `axes.prop_cycle` |
| `GREY` | `"#9A9A9A"` | 辅助：参考线、对角线、阴影边 |
| `DARK_GREY` | `"#4D4D4D"` | 辅助：零线、"absent"/"n/a" 文字 |
| `BAND` | `"#EDEDED"` | 辅助：高亮行底带 |
| `NA_FILL` | `"#E6E6E6"` | 辅助：不可估 / absent 格填充（带斜线） |
| `RC` | dict | 6 pt 基础字号、0.6 线宽、去上右脊、fonttype 42、svg 文字、`axes.unicode_minus=True` |
| `mm` | `(x)` -> 英寸 | 毫米换英寸 |
| `apply` | `(cfg=None)` -> `Config` | scipilot `setup_style(journal, lang="en")` 后叠加 `RC`；字体缺 U+2212 抛 `RuntimeError` |
| `palette` | `(kind, cfg=None)` -> dict | `figkit.toml` 的 `[palettes.<kind>]`：name -> {color, marker, label, edge}；未定义抛 `KeyError` |
| `aux` | `(*artists)` -> artist 或 tuple | 标记辅助元素（参考带、`ax.plot` 画的对角线等），S3 色彩审计豁免 |

## qa

| 名称 | 签名 | 用途 |
|---|---|---|
| `BANNED` | list | 默认禁用词表：validated, superior, clinical benefit, UMAP, deployment, diagnostic, clinically proven |
| `banned_list` | `(cfg=None)` -> `list[str]` | 项目禁用词表 = `BANNED` − `[qa] banned_allow` + `[qa] banned_extra`（不分大小写去重）；无 active config 时即 `BANNED` |
| `geometry_audit` | `(fig)` -> `list[str]` | 文字-文字/图例框重叠、文字出画布、图例盖住数据点（marker 线 + scatter/hexbin offset，裁到视图）；只查顶层 axes |
| `banned_in_text` | `(text, cfg=None)` -> `list[str]` | 字符串（图注、表格）中 `banned_list(cfg)` 的词（词边界、不分大小写） |
| `banned_words` | `(fig, cfg=None)` -> `list[str]` | 图内全部 Text 的禁用词（`banned_list(cfg)`） |
| `min_font` | `(fig)` -> `list[str]` | 低于 6 pt 的文字（inset 刻度 5 pt），含图例条目与 inset |
| `true_minus` | `(fig)` -> `list[str]` | 用 ASCII 连字符当负号的已绘文字（如 `-1.5`） |
| `WHITESPACE_MAX` | `0.15` | S1 阈值 |
| `whitespace_audit` | `(fig)` -> `list[str]` | S1：网格单元左右空白合计 > 15%；影像 axes 以实际图像范围计，letterbox 算空白 |
| `text_only_panel` | `(fig)` -> `list[str]` | S2：有文字但没有数据图元（多点线或单个 marker、collection、image、patch；参考线与 `style.aux` 元素不算）的 axes |
| `SAT_MIN` | `0.15` | S3 饱和度阈值 |
| `GREY_CMAPS` | set | 视为灰色的 cmap 名（gray, Greys, binary, bone, ...，含 `_r`） |
| `colour_audit` | `(fig)` -> `list[str]` | S3：只用黑白灰画的数据图元；豁免 `axhline/axvline/axline`、`style.aux` 标记、`_figkit_raw_image` 原始影像、`_figkit_image_axes` 标记的 axes |
| `FIGURE_CAVEATS`, `CROSS_REF`, `figure_text_audit` | dict / regex; `(fig, cfg=None)` -> `list[str]` | 图内文字闸门：图级自由文字（非 panel 序号、非 supxlabel/supylabel）、免责 / 口径措辞（减去 `[qa] caveat_allow`）、交叉引用、`[qa] forbidden_patterns`；查所有绘出的文字（标题、轴名、刻度、注释、图例、inset） |
| `caveat_patterns`, `forbidden_in_text` | `(cfg=None)` -> dict; `(text, cfg=None)` -> `list[str]` | 生效的免责措辞表；纯文本（表格 / markdown）里命中的项目代号正则（表格脚注可写口径，所以表格只查代号） |
| `PALETTE_MIN_DE`, `palette_clash` | `12.0`; `(fig, min_de=None, cfg=None)` -> `list[str]` | 色差闸门：同一 axes 里两个不同的饱和数据色 0 < ΔE00 < 阈值即报错（例如动作色与几乎相同的队列色）；完全相同的颜色不报（同一编码），同一图元内的面 / 边色不互比，辅助元素、灰色、色图不参与。阈值：参数 > `[qa] palette_min_delta_e` > 12 |
| `bar_baseline_audit` | `(fig)` -> list | soft 主题：值轴不含 0 的柱子必须有 `style.axis_break`，否则导出失败；默认主题不检查 |
| `VALUE_LABEL_PT` | `5.0` | `min_font` 下限的唯一例外之二：密集柱上的数值标签（`_figkit_value_label`，由 `compare.metric_bars` 设置）可用 5 pt；其他文字仍是 6 pt |

S2 / S3 检查全部可见 axes：GridSpec、`fig.add_axes`、subfigure 的 axes，以及 inset（`ax.child_axes`，递归）；只跳过 colorbar axes、`secondary_xaxis` / `secondary_yaxis`（父 axes 的第二刻度，其文字按父 axes 的 6 pt 下限检查）和 `style.aux` 标记的 axes（如只放图例的辅助 axes）。`twinx` / `twiny` 兄弟 axes 属于同一 panel：`mark_panel` 时随主 axes 一起独立导出，`panels="none"` 时算一个 panel。S1 不查 inset（`child_axes` 与标了 `ax._figkit_inset = True` 的 add_axes axes）；无 subplotspec 的 axes 以自身位置为单元格，只有 letterbox 会算空白。`min_font` 对这两类 inset 的刻度允许 5 pt。

## export

| 名称 | 签名 | 用途 |
|---|---|---|
| `save` | `(fig, name, prov, kind="main", size=None, cfg=None, dpi=600, panels="marked")` -> dict | 唯一导出出口，见下。`panels="marked"`：有数据 axes 却没有 `mark_panel` 时写文件前抛 `RuntimeError`（S4）；`panels="none"`：只用于单 panel 图（>1 个数据 axes 或已有标记时抛错），组图本身另存为 `<name>_a.{pdf,svg}` |
| `audit_layout`, `export_figure`, `check_figure` | 模块级 `None` | 仅供测试 monkeypatch；非 `None` 时替代 scipilot 工具 |

`save` 顺序：`set_size_inches(size)` → scipilot `audit_layout` + `geometry_audit` + `banned_words` + `min_font` + `true_minus` + `whitespace_audit` + `text_only_panel` + `colour_audit` + `palette_clash` + `figure_text_audit`（结果写入 `prov.values["qa"]`；任一非空或 audit FAIL 抛 `RuntimeError`）→ S4 panel 标记检查 → scipilot `export_figure` 写 `<out_dir>/figures/<kind>/<name>.{pdf,svg,png}` + `_grayscale.png` → `check_figure(min_dpi=300)`（FAIL 删除已写文件并抛错）→ S4 `panel.export_panels`（`panels="none"` 时 `panel.export_whole`）（失败删除组图并重新抛出）→ `prov.write`。返回 `{"files", "qa", "panels", "source"}`。

## panel（S4）

| 名称 | 签名 | 用途 |
|---|---|---|
| `mark_panel` | `(ax, pid, extra_axes=None)` -> ax | 标记 panel；`extra_axes`（colorbar、inset）随它一起导出 |
| `label_panels` | `(fig, axes, labels, **kw)` -> list | 包装 scipilot `layout_tools.add_panel_labels`，并把标签标为 panel 标签；`kw` 可含 `cfg`、`x_offset_pt` 等 |
| `is_panel_label` | `(t)` -> bool | 带标记，或启发式：粗体单字母文字位于 axes 数据区外 |
| `panel_labels` | `(fig)` -> list | 图中全部 panel 标签 |
| `marked_panels` | `(fig)` -> list | 已标记 axes，按 id 排序；id 重复抛 `ValueError` |
| `export_panels` | `(fig, name, out_dir, dpi=600)` -> list | 每个 panel 写 `<out_dir>/panels/<name>/<name>_<id>.{pdf,svg}`，尺寸同组图、隐藏序号；返回 `[{id, pdf, svg, size_in}]`；PDF 缺失抛 `RuntimeError` |

## layout

| 名称 | 签名 | 用途 |
|---|---|---|
| `image_width_ratios` | `(shapes)` -> `list[float]` | 每张图 `(H, W)` 的 `W/H`，作为 GridSpec `width_ratios`，让等高影像填满列（S1）；非正尺寸抛 `ValueError` |
| `small_multiples` | `(fig, n, ncols, cell_in=1.6, legend_rows=0.0, gs=None, sharex=True, sharey=True)` -> (axes, (w, h)) | n 个正方形格的小多图；6 pt 下放 3 条 "model (AUC = mean ± SD)" 图例需 ≥ 1.6 in；返回建议尺寸 |

## stats

| 名称 | 签名 | 用途 |
|---|---|---|
| `odds_ratio` | `(a, b, c, d, z=Z95)` -> dict(or_, lo, hi, corrected) | 2×2 OR + Woolf CI；任一格为 0 时四格加 0.5 并标 `corrected=True`（图注需说明） |
| `risk_group_or` | `(y_true, y_prob, n_groups=10, edges=None)` -> DataFrame | 预测风险分组（分位数或给定切点）相对最低组的 OR；第 1 行为参照（OR 1，无 CI）。来源：Retinal_VascularEvents `OR.py`（MIT） |
| `bland_altman` | `(a, b, k=1.96, ci=0.95, ddof=1)` -> dict | 成对测量一致性：bias、SD、界限 bias ± k·SD、bias 的 t 区间；非有限对剔除并计 `n_dropped`。`ddof=0` 时与 statsmodels `mean_diff_plot` 一致（测试对照） |
| `p_text` | `(p, floor=1e-6)` -> str | 精确 P 文本：`P = 0.012`、`P = 0.24`、`P = 4.2 × 10⁻⁴`、`P < 1 × 10⁻⁶`、`P > 0.99`；不用星号 |
| `structure_strength` | `(x, y, kind="paired"/"mechanism", nbins=10)` -> dict | 画配对 / 机制散点前的预检：paired 要 \|r\| > 0.9；mechanism 要 \|r\| > 0.5 或分箱中位数升幅 > 中位 IQR。不过就换图型。来源 taoge946/academic-figure-patterns（MIT） |
| `binned_median` | `(x, y, nbins=10, min_count=5)` -> dict | x 分位分箱：center / median / q25 / q75 / count |
| `exceedance` | `(values, xs=None, n=200)` -> (xs, frac) | 严格大于 x 的样本比例（尾部曲线） |
| `stratified_cases` | `(df, group, correct, n_correct, n_error, seed, order=None, unique=None, pool="")` -> (selected, record) | 影像病例矩阵选例：每组在对 / 错两层内用 `default_rng(seed)` 无放回抽取，按 `order` 排序后抽（不按置信度或外观）；某层不够数直接报错；`unique`（眼 / 患者 id）重复报错。`record` 写进 `prov.set("case_selection", record)`，规则与 seed 写进图注 |

## style（补充）

| 名称 | 签名 | 用途 |
|---|---|---|
| `log_ticks` | `(ax, axis="x")` | log / symlog 轴的十进制刻度改用真减号（默认 `10^{-k}` 过不了 `qa.true_minus`）；在 `set_xscale` 之后调用 |
| `SOFT_KEYS`, `tint`, `soft_palette`, `SOFT_EMPHASIS`, `soft_controls`, `mark_controls`, `axis_break` | 见 docstring | soft 主题：`SOFT_EMPHASIS` (#3775BA) 给本文方法；`soft_controls(n, kind="pastel" ≤ 6 / "gradient" ≤ 4)` 给对照；`mark_controls(ax, colors)` 声明对照组（soft 下组内色差下限 4，组外仍 12）；`axis_break(ax, "y"/"x")` 截断值轴的双斜线标记；soft 下 S3 只拦饱和度 < 0.05 的近灰色 |
| `ordinal_gradient`, `mark_ordinal` | `(c, n<=5)` -> list；`(ax, levels)` | 有序类别单色相梯度：浅色→深色路径按 CIEDE2000 弧长等分，相邻 ≥ 12，否则 `ValueError`；只用于有序变量 |
| `current_theme` | `()` -> "default" / "soft" | `style.apply` 后的主题；soft 额外设置 `SOFT_RC`（轴名 7 pt、刻度 6.5 pt、线宽 0.8、无框图例、errorbar capsize 2） |
| `delta_e` | `(c1, c2)` -> float | 两个颜色的 CIEDE2000 色差（与 skimage 一致到 0.01）；选新色板时和图内每个颜色比，< 12 读起来就是同一色相，最好 ≥ 20 |

## panels.scatter

| 名称 | 签名 | 用途 |
|---|---|---|
| `bubble_area` | `(n, n_ref, s_ref=40.0, s_min=4.0)` | 面积 ∝ n 的标记大小 |
| `gated_bubble` | `(ax, rows, color=None, n_ref=None, ref=None, hatch="//////", label_col="label", annotate_fail=True)` | `rows` 列 `x, est, lo, hi, n, passes`；过闸门实心 + 实线 CI，未过空心 + 斜线 + 虚线 CI + "(n)"；挂 `_anchor_gate, _anchor_area` |
| `sized` | `(ax, df, x, y, group, size, palette=None, ..., key_sizes=None, symlog=False, linthresh=1e-3, legend_loc=...)` | 每组一色散点，面积 ∝ `size`；`key_sizes` 加灰色辅助尺寸图例；挂 `_anchor_groups` |

## panels.bars

| 名称 | 签名 | 用途 |
|---|---|---|
| `stacked_fraction` | `(ax, rows, parts, palette=None, hatch="////", absent_text="absent")` | 每行 100% 堆叠横条；合计为 0 的行画辅助斜线 + "absent"；挂 `_anchor_frac, _anchor_absent` |

## panels.confusion

| 名称 | 签名 | 用途 |
|---|---|---|
| `matrix` | `(ax, counts, classes, absent_rows=(), annot="pct_n", cbar=False, fontsize=6, tick_labels=None, count_fmt="{:d}", cmap="Blues")` | 行归一化混淆矩阵；`counts` 列 `truth, prediction, count`；`absent_rows` 加上总数为 0 的行画灰色斜线 + "absent"；`annot` 为 `"pct_n"`/`"pct"`/`None`。挂 `_anchor_matrix, _anchor_absent, _anchor_counts, _anchor_mappable` |
| `colourbar` | `(ax, cax, label="Row proportion", ticks=(0, 0.5, 1.0), fontsize=6)` | 行比例 colorbar；`cax` 给定时多个矩阵共用一条 |

## panels.intervals

| 名称 | 签名 | 用途 |
|---|---|---|
| `forest` | `(ax, rows, ref, band_rows=None, color=None)` | 森林图；`rows` 列 `label, est, lo, hi`，可选 `color, marker`；`ref` 虚线参考；挂 `_anchor_y` |
| `dumbbell` | `(ax, rows, a_kw=None, b_kw=None, segment_color=None)` | 哑铃图；`rows` 列 `label, a, b`；挂 `_anchor_delta` |
| `estimation` | `(ax_left, ax_right, paired, deltas, a_label="A", b_label="B", color=None, *, extra_right=(), ticks=True)` -> (ax_left, ax_right) | 配对斜线 + 差值估计图（Gardner–Altman 式）；`deltas` 列 `label, est, lo, hi`，可选 `x, kw`；`extra_right` 用于断轴 |
| `or_forest` | `(ax, rows, color=None, ref_label=True)` | OR 森林图，对数 x 轴，OR = 1 辅助虚线；`rows` 列 `label, or_, lo, hi`（可直接用 `stats.risk_group_or` 输出），CI 为 NaN 的行是参照组；挂 `_anchor_or` |
| `slope` | `(ax, runs, x, y, group, run, order, colors=None, run_alpha=0.5)` | 斜率图：细线 = 单次重复（组色、低 alpha），粗线 + 标记 = 均值；挂 `_anchor_slope_mean` |
| `scorecard` | `(ax, rows, statuses, ref=0.0, legend_loc="lower right")` | 假设记分卡：`rows` 列 `label, est, lo, hi, status`，颜色 + 标记来自 status 色板，图例只列出现的状态；未知状态抛 `ValueError`；挂 `_anchor_status` |

## panels.dist

| 名称 | 签名 | 用途 |
|---|---|---|
| `violin_strip` | `(ax, df, x, y, hue, order, hue_order, log=False, palette=None, violin_alpha=0.35, point_alpha=0.5)` | 小提琴（cut=0）+ 栅格化原始点 |
| `box_swarm` | `(ax, df, x, y, order, color=None, point_color=None, point_df=None, hue=None, hue_styles=None, seed=0)` | 箱线（无离群点）+ 固定种子抖动点；挂 `_anchor_medians` |
| `ecdf` | `(ax, values, **kw)` | 经验 CDF 阶梯线；挂 `_anchor_ecdf` |
| `hdr_contour` | `(ax, xy, color=None, levels=(0.5, 0.9), grid=120, pad_sd=3.0, linewidth=0.8)` | KDE 最高密度区轮廓；阈值 = 样本密度分位数；网格外扩 ≥ 3 核 SD（否则 `ValueError`）；挂 `_anchor_levels, _anchor_grid` |

## panels.curves

| 名称 | 签名 | 用途 |
|---|---|---|
| `LINESTYLES`, `MARKERS` | list | 冗余编码用的线型 / 标记 |
| `step_ladder` | `(ax, df, stages, group="dataset", palette=None, stage="stage", value="value", probe="probe")` | 有序阶段折线，每个 `group` 一条；颜色取 `palette` 或 toml 的 `cohort` 配色，缺失用 `DATA_CYCLE`；`probe` 列为 True 的点画空心 |
| `capture` | `(ax, df, colors=None, x="budget", y="capture", group="signal", xlabel="Review budget", ylabel="Error capture", color_key=None, style_key=None)` | 每个 `group` 一条彩色线；`group` 可为列表；`color_key` / `style_key` 指定颜色和线型各按哪个键（如颜色 = 信号、线型 = 队列） |
| `calibration_bins` / `calibration` | `(y_true, y_prob, n_bins=10, strategy="uniform")` / `(ax, y_true, y_prob, label=None, color=None, marker="o", n_bins=10, strategy="uniform")` | 校准曲线；空箱不画；图例带 Brier；辅助对角线；挂 `_anchor_calibration`。来源：Retinal_VascularEvents `Calibration plot.py`（MIT） |
| `net_benefit` / `decision` | `(y_true, y_prob, thresholds)` / `(ax, y_true, y_prob, label=None, color=None, thresholds=DCA_THRESHOLDS, treat_all=True, treat_all_color=None, ylim=None, linestyle="-")` | 决策曲线；treat none = 辅助零线；`treat_all_color="aux"` 画一条灰色辅助线；低于 y 下限的起点记入 `_anchor_dca[label]["clipped_from"]`。来源：Retinal_VascularEvents `Decision curve.py`（MIT） |
| `pr_points` / `pr_mean_sd` | `(y_true, y_score)` -> (recall, precision, AP) / `(ax, runs, label=None, color=None, n_grid=100, band_alpha=0.2, prevalence=True)` | PR 均值 ± SD（插值精度包络），图例 "AP = mean ± SD"，患病率辅助点线；AP 与 sklearn 一致；挂 `_anchor_pr` |
| `risk_coverage_points` / `risk_coverage` | `(y_correct, confidence)` -> (coverage, risk, AURC) / `(ax, y_correct, confidence, label=None, color=None, linestyle="-")` | 风险–覆盖曲线，图例带 AURC；挂 `_anchor_rc` |
| `roc_inset` | `(ax, curves_, bounds=INSET_BOUNDS, tick_pt=None)` -> inset axes | 宿主 panel 内的子 axes ROC 小插图（随宿主一起导出），正方形、辅助对角线、5 pt 刻度；`curves_` 为 `[dict(fpr, tpr, color, linestyle, label)]`，单条曲线无 SD 带 |
| `intervention` | `(ax, df, colors=None, x="k", y="preserved", action="action", order="order", xlabel="k", ylabel="Prediction preserved")` | 每个 (action, order) 一条：颜色按 action，线型 + 标记按 order；图例 "action / order" |
| `roc_points` | `(y_true, y_score)` -> (fpr, tpr) | 二分类 ROC 点，同分作一个阈值；输入非法抛 `ValueError` |
| `roc_mean_sd` | `(ax, runs, label=None, color=None, n_grid=100, kind="scores", band_alpha=0.2)` | S5 平均 ROC ± SD，见下 |

`roc_mean_sd`：`kind="scores"` 时 `runs` 为 `[(y_true, y_score), ...]`；`kind="curve"` 时为 `[(fpr, tpr), ...]` 且逐条校验（单调、[0,1] 内、fpr 0→1、tpr 止于 1），不自动识别。每次重复在 `linspace(0, 1, n_grid)` 上 `np.interp`；图例 "label (AUC = mean ± SD)"（样本 SD，ddof=1），右下角；正方形坐标、灰色虚线对角参考、x 轴 "1 − specificity"。只有 1 次重复时不画 SD 带、图例只写 AUC，需在图注说明。同一 axes 多次调用即多模型，颜色按 `DATA_CYCLE` 轮换。挂 `_anchor_mean_auc, _anchor_sd_auc`（单次为 NaN）、`_anchor_fpr_grid, _anchor_mean_tpr, _anchor_sd_tpr, _anchor_auc`（{label: (mean, sd)}）。样式来源：MenglinLu/Retinal_VascularEvents `visualization/ROC curve.py`（MIT）。

## panels.heat

| 名称 | 签名 | 用途 |
|---|---|---|
| `CLOSURE_TOL` | `1e-5` | waterfall 闭合容差 |
| `annotated` | `(ax, M, cmap, center=None, fmt="{:.2f}", hatch_mask=None, cbar_label="", cbar=False, fontsize=6, vmin=None, vmax=None, gridlines=False)`（`gridlines=True` 白色格线） | 标注热图；`center` -> 对称 TwoSlopeNorm；`hatch_mask` 格画斜线 "n/a"；灰色 cmap 抛 `ValueError`（S3）；负值用真减号；挂 `_anchor_matrix, _anchor_mappable, _anchor_hatch` |
| `waterfall` | `(ax, start, contribs, end, start_label="Start", end_label="Total", orientation="horizontal", tol=CLOSURE_TOL)` | 贡献瀑布图；任一输入非有限值或 `|start + sum - end| > tol` 抛 `ValueError`，不做降级绘制；挂 `_anchor_closure_error, _anchor_cumulative` |

## panels.compare

风格参考 senlanke/figures4papers（无许可证，只借思路，代码重写）。

| 名称 | 签名 | 用途 |
|---|---|---|
| `metric_bars` | `(ax, df, metric, methods, method_col="method", value_col="value", emphasis=None, controls="pastel", palette=None, ylabel=None, higher_is_better=True, ylim=None, truncate="auto", values=True, decimals=3, show_runs=False)` | 单指标平涂柱：emphasis 用 `SOFT_EMPHASIS`，其余 `soft_controls`；须线 n ≤ 5 为 min–max，否则 ± SD（`_anchor_whisker`，写图注）；最低均值 > 顶端 40% 时截断值轴并画断轴标记；柱顶一律标数值（≤ 5 根柱 6 pt；更多 5 pt，太挤自动竖排并重算头部空间）；挂 `_anchor_bars` / `_anchor_ylim` / `_anchor_truncated` / `_anchor_colours` |
| `legend_panel`, `legend_inside` | `(ax, methods, labels=None, emphasis=None, controls="pastel", palette=None, ...)` | 右侧带框图例盒（辅助 axes，样式 1）；或 axes 内上方两列图例（样式 2，用 `ylim` 留出头部空间） |
| `ordinal_bars` | `(ax, rows, color=None, label_col="label", value_col="value", lo_col=None, hi_col=None, xlabel="", xlim=None, values=True, decimals=3)` | 有序平涂横柱（单色相梯度 2–5 级，端点 `ORDINAL_SOFT`，默认 #0072B2 可到 4 级）；深灰 CI 须线；柱端标数值；差异小时截断并画断轴标记；挂 `_anchor_ordinal` / `_anchor_xlim` |
| `area_trend` | `(ax, x, series, colors=None, cumulative=False, hatches=None, events=None)` | 面积趋势：浅色填充 + 深一档同色相线，hatch 用深一档色；图例为填充 + 线组合；`events=[(x, label)]` 画箭头标注；挂 `_anchor_area` |
| `p_bracket` | `(ax, x1, x2, y, p, h=None, text=None, fontsize=6)` | 显著性括号写精确 P（`stats.p_text`），线为辅助元素 |

## panels.evidence

逐样本证据图，思路参考 taoge946/academic-figure-patterns（MIT），按 figkit 重写。

| 名称 | 签名 | 用途 |
|---|---|---|
| `exceedance` | `(ax, values, color=None, label=None, xs=None, floor=1e-4, logy=True, **kw)` | 超越曲线（log y，真减号刻度）；挂 `_anchor_exceedance` |
| `paired_cloud` | `(ax, x, y, color=None, s=4.0, alpha=0.35, identity=True, lim=None, rasterized=True)` | 配对散点 + 辅助 y = x 线，等比例坐标；挂 `_anchor_paired`（n、below_diagonal） |
| `binned_median` | `(ax, x, y, nbins=10, color=None, band=True, min_count=5, label=None)` | 分箱中位数线 + IQR 浅色带；挂 `_anchor_binned` |
| `bland_altman` | `(ax, a, b, color=None, s=6.0, alpha=0.5, k=1.96, units="", labels=True, rasterized=True)` | Bland–Altman：bias 实线、界限虚线（axhline 辅助）并在右侧标数值；挂 `_anchor_ba` |

## journals

`figkit.journals`：期刊规格表（格式参考 JRBCH/spiffyplots `journals.py`，MIT）。每条有 `status`（VERIFIED = 本日从出版商页面核对；ESTIMATED = 官网不可达，来自注明的二手来源，投稿前要确认）、`source`、`checked`。收录：`nature`、`npj`、`science`、`cell`、`elsevier`、`media`（Medical Image Analysis）、`ieee`（含 TMI，别名 `tmi`）。`get(name).figsize("single"/"double", height_mm=None)` 返回英寸（按 `max_height_mm` 截断）；`figkit_font` 不低于 6 pt（house 下限，即使期刊允许 5 pt）。IEEE 目标字号约 9–10 pt，比其他期刊大。

## panels.imaging

| 名称 | 签名 | 用途 |
|---|---|---|
| `BOUNDARY_COLORS`, `BAND_ALPHA`, `MAP_ALPHA`, `MAP_THRESHOLD` | 常量 | 边界色、掩膜 alpha 0.28、图 alpha 0.55、阈值 0.15 |
| `upsample` | `(a, shape, order=1)` | 2-D 数组精确缩放到 `shape`；只用于概率 / 激活图，绝不用于掩膜 |
| `raw_image` | `(ax, raw, cmap="gray")` -> AxesImage | 等比例、居中、无刻度画原图，并标 `_figkit_raw_image`（S3 豁免） |
| `bscan_with_boundaries` | `(ax, raw, boundaries, band_masks=None, colors=None, band_cmap="viridis")` | 原图 + 边界线（`(K, M)`，按图高归一化）+ 可选带状掩膜 `(B, H, W)`（bool 或 [0, 1] 内的有限值）；掩膜形状不等于原图、或含非有限值 / 越界值抛 `ValueError`；挂 `_anchor_boundaries_px, _anchor_bands` |
| `concept_map` | `(ax, raw, spatial, vmin, vmax, cmap="magma", threshold=MAP_THRESHOLD, alpha=MAP_ALPHA)` | 共享 `[vmin, vmax]` 的激活图（必填）；归一化值 < threshold 或原值 ≤ 0 透明；挂 `_anchor_mappable, _anchor_upsampled, _anchor_alpha, _anchor_threshold, _anchor_resampled` |
| `prob_overlay` | `(ax, raw, prob, vmin, vmax, cmap="viridis", resample="bilinear", alpha=MAP_ALPHA)` | 低分辨率概率图叠加（不是掩膜）；`resample` 为 `"bilinear"`/`"nearest"`；挂 `_anchor_resampled = (src_shape, dst_shape, method)`，必须写进图注 |
| `crop_window` | `(shape, aspect, heat=None, frac=1.0)` -> (y0, y1, x0, x1) | 确定性裁剪窗：给定宽高比的最大窗 × `frac`（< 1 为放大），中心取热图正值质心（无热图取图像中心），越界时平移回图内；窗口写进 provenance |
| `case_tiles` | `(fig, rect, cases, vmin, vmax, ncols, tile_aspect=1.0, gap=0.04, cmap="magma", error_color="#D55E00", threshold=MAP_THRESHOLD, alpha=MAP_ALPHA, overlay=True, crop_frac=1.0)` -> [ax] | 一组病例的热图矩阵：在 `rect`（figure 坐标）里按 `ncols` 精确摆放等宽小图（`add_axes`，用 `layout="none"` 的 figure），每格是 `crop_window` 裁出的同宽高比切片，不留 letterbox；全部共用 `[vmin, vmax]`；`error=True` 的病例画错例色框；`overlay=False` 只画原图切片（局部放大行）。每格挂 `_anchor_case`（id、error、crop、resampled）。整组标成一个 panel：`mark_panel(axes[0], "b", extra_axes=axes[1:])` |


## review

| 名称 | 签名 | 用途 |
|---|---|---|
| `contact_sheet` | `(out_pdf, pages)` -> Path | 审阅 PDF：每页 (标题, [png, ...])，标题写在图上方页眉带并用分隔线隔开，图片区域不允许任何文字（`check_image_axes_clean`）；可放修改前 / 后两张 |