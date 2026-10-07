# Panel gallery 索引

> 本文件由 `_meta.py` 根据各配方的 `RECIPE` 元数据自动生成，不要手改；改元数据后运行
> `python _meta.py`。测试会在本文件过期时失败。

用法：先按"输入数据形状"和"不要用"两列排除，再看"什么时候用"；打开配方脚本看 `draw()`，把调用和
`figkit.toml` 里用到的色板复制进项目。全部配方用合成数据，导出时所有 QA 闸门（含色差闸门）必须为空。

运行：`python medfig-render/examples/gallery/<配方>.py`，输出到 `examples/gallery/out/figures/gallery/`。


## 判别

| 配方 | 图型 | 什么时候用 | 输入数据形状 | 不要用 | 库函数 | 关键词 | 来源 |
|---|---|---|---|---|---|---|---|
| `pr_mean_sd.py` | PR 曲线（多次重复均值 ± SD） | 类别不平衡，需要看阳性类的精度–召回取舍 | 每次重复的逐样本二分类标签 + 分数 | 类别基本平衡（ROC 已足够）；只有 AP 数字 | `curves.pr_mean_sd` | PR, AP, precision, recall, 不平衡 | 项目实战提炼 |
| `roc_mean_sd.py` | ROC（多次重复均值 ± SD） | 比较几个模型的判别能力，每个模型有多个 seed / 折 | 每次重复的逐样本二分类标签 + 分数（或已算好的 fpr/tpr） | 只有一次运行（改单条曲线、图注说明无 SD 带）；只有 AUC 数字没有曲线点 | `curves.roc_mean_sd` | ROC, AUC, seed, 判别, 受试者工作特征 | Retinal_VascularEvents ROC curve.py（MIT） |

## 校准与效用

| 配方 | 图型 | 什么时候用 | 输入数据形状 | 不要用 | 库函数 | 关键词 | 来源 |
|---|---|---|---|---|---|---|---|
| `bland_altman.py` | Bland–Altman 一致性图 | 两种测量（模型预测 vs 实测，或两台设备）在同一批样本上的一致性 | 逐样本成对测量值（同一单位） | 两者单位不同或量纲不可比；想证明相关性（相关高不等于一致，相关用散点） | `evidence.bland_altman` + `stats.bland_altman` | Bland-Altman, agreement, limits of agreement, 一致性 | 经典方法（Bland & Altman 1986），数值与 statsmodels 对照 |
| `calibration.py` | 可靠性图（校准曲线） | 报告预测概率是否与实际事件率一致 | 逐样本二分类标签 + 预测概率（必须是 [0, 1] 概率，不是 logit） | 输出不是概率（先校准或换图）；样本很少（每箱 < ~20 例，改用较少分箱或 quantile） | `curves.calibration` | calibration, Brier, 校准, reliability | Retinal_VascularEvents Calibration plot.py（MIT） |
| `capture_roc_inset.py` | 错误捕获曲线 + ROC 小插图 | 分诊 / 复核预算 panel，另需一个紧凑的判别摘要 | 每个信号 × 队列的 (预算, 捕获比例) 曲线点；插图要逐样本标签 + 分数 | 插图需要 ±SD（插图只画单条曲线）；主图曲线超过 6 条（太挤） | `curves.capture` + `curves.roc_inset` | triage, error capture, inset, 分诊, 插图 | 项目实战提炼 |
| `decision.py` | 决策曲线 DCA | 规格要求描述性的临床效用 panel | 逐样本二分类标签 + 预测概率 | 阈值是在测试集上调的；想据此声称临床获益（禁用词） | `curves.decision` | DCA, net benefit, 决策曲线, 净获益, 临床效用 | Retinal_VascularEvents Decision curve.py（MIT） |
| `risk_coverage.py` | 风险–覆盖曲线 | 模型可以弃权时，展示保留比例与错误率的关系 | 逐样本是否预测正确（0/1）+ 置信度分数 | 没有可用的置信度 / 不确定性分数 | `curves.risk_coverage` | selective prediction, AURC, abstention, 弃权, 覆盖率 | 项目实战提炼 |

## 区间与记分

