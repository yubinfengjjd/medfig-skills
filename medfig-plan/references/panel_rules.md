# panel_rules：panel 字段、版式与编码规则

## 1. 五字段（每个 panel 必填，A1）

```markdown
- **a <短标题>**
  - claim：<一句话结论，读者看完该相信什么>
  - data：<相对数据根的路径> · 列/键 <col1, col2> · 筛选 <条件> · 变换 <确定性变换或"无">
  - chart：<图型>；x=<>，y=<>，颜色=<>，marker=<>，分面=<>
  - reason：<为什么是这个图型；为什么不是更常见的替代>
  - caption：<单位；n 及其单位；区间类型与 bootstrap 方式；排除项与计数；限制声明>
  - counterfactual：<结论不成立时本 panel 会是什么样子；必须是所选图型能显示出来的样子>
```

拒收条件：claim 为空或写成描述（"展示 X 的分布"不是结论）；data 无法定位到列；chart 未写编码；reason 缺失；counterfactual 缺失或所选图型显示不出来。

## 2. 一 panel 一结论（A1）

- 一个 panel 要支撑两个结论 → 拆成两个 panel。
- 说不出结论的 panel → 删，或移到附图作为细节，并在附图 claim 中写清它支撑哪个主结论。
- 同一病例 / 同一数据在两张图里出现，角色必须不同，图注互相引用（A6）。

## 3. panel 数与版式（A2, A4）

- panel 数按论证定：1、2、3、5、7 都正常；禁止为了整齐凑成 4 个或机械 2×2。
- 每张图标题行写：`Fig N <主题>（k panel；版式一句话）`，例：
  - "2 panel；左 2/3 大图 + 右 1/3 窄条"
  - "5 panel；上排通栏影像 a，下排 b 宽、c/d/e 窄"
  - "7 panel；左侧影像块 a1–a4，右侧叠 b/c/d"
- 版式要能直接翻译成 GridSpec（width_ratios / height_ratios / 嵌套），并写明成图尺寸（按期刊栏宽）。
- 子标签（a1–a4）也算 panel 计数的一部分，在规格里写清，交付时核对数量（A4, E8）。

## 4. 编码规则（A3）

| 数据结构 | 规则 |
|---|---|
| x 有序（时间、剂量、阶段、k） | 可连线 |
| x 为类别 | 不连线；用点 / 柱 / 分面 |
| n 很小（seed、受试者 ≤ 5 左右） | 画全部点，不画柱 + 误差棒 |
| 值为 0 或无变化 | 不画零高柱；改点图（0 点可见）或直接删除该信息；不做纯文字 panel（S2） |
| 组间相差数量级 | log 轴，并在轴标签注明 |
| 有逐样本数据 | 画分布（violin + strip、box + swarm、ECDF），不只画均值 |
| 只有汇总行（均值 + CI） | 画区间点；不重建分布（A3） |
| 不可估计 / oracle / absent | 斜线阴影 + "n/a" / "absent"，不留白、不画 0 |

## 5. 全局视觉约定（写进规格 §2）

- 固定配色表：分组（队列 / 中心 / 设备）一套、类别一套，全套一致；色盲友好（Okabe-Ito）；禁 jet。
- 冗余编码：类别 / 方法 / 排序同时用 Okabe-Ito 颜色 + 线型或 marker，保证灰度可辨；不用黑 / 灰区分方法或排序（S3）。
- 连续色图：顺序用 viridis / magma，发散以 0 为中心（RdBu_r）。
- 区间：统一类型（如 95%），图注写 bootstrap 方式与次数。
- 内部 vs 外部 / 开发 vs 验证：固定先后顺序与间隔。
- 字号与标签格式跟期刊（第 2 步确认），正文标签不低于期刊下限。
- 图内文字 = 结果 + 读图编码。免责声明、方法口径、结论、交叉引用、内部代号（终点 / 假设 / 规则编号、列名）进图注；不加图底注释行。规格写代号对照表，代号写进 `[qa] forbidden_patterns`（medfig-render `qa.figure_text_audit` 导出时硬拦）。

