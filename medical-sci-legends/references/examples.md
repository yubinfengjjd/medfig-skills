# 判断示例

只学习判断方式，不把示例中的对象、数值或术语迁移到新稿。示例数据为虚构。

## 只写图形 / 只写结论 → 证据与含义融合（规则第 3 节）

- 避免（只写图形）：“(C) Box plots of Dice scores for each anatomical band.”
- 避免（空泛结论）：“(C) Dice scores indicate high segmentation accuracy in all bands.”
- 采用：“(C) Dice scores across three seeds cluster near 1 for the inner and outer bands, whereas the middle band shows lower and more dispersed values.”

## 机械句式 → 随图变化（规则第 3 节）

- 避免：“(A) Violin plot showing … (B) Scatter plot showing … (C) Line plot showing …”
- 采用：“(A) Boundary errors of the learned model fall below those of the rule-based method at every interface. (B) Paired scan-level errors lie mostly below the identity line. (C) Coverage declines as the review budget shrinks, …”

## 同类 panel 合并（规则第 4 节）

- 避免：“(A) The confusion matrix for seed 0 shows … (B) The confusion matrix for seed 1 shows … (C) The confusion matrix for seed 2 shows …”
- 采用：“(A–C) Row-normalized confusion matrices across three seeds show consistently high recall for classes X and Z, whereas recall for class Y varies from 88.2% to 91.0%. (D) Pairwise prediction agreement between seeds ranges from 97.9% to 98.4%.”
- 不合并：三个 panel 都是混淆矩阵，但分别对应内部、外部队列 1、外部队列 2，且外部队列 2 出现了不同的错误方向。这时分别写，或合并前两个、单写第三个。

## 详细图注 → 图注（规则第 1、3 节）

详细图注原文（虚构）：“**b**，骨干表示（768 维，seed 0）的 PCA。每个数据集按 image_path 的 SHA-256 升序取前至多 2000 张；主成分只在内部样本（n = 2,410）上拟合；PC1、PC2 分别解释 48.2% 和 20.7%。核密度等高线（Scott 带宽）为 50% 与 90% 区域，颜色 #0072B2 为队列 A。”

- 避免：照搬抽样规则、维度、带宽、色号。
- 采用：“(B) Principal component analysis fitted on internal scans only places each external cohort in a distinct region of backbone-feature space; the first two components explain 48.2% and 20.7% of the variance. Contours, 50% and 90% highest-density regions.”

## 数字堆砌 → 范围与例外（规则第 3 节）

- 避免：“(A) Scan-level BACC is 0.802 for Cohort A, 0.938 for Cohort B, 0.929 for Cohort C, 0.859 for Cohort D, and 0.934 for Cohort E.”
- 采用：“(A) Scan-level BACC remains between 0.929 and 0.938 in the three-class cohorts but falls to 0.802 in Cohort A.”
- 避免：“(A–C) Class recalls are 0.988/0.941/0.971, 0.988/0.924/0.972, and 0.982/0.917/0.977.”
- 采用：“(A–C) Recall is consistently high for classes X and Z across seeds, whereas class Y varies from 91.7% to 94.1%.”

## 免责句 → 中性描述（规则第 6 节）

- 避免：“(E) Precision–recall curves give AP values of 0.926, 0.972, and 0.952; these curves are descriptive and do not establish a model ranking.”
- 采用：“(E) Precision–recall curves for class Y overlap across the three models (AP, 0.926–0.972).”
- 避免：“The overall result is mixed and not significant.”——直接写各指标的方向和区间，读者自己能看出是否跨零。

## 过度解读（规则第 6 节）

| 图与材料支持的事实 | 避免 | 采用 |
|---|---|---|
| 两组均值不同，无检验 | “Model A performs significantly better than model B.” | “Model A has higher BACC than model B in all three seeds.” |
| 配对差值区间跨零，上限低于预设界值 0.5 px | “Training does not affect segmentation.” | “Paired errors follow the identity line (mean difference, +0.02 px; 95% CI, −0.01 to 0.06), with the upper limit below the prespecified 0.5-px noninferiority margin.” |
| PCA 中外部队列与内部分开 | “Device differences cause the domain shift.” | “External cohorts occupy regions separate from the internal distribution.” |
| 解释图在病灶区域高亮 | “The model relies on fluid to diagnose edema.” | “Concept evidence for fluid overlies intraretinal cystoid spaces in this example.” |

## 尾注（规则第 5 节）

- 避免：“Error bars represent 95% CIs computed with 2,000 cluster-bootstrap resamples stratified by patient using the percentile method.”（计算过程归 Methods）
- 采用：“Points, seed means; error bars, 95% CIs. Dashed line, 90% nominal coverage. †Cohorts B and C share duplicate images and are not independent. BACC, balanced accuracy; CI, confidence interval.”
- 避免：缩写在 panel 句内已展开，尾注又列一次；或尾注列了图注中没有出现的缩写。

## 表格标题与表注（规则第 7 节）

- 避免（标题写发现）：“Table 2. The model maintains performance in most external cohorts.”
- 采用：“Table 2. Three-class performance by cohort and analysis unit.”
- 表注采用：“Values are means across three seeds with min–max in parentheses; 95% CIs span the smallest lower and largest upper per-seed bounds. —, class absent. Cohorts D and E contain two of the three classes and were scored on the observed classes. BACC, balanced accuracy; CI, confidence interval.”

## 量的定义与拟合划分（规则第 1、10 节）

- 详细图注写"三个概念概率的均值"，代码是 `concept_scores[:, idx].mean(axis=1)`，而存储注明 concept_scores 是 logits → 图注写"三个概念分数（logit）的均值"，不写概率。
- 图注写"探针在训练集上拟合"，代码是 `information_loss_ladder(cal, ...)`、`cal = stores["calib"]` → 图注写"在校准分区扫描上拟合"。
- 训练期序数损失的加权负荷（1.0/1.0/0.5）与图内分析的未加权均值不是同一个量，图注只写后者，并在核查说明中记一句区分。

## 中文对照（规则第 8 节）

- 英文：“(B) Paired scan-level errors lie predominantly below the identity line.”
- 避免（直译）：“(B) 配对的扫描级的误差主要地位于恒等线的下方。”
- 采用：“(B) 逐扫描配对误差大多位于恒等线下方。”
