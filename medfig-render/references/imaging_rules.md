# 影像 panel 红线

适用于组图中的任何医学影像 panel（OCT B-scan、眼底、CT/MRI 切片、病理）。每条都有对应的代码约束或检查；违反时宁可删 panel，也不交出误导性的图。

## 1. 不拉伸（B1, S1）
- 影像一律 `aspect="equal"` + `set_anchor("C")`：`imaging.raw_image` / `bscan_with_boundaries` / `concept_map` / `prob_overlay` 已强制。禁止 `imshow(aspect="auto")`。
- 列宽按宽高比分配：`gridspec width_ratios = layout.image_width_ratios([img.shape[:2], ...])`，否则 letterbox 留白会被 `qa.whitespace_audit` 判 FAIL（左右空白合计 > 15%）。
- 图例放图内角或紧贴上方，不单独占侧栏。
- 上游已统一缩放过（例如模型输入网格）时，图注写明"显示宽高比不是原始宽高比"，并在 provenance 记录原始尺寸。

## 2. 掩膜不缩放（B1）
- 分割掩膜、类别掩膜必须与原图同一像素网格。`bscan_with_boundaries(band_masks=...)` 形状不符直接 `ValueError`。
- 不要为了"对齐"去 `upsample` 掩膜；`upsample` 只用于概率 / 激活图。
- 模型只输出低分辨率图时，按概率图画：`imaging.prob_overlay(ax, raw, prob, vmin, vmax, resample="bilinear")`。它不是掩膜，colorbar 标 "probability"，`ax._anchor_resampled = (src, dst, method)` 写进 provenance 和图注（"由 h×w 以双线性插值重采样到 H×W"）。
- 类别掩膜的数值-类别映射必须有出处；查不到就不画该层。

## 3. CAM / 概念图共享色阶（B2, B3）
- 同一 panel 内所有图共享一个 `vmin, vmax`：先在所有展示病例上统一计算，再逐个调用 `concept_map(..., vmin, vmax)`。禁止逐图 min-max 归一化。
- colorbar 显示原始单位；图注说明"色阶跨病例共享"。
- 先看原始量级：原始最大值在数值噪声水平（例如 1e-10 量级）的 CAM 不画，改用概念空间图，并在图注写明为何不展示。
- 只显示正向激活：`concept_map` 中原值 ≤ 0 恒透明（共享 vmin 为负时也不会把负值图涂满），归一化值 < 0.15 透明；阈值 `ax._anchor_threshold` 记入 provenance，图注说明。

## 4. 比例尺只画有依据的轴（E4）
- 只有文档给出像素间距（µm/pixel）的轴才画比例尺；间距来源写入 provenance。
- 横向间距缺失 → 不画横向比例尺，图注说明；不要估算、不要借用别的设备参数。

## 5. 轮廓与叠加的来源
- 预测轮廓 / 预测掩膜必须标明来源："model prediction, not manual annotation"（图例或图注）。
- 金标准与预测同时出现时用颜色 + 线型冗余编码（例如金标准实线、预测虚线）。
- 边界线、叠加色一律饱和色（S3）；原始灰度影像由 `raw_image` 标记豁免，其他灰色数据图元会被 `qa.colour_audit` 判 FAIL。

## 6. 显示处理留痕
- 只允许整图线性窗宽窗位；参数记入 `prov.add_transform`。
- 不做超分、锐化、局部对比度增强；不用插值应付分辨率检查。
- 导出前确认没有患者信息残留（烧录文字、ID、日期）。

## 7. 多病例分层矩阵（S6）
- 展示"模型看哪里"的影像 panel 不放 3–4 个挑出来的病例：按类别 / 队列分组并排，每组一行代表图 + 叠加、一个 ≥ 12 例的热图矩阵（全部共用一个色阶）、一行局部放大。配方 `examples/gallery/case_matrix.py`。
- 选例用 `stats.stratified_cases`：每组在对 / 错两层内固定 seed 随机抽，必须含错例；不按置信度、不看图挑。某层不够数就报错，回规划阶段改每组例数或分组，不悄悄缩小矩阵。
- `prov.set("case_selection", record)`；图注写选例规则、seed、每组对 / 错例数、病例池（例如"可用原图子集"）与错例框的含义。
- 小图用 `imaging.case_tiles`：同宽高比的确定性裁剪（`crop_window`，中心为热图质心），每格窗口写进 provenance；图注说明小图是裁剪视野。figure 用 `layout="none"`，位置由函数精确计算。
- 代表图从已抽中的病例里取（例如每组第一个正确病例），不另外挑。

## 8. 纯影像网格交给 scipilot-medimg
只有影像 + 掩膜/热图/放大框、没有统计 panel 的图，用 `scipilot-medimg-figure-skill` 的 JSON 规格渲染（`python scripts/image_panel.py spec.json`），它自带掩膜配准、比例尺、provenance 与图注草稿。影像与统计混排才用 figkit。
