# chart_diversity：结论类型 → 图型

原则：图型由结论类型和数据结构决定（A3）。同一图型在全套重复出现要写理由；森林类（forest / 点 + CI 横排）全套 ≤ 3 处，每处一句理由（A2）。

## 1. 统计 panel

| 结论类型 | 推荐图 | 禁用图 | 降级路径（数据撑不起时） | 配方 / 库函数（medfig-render gallery） |
|---|---|---|---|---|
| 组间分布差异（逐样本） | violin + strip；box + swarm；ECDF | 均值柱 + 误差棒 | 仅汇总行 → 区间点；取值离散 → 分组柱 | `dist.violin_strip` / `dist.box_swarm` / `dist.ecdf` |
| 少数重复（n ≤ 5 seed / 受试者） | 点图（全部点 + 均值标记）；soft 柱 + min–max 须线（图注写明 seed 数） | 只有柱 + 误差棒 | — | `slope.py`；`multi_metric_bars.py` |
| 多方法 × 多指标对比 | 每指标一个小图 + 共享图例 panel（soft：本文方法饱和色、对照浅色、平涂、柱顶数值；截断值轴必须画断轴标记） | 截断却无断轴标记；每个小图各配图例 | 方法 > 6 → 分组或小多图 | `multi_metric_bars.py` |
| 一个指标、3–5 个同类对照方法 | soft 单指标柱：对照用同色相渐变（≤ 4 个）、本文方法饱和色、图例放 axes 内上方 | 对照方法本身要互相比较时用渐变 | 对照 > 4 → pastel 浅色 | `metric_bars_gradient.py` |
| 有序消融 / 逐步叠加 | 单色相梯度横柱（2–5 级）；阶梯图 | 无序的彩虹色柱 | 超过 5 级 → 点图 | `ordinal_ablation.py` |
| 尾部 / "大误差更少"（逐样本） | 超越曲线（log y） | 只报平均误差 | 仅汇总 → 区间点 | `exceedance.py` |
| 两种测量一致性 | Bland–Altman（偏差 + 一致性界限） | 只用相关系数 | — | `bland_altman.py` |
| 累计数量随时间 | 面积趋势（≤ 3 类） | 3D 面积 | 类别 > 3 → 小多图 | `area_trend.py` |
| 配对前后 / 两方法配对 | 斜率图；配对散点 + y = x 参考线与容差带（先过 `stats.structure_strength`） | 两根独立柱 | 无配对 id → 并列区间点，图注说明未配对 | `slope.py`；`paired_cloud.py`；`intervals.estimation` |
| 两条件差值 + 不确定性 | Gardner–Altman estimation；哑铃图 | 仅 P 值星号 | 无逐样本 → 差值区间点 | `intervals.estimation` / `intervals.dumbbell` |
| 多个估计对同一零线 / 名义水平 | 森林图（计入 ≤ 3 预算） | 多组柱 | 项目少（≤ 3）→ 点 + CI 竖排 | `intervals.forest`；`or_forest.py` |
| 构成 / 比例 | 100% 堆叠柱（外侧标 n） | 饼图、3D | 只一类非零 → 删除或进表，不做纯文字 panel（S2） | `stacked_fraction.py` |
| 分类性能（混淆） | 行归一化混淆矩阵小多图（absent 行阴影） | 只报 accuracy | 类别缺失 → absent 标注，不画 0 | `confusion.matrix` |
| 判别曲线 | ROC（S5：共同 FPR 网格 mean ± SD 带）/ PR 小多图（PR 用于不平衡） | 只报 AUC 数字 | 无曲线点 → 表格；单条曲线 → 不画 SD 带并在图注说明 | `roc_mean_sd.py`；`roc_grid.py`；`pr_mean_sd.py` |
| 校准 / 覆盖 | 可靠性图；覆盖–α 曲线；风险–覆盖曲线 | 单点覆盖率柱 | 只一个 α → 点 + CI | `calibration.py`；`risk_coverage.py` |
| 临床效用（描述性） | DCA 净获益曲线 | 带"获益"措辞的柱 | — | `decision.py` |
| 有序过程 / 逐步损失 | 阶梯图（step ladder）；瀑布图（先检查闭合） | 无序柱 | 闭合失败 → 停下报错，不画 | `curves.step_ladder` / `heat.waterfall` |
| 表示空间 / 域偏移 | PCA 密度 HDR 等高线 + 质心（标方法名） | 未标方法的 2D 嵌入 | 小 n → 只画 50% HDR + 质心，图注"仅供参考" | `dist.hdr_contour` |
| 大量点二维关系 | hexbin；散点 + 透明度 | 过绘散点 | — | `sized_scatter.py`（组级） |
| 矩阵型结果（条件 × 指标） | 注释热图；聚类热图 + 边际图 | 大量并列柱 | 缺格 → 斜线阴影 | `heat.annotated` |
| 多指标记分卡 | 点 + CI 记分卡（附最小可达 P 竖线） | 雷达图 | — | `scorecard.py`；`gated_bubble.py` |
| 集合交集 | UpSet（≥ 2 个交集时） | 维恩图（> 3 集合） | 只一个交集 → 横向条形 | — |
| 零值 / 无变化 / 单一数字 | 并入相邻数据 panel 的点图（0 点可见），或删除 | 零高柱；纯文字 panel（S2） | — | — |

配方名（`*.py`）指 medfig-render `examples/gallery/` 下的可运行脚本，选型确定后在规格 chart 列写上配方名；
`模块.函数` 指库里已有、但没有单独配方的函数。

## 2. 影像 panel（交 scipilot-medimg 规则）

影像 panel 在本技能只做选型与数据有效性判断；具体渲染（叠加、比例尺、QA）由 medfig-render 调用 scipilot-medimg-figure-skill 的规则。

| 结论类型 | 推荐 | 禁用 | 降级路径 |
|---|---|---|---|
| 代表性病例外观 | 影像网格，aspect equal，列宽按图像宽高比（S1） | 拉伸到统一框 | 上游已重采样 → 图注注明显示比例 ≠ 原始比例 |
| 分割 / 边界 | 影像 + 轮廓，标明来源（人工 / 模型预测） | 把预测当标注 | 无人工参照 → 只画预测，标"predicted, no manual reference"，定量比较放统计 panel |
| 显著性 / 概念图 | 共享色阶（同 panel 共用 vmin/vmax），colorbar 标原始单位 | 逐图 min-max 放大 | 原始量级接近数值噪声 → 不展示，换可信图并在图注写原因 |
| 仅正激活有意义 | vmin = 0，≤ 0 透明 | 负值被着色 | — |
| 物理尺度 | 仅在有文档依据的轴画比例尺 | 猜测像素间距 | 无间距 → 不画比例尺 |
| 病例报告页 | 影像 + 概率条 + 预测集 | 暗示临床验证 | 图注"示例，非临床验证" |

## 3. 重复预算记录

规格末尾列一张表：图型 → 出现位置 → 理由。森林类行数 > 3 即自检不通过。
