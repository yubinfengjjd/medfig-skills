---
name: medfig-render
description: Use when drawing one specific figure for a medical research paper that mixes images and statistics, such as an OCT, CT, MRI, fundus or pathology image with masks, contours, probability or concept maps next to ROC curves, confusion matrices, forest plots, distributions or waterfalls; when writing or fixing a figkit figure script, exporting a journal-ready figure with QA, standalone per-panel PDF and SVG, source.json provenance and a caption draft; when a figure fails export QA for overlap, whitespace, text-only panels, grey data, fonts or minus signs; or when the user says 按规格画这张图、影像加统计混排、单张医学论文图、画 ROC 均值加标准差、导出投稿级 figure、图注草稿.
---

# medfig-render：按规格画一张医学论文图

一张图 = 一个 figure script（`build() -> (fig, prov)`）+ 一次 `export.save`。库在本技能自带的 `lib/figkit/`，全部路径从项目的 `figkit.toml` 读取。图内文字默认英文。

## 1. 什么时候用哪个技能

| 情况 | 用 |
|---|---|
| 已有该图的规格（每个 panel 的结论、数据文件与列、图型），画这一张 | **medfig-render** |
| 还没定图、panel、图型、主附图划分 | medfig-plan（先出规格再回来） |
| 规格已定，要批量出多张 / 整套、并行执行、台账与终审 | medfig-orchestrate（逐图任务内部用本技能） |
| 只要一张纯影像网格（影像 + 掩膜 / 热图 / 放大框，没有统计 panel） | scipilot-medimg-figure-skill（见 §9） |
| 非医学数据图、示意图、流程图、架构图 | 不用本技能 |

没有规格时，不要边画边定：先问清每个 panel 的一句话结论和数据来源，或转 medfig-plan。

## 2. 项目设置

1. 项目根放一份 `figkit.toml`，从 `templates/figkit.toml` 复制后修改。关键键：
   - `data_root`（必填，只读结果根目录；`Reader` 拒绝任何越界路径）
   - `out_dir`（默认 `out`）、`external_dirs`（第二权威目录白名单，默认空）
   - `journal`（默认 `nature`）、`scipilot_scripts`（scipilot 脚本目录）
   - `[palettes.cohort.*]`、`[palettes.class.*]`：每种语义一套颜色，不跨语义复用
   相对路径：只有 `project_root` 按 toml 所在目录解析；其余路径（`data_root`、`out_dir`、`external_dirs`、`scipilot_scripts`）按 `project_root` 解析。
2. 依赖：matplotlib ≥ 3.7、numpy、pandas、scipy、seaborn；Python ≥ 3.11（或装 `tomli`）；已安装 scipilot-medimg-figure-skill（缺失时 `style.apply` 给出明确报错）。
3. 脚本放 `<project>/scripts/figN.py`，从 `templates/figure_script.py` 复制。模板通过 `FIGKIT_LIB`（默认 `~/.claude/skills/medfig-render/lib`）和 `FIGKIT_TOML` 环境变量定位库与配置。装在 Codex（`~/.codex/skills/`）时必须设置 `FIGKIT_LIB=~/.codex/skills/medfig-render/lib`，否则脚本会去默认的 `~/.claude` 路径找库。

完整 API 见 `references/figkit_api.md`。

**先查配方库**：`examples/gallery/INDEX.md` 按类别列出可直接运行的 panel 配方（ROC 均值 ± SD、ROC 小多图、PR、校准、DCA、风险–覆盖、错误捕获 + ROC 插图、OR 森林、记分卡、斜率图、闸门气泡、组级散点、堆叠比例、多指标对比柱、有序消融柱、面积趋势、超越曲线、配对散点、Bland–Altman），每行写明输入数据形状和"不要用"的情况。先按数据形状和"不要用"排除，再选配方；能对上时照抄配方的调用和色板，不要重写绘图代码。

**主题**：`figkit.toml` 写 `theme = "soft"` 换成 figures4papers 风格（参考 senlanke/figures4papers，代码重写）：本文方法用唯一饱和色 `style.SOFT_EMPHASIS`，对照方法用浅色（`style.soft_controls`，pastel 或同色相渐变，用 `style.mark_controls` 声明成一组）；柱子平涂、无描边无纹理、柱顶标数值、细深灰误差棒；值轴可以截断，但必须画 `style.axis_break`（`qa.bar_baseline_audit` 会拦）；3 个 seed 不叠点，须线含义写图注；字号 7 / 6.5 pt。默认主题不变，柱子从 0 起。有序类别才用单色相梯度（`style.ordinal_gradient`）；期刊尺寸从 `figkit.journals` 取，ESTIMATED 条目投稿前确认。审阅 PDF 用 `figkit.review.contact_sheet`（文件名在页眉带，不压在图上）。