| 配方 | 图型 | 什么时候用 | 输入数据形状 | 不要用 | 库函数 | 关键词 | 来源 |
|---|---|---|---|---|---|---|---|
| `metric_bars_gradient.py` | 多方法单指标柱（同色相渐变对照 + 内置图例） | 一个指标上比较 3–5 个方法，对照方法同属一类（同一色相深浅），本文方法突出 | 方法 × 重复（seed / 折）的长表 | 对照方法超过 4 个（渐变分不开，改 pastel 浅色）；对照方法之间本身要比较（改 pastel 不同色相）；截断却不画断轴标记（导出闸门会拦） | `compare.metric_bars` + `compare.legend_inside` + `style.soft_controls` + `style.mark_controls` | bar, gradient, soft theme, figures4papers, 柱状图, 渐变 | 风格参考 senlanke/figures4papers 样式 2（无许可证，仅借鉴思路，代码重写） |
| `multi_metric_bars.py` | 多指标对比柱（共享图例 panel） | 几个方法在 2–4 个指标上并排比较，本文方法用唯一饱和色突出，对照方法用浅色，指标间顺序和颜色一致 | 方法 × 指标 × 重复（seed / 折）的长表 | 方法超过 6 个（浅色不够分，改分组或小多图）；只有一个指标（直接点图）；截断 y 轴却不画断轴标记（导出闸门会拦） | `compare.metric_bars` + `compare.legend_panel` + `style.soft_controls` + `style.axis_break` | bar, multi-metric, soft theme, figures4papers, 柱状图, 多指标 | 风格参考 senlanke/figures4papers 样式 1（无许可证，仅借鉴思路，代码重写） |
| `or_forest.py` | 风险分组 OR 森林图 | 展示风险评分的分层能力：各风险组相对最低组的 OR | 逐样本二分类结局 + 预测风险分数 | 事件很少导致多个零格（OR 不稳定，改报事件率） | `stats.risk_group_or` + `intervals.or_forest` | OR, odds ratio, decile, 风险分层, 比值比 | Retinal_VascularEvents OR.py（MIT） |
| `ordinal_ablation.py` | 有序消融柱（单色相深浅梯度） | 组件逐个叠加的消融（基线 → +A → +A+B …），顺序本身有含义 | 汇总行：每个有序水平的估计值（可带 CI） | 水平之间没有顺序（改不同颜色）；超过 5 级（相邻色差不够，改点图或分箱） | `compare.ordinal_bars` + `style.ordinal_gradient` + `style.axis_break` | ablation, ordinal, gradient, soft theme, figures4papers, 消融, 梯度 | 风格参考 senlanke/figures4papers（无许可证，仅借鉴思路，代码重写） |
| `scorecard.py` | 假设记分卡（点 + CI） | 如实报告预注册假设 H1..Hn，包括阴性和不确定结果 | 汇总行：每个假设的估计、CI、状态 | 假设之间单位不同又要共用一个 x 轴（拆 panel 或标准化） | `intervals.scorecard` | hypothesis, pre-registered, scorecard, 预注册, 记分卡 | 项目实战提炼 |
| `slope.py` | 斜率图（重复细线 + 均值粗线） | 少数几个有序条件下比较一个指标，并展示 seed 间离散 | 组 × 重复 × 条件 的长表 | 条件无序（不应连线，改点图）；条件超过 ~6 个 | `intervals.slope` | slope chart, seed, paired, 斜率图, 配对 | 项目实战提炼 |

## 分布与组成

