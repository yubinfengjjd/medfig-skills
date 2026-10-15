# 规则示例归档

本文件仅作规则说明的补充示例，不是写作模板，也不要求新课题出现相同情形。来源：作者在 2026-10-11 至 10-12 审阅某 OCT 深度学习课题的 Methods 稿时确认的处理方式。写作新课题时只学习其判断方式，不把这些对象、数值或术语迁移到新稿。

## 管理性元叙述（规则第 2 节）

| 原句类型 | 示例 | 处理 |
|---|---|---|
| 泛化研究性质定性 | “Analyses beyond the primary endpoint were exploratory.” | 删除 |
| 计划与执行状态盘点 | “Items not collected or not executed, including the reader study and the observed-concept ceiling, are listed in Table S1.” | 删除；正文和核查说明都不列 |
| 通用自证 | “No values were simulated or imputed for these items.” | 删除 |
| 空泛导航 | “Dedicated transport analyses used target-cohort information as specified in Section 2.4.1.” | 删除；在 2.4.1 直接写目标标签如何拟合与评估 |
| 应保留的具体事实 | “Missing concept labels were masked.”“The target-label bias was fitted and evaluated on the same target cohort.” | 保留 |

## 比例分母与门槛对象（规则第 2 节“事实核对”）

- 错误：“Subjects were allocated to training, validation and evaluation partitions (60%, 20%, 20%).”
- 实际：先留出约 20% 受试者评估，再从剩余受试者取约 20% 验证。应按先后顺序写明分母。
- 错误：“at least 10 positive eyes”。实际调用统计的是有效标注扫描所来自的眼数，应写“at least 10 eyes represented among validly labelled scans”。

## 计数单位（规则第 8 节第 5 步）

- 错误：“The evaluable subset contained 120 images.”——实际代码对每张图像的每个病灶类别各记一条，120 是“图像–病灶类别对”的数量。
- 应写：“The evaluable subset comprised 120 image–lesion-class pairs from 40 images.”（材料给出图像数时一并写出）。
- 同类情形：按眼计数与按扫描计数、按受试者计数与按访视计数、配对分析中“有效配对数”与“样本数”。

## 模型分支范围

- 错误：“These runs shared the single anatomical adaptation.”——黑箱与常规概念瓶颈对照实际从原始预训练骨干开始，未载入解剖适配参数。
- 应分别写明：哪些模型从共享解剖参数初始化，哪些模型重拟合三分类头，黑箱对照不进行概念头重拟合。

## 内部编号替换（规则第 3 节）

- 内部代号 `R0–R5` 指一个内部参照和五个目标队列条件。正文写“an internally fitted reference and five target-cohort conditions”，再逐项按科学含义命名；不称“six algorithms”。
- `Wave-2`、`E-7`、ledger key 等只出现在核查说明的映射中。

## 范围冲突（规则第 1 节）

- 大纲“写作重点”写错误分诊用两个信号，同一节代码映射写“三信号”。正文按写作重点写两个信号，冲突列入核查说明，由作者裁决是否更新大纲。

## 实现层质控（规则第 5 节）

以下句子属于实现核对，不进正文；必要时记入核查说明：

- “Reconstructed individual logits were required to agree with stored logits within 1e-5.”
- “The fixed model was rerun and its outputs were checked against the stored predictions.”
- “Eye uniqueness was checked after selection.”
- “Images were ordered by the SHA-256 hash of their path.”（改写为“a deterministic, prediction-independent sample of up to 3,000 images per dataset”即可）

## 目的句写法（规则第 5 节）

反例 1（相邻段落套同一状语模板）：

> To assess calibration, we … / To evaluate cross-cohort performance, we … / To examine concept attribution, we …

反例 2（换了开头词，句式仍相同；分析被写成执行动作的主语）：

> Group resampling quantified uncertainty … / Prediction sets quantified uncertainty … / Interventions assessed which features …

改写：“Uncertainty was estimated by resampling patients …”“We constructed prediction sets to …”“Feature interventions tested whether …”中只保留确有必要的一种，相邻段落改用不同结构。

可选写法（按信息重点选用，不轮换凑数）：

- 目的并入主句：“Calibration was examined because the decision thresholds depend on the probability scale.”
- 以对象开头、用途后置：“A logistic recalibration was fitted in each external cohort to separate threshold shift from changes in discrimination.”
- 以研究问题开头：“Whether feature attributions remained stable across sites was examined by …”
- 需要强调目的时再用状语开头：“To assess whether …, we …”

## 新增细节的取舍（规则第 5 节、第 8 节）

- 保留：分区样本量、纳排门槛、关键超参数（帮助理解方法）。
- 不进正文：检验得到的 P 值、实际观测到的类别计数分布（属于结果）；去重算法名称、采样器名称、随机变量来源（属于实现）。
- 常见的回查遗漏（通用描述）：把“在 A 集拟合、在 B 集评估”的参照写成“在 B 集拟合并评估”；凭印象写输出头或对照模型的结构，而未核对配置；把同时改动多项的消融归入“每项只改一个组件”。这几类都出自修订时新增、但未回查的事实句。

## 中文对照：直译与重组（规则第 6 节）

英文：“Missing covariates were handled by complete-case analysis, and the threshold was selected on the validation set before being applied to the test set.”

- 直译（避免）：“缺失的协变量被通过完整病例分析处理，并且阈值被在验证集上选择，然后才被应用于测试集。”
- 重组（采用）：“协变量缺失时采用完整病例分析；阈值在验证集上确定后，再应用于测试集。”