**新增配方**：在配方文件里写 `RECIPE = dict(chart, category, use, data, avoid, functions, tags, source)`，运行 `python examples/gallery/_meta.py` 重新生成 INDEX（不要手改 INDEX，测试会拦）；新库函数要配测试，数字和参考实现对过，开源代码保留来源与许可证注释。

## 3. 脚本骨架

```python
def build():
    cfg = config.load(TOML)
    style.apply(cfg)                       # 6 pt 基础字号、真减号、Okabe-Ito 数据色
    prov = Provenance(NAME)
    rd = Reader(prov, cfg)                 # 每次读取登记 SHA-256 + 行数
    img = rd.npz("images/case01.npz")["image"]
    df = rd.csv("scores/roc_runs.csv")

    ratios = layout.image_width_ratios([img.shape[:2]]) + [1.0, 1.0]
    fig = plt.figure(figsize=SIZE, layout="constrained")
    gs = fig.add_gridspec(1, 3, width_ratios=ratios)
    ax_a, ax_b, ax_c = (fig.add_subplot(gs[0, i]) for i in range(3))

    imaging.prob_overlay(ax_a, img, prob, vmin=0.0, vmax=1.0)
    curves.roc_mean_sd(ax_b, runs, label="Model A", kind="scores")
    confusion.matrix(ax_c, counts, CLASSES)
    prov.set("b_auc_mean", ax_b._anchor_mean_auc)   # 图中每个数字都进 prov

    for ax, pid in zip((ax_a, ax_b, ax_c), "abc"):
        panel.mark_panel(ax, pid)          # colorbar 用 extra_axes=[cb.ax] 带上
    fig.set_size_inches(*SIZE); fig.canvas.draw()
    panel.label_panels(fig, [ax_a, ax_b, ax_c], ["a", "b", "c"], cfg=cfg)
    return fig, prov

if __name__ == "__main__":
    fig, prov = build()
    export.save(fig, NAME, prov, kind="main", size=SIZE)   # 唯一出口，不包 try/except
```

要点：
- `build()` 不写文件；测试 import 脚本调用 `build()`，断言 `prov.values`（n、AUC、absent 集合等）与独立读取的源数据一致，并在最终尺寸下断言 `qa.geometry_audit(fig) == []`。
- 宽度用 `style.DOUBLE`（7.09 in）或 `style.SINGLE`（3.46 in）；其他宽度要在交付说明中列为偏离。
- 手工 GridSpec 且不用 constrained layout 时，用 `fig.set_layout_engine("none")` 或 PlaceHolder 引擎；关掉的 axes 同时清掉刻度。
- 共享 colorbar 放顶层 axes（inset 子 axes 不进 geometry audit）。
- panel 函数都是 `f(ax, data, ...) -> ax`，计算结果挂在 `ax._anchor_*`，从这里取数写入 prov。

## 4. 唯一导出出口：`export.save`

`export.save(fig, name, prov, kind="main", size=SIZE)` 按顺序（有数据 axes 却没有任何 `mark_panel` 时在写文件前抛错；只有一个 panel、组图本身就是该 panel 时显式传 `panels="none"`，组图另存为 `<name>_a`）：

