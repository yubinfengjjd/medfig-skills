# 判断示例

只学判断方式，不迁移具体内容。示例中的引用标识省略为 `(PMID: …)`，实际写作必须填入已核验的真实标识，不得照抄省略号或占位。

## 1. 总结段

- 不可：“Diabetic retinopathy is a leading cause of blindness worldwide (PMID: …). Deep learning has been widely applied … In this study, we developed … The model achieved an AUROC of 0.94 (95% CI 0.92–0.96), a sensitivity of 0.89, a specificity of 0.91 …”
  问题：重复 Introduction 背景，又把 Results 的指标整段搬来。
- 可以：“We asked whether a model trained on a single device retains its accuracy on scans from other devices. Accuracy was largely preserved on two of three external cohorts but fell on the cohort acquired with the oldest device, and most of this loss was recovered by recalibrating the final layer alone. These findings suggest that, in this setting, the representation transferred better than the decision threshold.”
  理由：一句回到问题，两句给发现（含例外），一句给含义；措辞为 suggest，并限定 in this setting。

## 2. 解释与推断强度

- 不可：“This proves that the decision layer causes the domain shift.”
  问题：prove 和 causes 超出观察性分析能支持的强度。
- 可以：“Because recalibrating only the final layer recovered most of the external loss (Fig. 4b), the shift appears to act mainly on the decision threshold rather than on the learned features. A direct test would require …”
  理由：解释落在本研究的具体分析上，并说明还缺什么检验。
- 不可：“This may be because the model learns retinal anatomy.”（Results 没有分析，也没有文献）
  可以：不写；或在有探针分析时写 “Layer-wise probes retained … (Fig. 5c), which is consistent with …”。

## 2a. 只重述、不解释

- 不可：“External transfer did not follow a common pattern. Cohort A had the lowest accuracy, and its probe already showed a deficit; cohort B retained probe discrimination with a larger loss at the decision head. Reduced source identifiability therefore did not imply preserved information.”
  问题：三句都是 Results 的换说法，外加一句否定限定；读者仍不知道为什么 A 最差。
- 可以：“Cohort A was the only external cohort dominated by intermediate AMD, whose drusen-level changes are subtler than the late-stage lesions that defined Degeneration during training; the early deficit in its concept probe may therefore reflect a disease-stage mismatch rather than an acquisition effect. Stage-matched scans from the same device would separate the two.”
  理由：给出由材料可核对的候选原因（队列构成），限定为 may，并说明区分它的检验。

## 3. 文献对比

- 不可：“Our results are consistent with previous studies (PMID: …; PMID: …; PMID: …).”
  问题：没有说一致在哪里，读者无法核对。
- 可以：“De Fauw et al. reported that separating segmentation from classification allowed transfer to a second device after retraining only the segmentation network (PMID: …). Our results point the other way for this task: the feature stage transferred, whereas the classification threshold did not. One reason may be that their second device differed mainly in image appearance, whereas our external cohorts also differed in disease prevalence.”
  理由：对方的条件和发现、本研究的不同之处、落在可核对差异上的可能原因。
- 不可：并列 “our AUROC of 0.94 exceeds the 0.89 reported by X”，而 X 报告的是患者级指标、本研究是扫描级。
  可以：说明定义不同、不直接比较数字。

## 4. 创新与意义

- 不可：“To the best of our knowledge, this is the first and most comprehensive study, with important clinical implications.”
- 可以：“Previous evaluations of concept-based OCT models reported accuracy on held-out data from the training site (PMID: …); by testing the same explanations across six external cohorts, this study indicates which concepts a reviewer can rely on when the model is applied to a new device.”
  理由：回应 Introduction 的空白，写明对谁、在哪个环节有用。

## 5. 局限

- 不可：“This study has some limitations. First, the sample size was small. Second, it was retrospective. Further studies are needed.”
  问题：通用局限，没有说影响哪个结论，没有可操作的方向。
- 可以：“All external cohorts were public datasets with labels assigned at the scan level, so the transfer estimates may not reflect performance on consecutive clinical scans, where disease prevalence and image quality vary more widely. Prospective evaluation on consecutive scans from devices not represented here would test whether the recalibration step is sufficient in routine use.”
  理由：具体局限 → 可能影响哪个结论及方向 → 可操作的未来研究。
- 不可：回避 Results 中一个队列覆盖率不达标的结果。
  可以：在局限或解释段如实写出该队列，并说明可能原因和对结论范围的影响。

## 6. 前置稿件缺失

- 情形：作者给了 Methods、Results 和图注，Introduction 还没写。
- 处理：说明 Discussion 要回应 Introduction 提出的研究空白和问题，Introduction 缺失时无法对齐，列出缺项（Introduction），建议先用 medical-sci-introduction 完成，然后停止。作者坚持也不起草。