| 配方 | 图型 | 什么时候用 | 输入数据形状 | 不要用 | 库函数 | 关键词 | 来源 |
|---|---|---|---|---|---|---|---|
| `area_trend.py` | 累计面积趋势图 | 两三个类别随时间的累计数量（文献数、入组数、病例数），可标一两个事件 | 时间点 × 类别 的计数表 | 类别超过 3 个（面积互相遮挡，改小多图或折线）；需要比较比例而非数量（改堆叠比例） | `compare.area_trend` | area, trend, cumulative, soft theme, figures4papers, 面积图, 趋势 | 风格参考 senlanke/figures4papers（无许可证，仅借鉴思路，代码重写） |
| `exceedance.py` | 超越曲线（尾部误差） | 结论是"大误差更少"：比较两三个方法逐样本误差分布的尾部 | 每个方法的逐样本误差（同一批样本） | 只有汇总误差（没有逐样本值）；结论关于平均水平而非尾部（改分布图或点 + 区间） | `evidence.exceedance` | exceedance, tail, per-sample, error, 超越曲线, 尾部 | 思路参考 taoge946/academic-figure-patterns（MIT），代码按 figkit 重写 |
| `gated_bubble.py` | 闸门气泡图 | 很多子指标的支持度差异很大，需要标出哪些可报告 | 汇总行：每个子指标的估计、CI、n 和是否过闸门 | 所有子指标支持度相近（普通点 + CI 即可） | `scatter.gated_bubble` | bubble, gate, support, 气泡, 闸门 | 项目实战提炼 |
| `paired_cloud.py` | 配对散点云（y = x 参考线 + 分箱中位数） | 同一批样本在两种条件 / 两个方法下的逐样本对比，结论体现在点云形状 | 逐样本成对数值（同一单位） | structure_strength 不通过（结构看不出，改差值分布或表格）；样本不成对 | `evidence.paired_cloud` + `evidence.binned_median` + `stats.structure_strength` | paired, scatter, identity line, per-sample, 配对, 散点 | 思路参考 taoge946/academic-figure-patterns（MIT），代码按 figkit 重写 |
| `sized_scatter.py` | 组级散点（面积 ∝ 组大小） | 按组看一致性 / 异质性，组大小相差很大 | 每组一行：x、y、组大小、分组标签 | 组大小相近（点大小无信息）；点数 > ~2000（改 hexbin） | `scatter.sized` | scatter, symlog, group size, 散点, 异质性 | 项目实战提炼 |
| `stacked_fraction.py` | 100% 堆叠横条 | 展示多行中总量如何分配到几个有序部分 | 每行一组计数（或比例） | 只有一个部分非零（删除或进表）；部分超过 ~5 个 | `bars.stacked_fraction` | composition, stacked bar, set size, 构成, 堆叠 | 项目实战提炼 |

## 版式

| 配方 | 图型 | 什么时候用 | 输入数据形状 | 不要用 | 库函数 | 关键词 | 来源 |
|---|---|---|---|---|---|---|---|
| `case_matrix.py` | 分组分层病例矩阵（代表图 + 多病例热图矩阵 + 局部放大） | 按类别 / 队列对照展示模型关注区域，每组 ≥ 12 例，分层随机选例且含错例 | 每例原图 (H, W) + 低分辨率热图 / 概念图 + 真值 / 预测；先用 stratified_cases 选例 | 只有 1–4 个病例（改单病例影像 panel 并在图注说明）；各例热图不能共用一个色阶（量级不可比） | `stats.stratified_cases` + `imaging.case_tiles` + `imaging.crop_window` + `imaging.concept_map` | case matrix, heatmap, CAM, gallery, 病例矩阵, 热图, 选例 | 项目实战提炼（版式参考乳腺 MRI 生境热图 + 病理放大的多病例组图） |
| `roc_grid.py` | ROC 小多图 | 同一组模型在多个队列上分别比较，每队列一格 | 队列 × 模型 × 重复的逐样本标签 + 分数 | 只有 1–2 个队列（直接并排两个 roc_mean_sd 即可） | `layout.small_multiples` + `curves.roc_mean_sd` | ROC, small multiples, 队列, 小多图 | 项目实战提炼 |

已有、未单独做配方的图型（见 `references/figkit_api.md`）：森林图 / 哑铃图 / 配对估计图（`intervals`）、
小提琴 / 箱线 / ECDF / HDR 轮廓（`dist`）、标注热图 / 瀑布图（`heat`）、混淆矩阵（`confusion`）、
B-scan 边界与分带 / 概念图 / 概率叠加（`imaging`）、阶梯图 / 干预曲线（`curves`）。

## 通用经验

- 颜色：数据色一律从 `figkit.toml` 色板取；同一 axes 里不同数据色 ΔE00 < 12 会被 `qa.palette_clash` 拦下
  （阈值可在 `[qa] palette_min_delta_e` 调）。选新色时用 `style.delta_e` 和图内每个颜色比，最好 ≥ 20。
- 参考线、对角线、背景带、尺寸图例都用 `style.aux` 标成辅助元素，不要画成灰色数据。
- 对数 / symlog 轴调用 `style.log_ticks(ax)`，否则默认的 10^{-k} 用 ASCII 连字符，过不了真减号检查。
- 图例压住数据时，换图例位置（`scorecard` / `sized` 有 `legend_loc` 参数，其余函数画完后调用 `ax.legend(loc=...)`
  覆盖），或者给轴范围留出空白，不要缩小字号（下限 6 pt）。`roc_mean_sd` 没有 `linestyle` 参数，需要线型冗余时
  画完后设置最后一条线（见 `roc_mean_sd.py`）。
- 只有一次运行时不画 SD 带，图注里要说明；SD 用样本 SD（ddof = 1）。
- DCA、风险覆盖是描述性分析，图注写明阈值没有在测试集上调，不构成临床决策依据。