1. `fig.set_size_inches(size)`：先定最终尺寸，QA 看的就是导出的几何。
2. QA：任一不通过抛 `RuntimeError`，错误信息逐项列出问题，此时不写任何文件（没有 `source.json`）；只有导出成功时，QA 结果才随 `source.json` 记录在 `values.qa`。检查项：
   - scipilot `audit_layout`（FAIL 级）
   - `qa.geometry_audit`：文字重叠、出画布、图例框盖住数据点（含 scatter / hexbin）
   - `qa.banned_words`：项目禁用词表（默认 `qa.BANNED`，按 `figkit.toml` 的 `[qa]` 增减）
   - `qa.min_font`：< 6 pt（inset 刻度允许 5 pt）
   - `qa.true_minus`：ASCII 连字符当负号
   - `qa.whitespace_audit`（S1）：任一 panel 内容左右空白合计 > 单元宽度 15%
   - `qa.text_only_panel`（S2）：只有文字、没有数据图元的 axes（参考线、`style.aux` 元素不算数据）
   - `qa.colour_audit`（S3）：数据图元只用黑白灰（饱和度 ≤ 0.15），或数据热图用灰色 cmap
   - `qa.figure_text_audit`：图内文字只放结果与读图编码。报错项：图级自由文字（`fig.text` 注释行、`suptitle`；panel 序号和 `supxlabel/supylabel` 除外）、免责 / 口径措辞（`qa.FIGURE_CAVEATS`：illustrative、not a clinical、not used for、by construction、descriptive、not a CI、retrospective、exploratory ...，项目可用 `[qa] caveat_allow` 放行）、交叉引用（Table 6、Fig. 3b、Supplementary Fig. S2）、项目代号（`[qa] forbidden_patterns` 正则，例如 `\bE[12]\b`）、开发史（`qa.DEV_HISTORY`：pre-registered、hypothesis status、closeout、closure、wave-N、earlier / historical version、repair、post-outcome、reconciliation；只有真实方法名才用 `[qa] caveat_allow` 放行）。修法是把这句话挪进图注、代号换描述名、丢弃版本直接删掉，不是放行
   - `qa.palette_clash`（S3）：同一 axes 里两种不同数据色几乎同色（ΔE00 < 12，可在 `[qa] palette_min_delta_e` 调）。修法是换色板颜色（用 `style.delta_e` 和图内每个颜色比），不是调低阈值
3. scipilot `export_figure`：`<out_dir>/figures/<kind>/<name>.{pdf,svg,png}` + `_grayscale.png`（600 dpi），再逐个 `check_figure`，FAIL 时删除已写文件并抛错。
4. S4：每个 `mark_panel` 过的 panel 另存 `<out_dir>/panels/<name>/<name>_<id>.{pdf,svg}`，fonttype 42、文字可选、尺寸与组图中一致、隐藏 a/b/c 序号；缺失即 FAIL 并删除组图。
5. 写 `<name>.source.json`（inputs、transforms、values、qa、panels）。

QA 失败时修图，不修检查：
- S1 超标 → 用 `layout.image_width_ratios` 分配列宽，图例移到图内角或上方，不留侧栏。
- S2 → 删掉纯文字 panel，信息不迁到图注。
- S3 → 数据改用 `style.DATA_CYCLE` / 配色表；区分方法、顺序用颜色 + 线型 / 标记冗余编码，不用黑与灰区分。灰色只给坐标轴、网格、参考线、对角线、底带；用 `ax.plot` 画的参考线用 `style.aux(...)` 标记。
- 审计误报 → 修审计器并加回归测试，不在图上绕开，也不降低阈值。

## 5. 影像红线

详见 `references/imaging_rules.md`。

- 不拉伸：影像 `aspect="equal"`，`imaging.*` 已强制；列宽按宽高比分配。上游已缩放时图注说明显示宽高比不是原始宽高比。
- 掩膜不缩放：`band_masks` 与原图形状不同直接报错。
- 低分辨率模型输出画成概率图：`imaging.prob_overlay(..., resample="bilinear")`，`ax._anchor_resampled` 写进 prov 和图注。
- CAM / 概念图共享色阶：先对所有展示病例算一个 `vmin, vmax`，再逐个 `concept_map`；原值 ≤ 0 透明；原始量级在噪声水平的 CAM 不画。
- 比例尺只画有文档像素间距的轴。
- 预测轮廓标明 "model prediction, not manual annotation"。

## 6. 统计规则

- 不可估 / 缺失类别：斜线阴影 + "absent" / "n/a"，不画 0，不留白。`confusion.matrix` 自动把总数为 0 的行设为 absent；`heat.annotated(hatch_mask=...)`。脚本断言 `ax._anchor_absent` 等于预期集合。
- 结构零（按构造为 0）用不同纹理，图注写 "by construction"，构造从运行记录断言。
- 区间：图注写区间类型（95% CI / ±1 SD）、n（带单位）和重采样方式（例如 cluster bootstrap 次数）。
- 图中和图注中的数字全部由数据计算并写入 `prov.values`；字面值只出现在断言里（`assert absent == EXPECTED_ABSENT`）。标题中的 "(2-class)" 也从数据中的类别集合推出。
- 两种筛选得到不同 n 时，在代码中算出差值并断言等于文档记录的排除数。
- 闭合 / 求和检查先断言全部有限：`heat.waterfall` 遇到非有限值或不闭合直接报错，不做降级绘制。
- x 有序才连线；n 很小时画点不画柱；KDE 轮廓用 `dist.hdr_contour`（小样本只画 50%）。
- 对一组检验的笼统结论按可推翻它的极值门控（"all P > 0.05" 要求 `min(p) > 0.05`）。

