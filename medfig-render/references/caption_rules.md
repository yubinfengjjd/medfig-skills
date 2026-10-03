# 图注规则

图注草稿与图一起生成（`caption(prov)`），所有数字从 `prov.values` 取，不手写。

## 1. 必备要素（E3）
- 一句结论（与规格里该图的结论一致）。
- 每个 panel：展示内容、单位、n（写明单位：images / scans / patients / groups）。
- 区间：类型（95% CI、±1 SD、IQR）、n、重采样方法（例如 "cluster bootstrap, 2,000 resamples"）；没有区间估计时写 "no interval estimates in this figure"。
- 排除标准及计数（"2,000 → 1,850 after quality filtering"，数字来自数据）。
- 估计器细节：KDE 带宽规则、HDR 阈值定义、插值方法。
- 小样本提示：n 较小时只画 50% HDR，写 "indicative"。
- 同一病例出现在多张图时互相引用。

## 2. 探索性声明（E2）
按项目实际情况写入每个图注，例如："This is a post-outcome exploratory analysis without a prospective independent cohort."。有前瞻验证队列的项目改写为相应表述，但不能省略研究性质说明。

## 3. 适用限制（E4, E6）
凡相关就必须出现：
- 共享样本/成分的队列 → "not an independent replication"。
- 缺类别的队列 → "two classes only (no X)"，不能称"三分类验证"；标题里用 "(2-class)"。
- 预测轮廓 → "model prediction, not manual annotation"。
- CAM / 概念图 → 色阶跨病例共享；未展示的图及原因。
- 由汇总表派生的 panel → "does not reconstruct per-image distributions"。
- 缺像素间距 → 未画该方向比例尺。
- 显示宽高比 ≠ 原始（上游已缩放）；概率图的重采样（`_anchor_resampled`）。
- ROC 只有 1 次重复 → "single run; no SD band"；有 SD 带时说明 "±1 SD across runs, not a confidence interval"。
- 描述性结果 → "descriptive; does not support clinical decisions"。

## 4. 措辞（E1, E5, E7）
- 禁用词（与图、表共用同一张项目表 `qa.banned_list()`）：默认 validated, superior, clinical benefit, UMAP, deployment, diagnostic, clinically proven；项目在 `figkit.toml` 的 `[qa] banned_extra` / `banned_allow` 里增减。用 `qa.banned_in_text(caption)` 检查，命中即抛错。
- 阴性 / 不确定结果照实写。
- 对一组检验的笼统结论按可推翻它的极值判断：写 "all P > 0.05" 前检查 `min(p) > 0.05`，放在有单元测试的函数里。
- `<` 与 `≤` 按真实值取舍；设计限制最小可达 P 时写明。
- 方法描述（约束、归一化、校准方式）必须能追溯到配置或运行记录；模型变更后全文搜索旧属性。
- 负号用真减号 U+2212，区间用 en dash（0.81–0.88）。

## 5. 偏离披露（E8）
相对规格的任何偏离（panel 移动、图型降级、非标准宽度、占位）写进交付说明的"偏离"清单，并在图注中必要处体现。