## 6. Panel 样式与组图规范（S1–S7，绑定）

规划阶段就要让每个 panel 满足下列规则；渲染与 QA 阶段按同一编号检查，超标即 FAIL。

- S1 版面留白：影像列的 `width_ratios` 按图像宽高比（w/h）分配，不给影像列平均列宽；图例放图像内角或紧贴上方，不单独占侧栏。任一 panel 内容 bbox 左右空白合计 ≤ 该 panel 宽度 15%；letterbox 留白（图像按 aspect equal 缩进等宽列后两侧的空白）不算达标，width_ratios 必须按图像宽高比设定。规格版式行写明每列 ratio 及其来源（图像宽高比）。
- S2 禁止纯文字 panel：只有文字、没有数据图元的 axes 不规划、不输出。这类信息直接删除，不迁到图注，也不改成别的 panel 的大段注释。"零值 / 单一数字"一律不单独成 panel。
- S3 数据图元必须有颜色：所有数据元素（线、点、柱、区间、热图 cmap）有色（饱和度 > 0.15）；灰色只用于辅助元素（坐标轴、网格、参考线、对角线、底带）。区分方法 / 排序用 Okabe-Ito 色 + 线型 / marker 冗余编码，不用黑 / 灰区分。方法色与队列色不得撞色：先定队列色，方法色从剩余 Okabe-Ito 色中取，规格 §2 配色表同时列出两套并注明不冲突。
- S4 单 panel 独立导出：每个 panel 另出可编辑 PDF（必需）+ SVG（fonttype 42、文字可选），尺寸与它在组图中的尺寸一致，不带 a/b/c 序号；序号只在组图里出现。命名 `<figure>_<panel>.pdf`（如 `fig2_b.pdf`），并写入 source.json。规格每个 panel 写明该文件名。
- S5 ROC 样式：正方形坐标；虚线对角 chance line；多次重复（seed / fold）先插值到共同 FPR 网格（`np.interp`，不用已废弃的 `scipy.interp`），画平均曲线 + ±SD 阴影带；图例写 "AUC = mean ± SD"，放右下角；x 轴标 "1 − specificity"，y 轴标 "Sensitivity"；配色 Okabe-Ito。只有单条曲线时不画 SD 带，并在图注说明。样式来源：MenglinLu/Retinal_VascularEvents `visualization/ROC curve.py`（MIT License），实现处保留来源注释；原代码 x 轴标 "Specificity" 为笔误，已更正。

- S6 病例影像要密、分组、分层，选例可追溯：代表性病例 panel 按类别或队列分组并排；每组 = 一行代表性原图 + 叠加 + 一个多病例图矩阵（每组 ≥ 12 例，全部病例共用一个色阶，colorbar 标原始单位）+ 一行局部放大（放大框在原图上标出）。病例在看图像和模型输出之前按规则抽取：按组分层、固定 seed 随机、每组必须含误判病例，不按置信度或观感挑。panel 写 `case_selection：<规则；seed = N；每组 n（其中误判 m）；候选池>`；source.json 记 `values.case_selection`（seed、rule、strata、per_group、pool、pool_counts）；图注写规则、seed 与候选池限制。病例行标队列 / 真值 / 预测，误判病例用单独的描边色（色板里给"误判"一个角色，不借用类别色）。单病例报告页写 `case_selection：single illustrative case; exempt: <原因>`。
- S7 主图性能曲线（硬规则）：主图报判别性能且有逐样本分数时，至少一个 ROC 曲线 panel（S5 样式），类别不平衡时加 PR；图例写 AUC 及 95% CI（或多 seed mean ± SD）。点估计、哑铃图、记分卡可作补充 panel，不能代替曲线。没有逐样本分数时，在图标题行下写 `- curve_exempt：<原因>` 并降级为区间点。

规划自检：逐 panel 核对 S1–S7，不满足的改规格；无法满足的写进"偏离"节并说明原因。