## 7. ROC：`curves.roc_mean_sd`（S5）

样式来自 MenglinLu/Retinal_VascularEvents `visualization/ROC curve.py`（MIT）：正方形坐标、灰色虚线对角参考线、各次重复（seed / fold）在共同 FPR 网格上用 `np.interp` 插值后取平均、±SD 阴影带、图例 "label (AUC = mean ± SD)" 在右下角、x 轴 "1 − specificity"、Okabe-Ito 配色。

```python
runs = [(g.y_true.to_numpy(), g.y_score.to_numpy()) for _, g in df.groupby("run")]
curves.roc_mean_sd(ax, runs, label="Model A", kind="scores")      # 原始标签 + 分数
curves.roc_mean_sd(ax, curves_b, label="Model B", kind="curve")   # 已算好的 (fpr, tpr)
```

- `kind` 必须显式指定，不自动识别；`kind="curve"` 会校验单调性与端点。
- 同一 axes 多次调用即多模型对比。
- 只有一次重复：不画 SD 带，图例只写 AUC，图注说明 "single run; no SD band"。
- 图注说明阴影是 "±1 SD across runs, not a confidence interval"，并写每次重复的 n。
- AUC 均值与 SD 从 `ax._anchor_mean_auc` / `_anchor_sd_auc` 写入 prov。

## 8. 图注

详见 `references/caption_rules.md`。草稿由 `caption(prov)` 从 provenance 生成（模板已有示例），写到 `source.json` 旁的 `<name>.caption.md`。

- 研究性质与开发史：图注不逐图写探索性声明，不写开发流程，不出现早期版本（只呈现主线，见 `medfig-plan/references/mainline_rules.md`）；探索性质在稿件 Methods 交代一次。
- 适用限制：共享成分不是独立复现、两类队列不称三分类验证、预测轮廓、CAM 共享色阶、概率图重采样、缺像素间距不画比例尺、单次 ROC。
- 禁用词：默认 validated, superior, clinical benefit, UMAP, deployment, diagnostic, clinically proven。项目只在 `figkit.toml` 里调整：`[qa] banned_extra = [...]` 追加，`[qa] banned_allow = [...]` 放行默认词（如确实使用 UMAP、报告 diagnostic accuracy 的论文）。图、表、图注共用这一张项目表，用 `qa.banned_in_text(text)` 检查，命中即抛错。
- 方法描述（约束、归一化、校准方式）要能追溯到当前运行配置。

## 9. 纯影像网格：调用 scipilot-medimg

图里只有影像（+ 掩膜、轮廓、热图、放大框、箭头、比例尺），没有统计 panel 时，不写 figkit 脚本，直接用 scipilot-medimg-figure-skill：

1. 按 scipilot-medimg 自带的影像规格文档（其 references 目录下的 image_panels 说明）写 JSON 规格（`cells[]`：`image`、`crop`、`overlays`、`zooms`、`arrows`、`scale_bar`、`corner_text`；跨图可比的热图 `normalize: shared`；比例尺需 `pixel_spacing_um`）。
2. 运行 `python <scipilot 目录>/scripts/image_panel.py spec.json`，产出 pdf/svg/png、灰度预览、`*.qa.json`、`*.provenance.json`、`*.caption_methods.md`。
3. 有 `[FAIL]` 先改规格或数据再重渲；读预览图和灰度图复核。

scipilot 目录即 `figkit.toml` 的 `scipilot_scripts` 的上一级。混排图中的影像 panel 仍用 `figkit.panels.imaging`，由 figkit 统一导出。

## 10. 交付前自查

- [ ] 规格中每个 panel 都画了，结论与规格一致；偏离已记录。
- [ ] `export.save` 在最终尺寸下通过，没有 try/except 包裹。
- [ ] `out/panels/<name>/` 中每个 panel 都有 PDF + SVG。
- [ ] `source.json` 的 inputs 都在 `data_root`（或白名单）下；图中每个数字都在 `values` 里。
- [ ] 测试调用 `build()` 并断言关键数字与源数据一致。
- [ ] 读过组图 PNG 和灰度 PNG：影像未变形、图例不压数据、颜色在灰度下仍可区分。
- [ ] 图注草稿含结论、n、区间类型与方法、研究性质声明、适用限制，禁用词检查通过。
