# 判断示例

只学判断方式，不迁移具体内容。示例中的引用标识省略为 `(PMID: …)`，实际写作必须填入已核验的真实标识，不得照抄省略号或占位。

## 1. 结果泄露

- 不可：“We show that the hybrid model detects referable diabetic retinopathy with an AUROC of 0.94 and generalizes across three devices.”
  问题：给出性能数字和“泛化成立”的结论。
- 不可：“Our analysis reveals that most of the external performance loss arises in the decision layer.”
  问题：reveals 后接本研究的发现。
- 可以：“We trained the model on one device and evaluated it on three external cohorts acquired with other devices, asking whether any loss of performance arises in the learned representation or in the final decision layer.”
  理由：只写设计和问题，答案留给 Results。

## 2. 研究空白的依据

- 不可：“No study has ever examined concept stability in retinal imaging.”
  问题：绝对化，无法核验。
- 可以：“Concept-based models have been evaluated mainly for accuracy on held-out data from the training site (PMID: …; PMID: …), and whether their explanations remain stable across random seeds or acquisition devices has rarely been tested.”
  理由：空白由所引研究的评估范围推出，措辞审慎；检索记录写入核查说明。

## 3. 综述的组织

- 不可：逐篇罗列：“Smith et al. used a CNN. Lee et al. used a transformer. Wang et al. used an ensemble.”
- 可以：按问题归纳：“Deep networks trained on single-center OCT data reach high internal accuracy (PMID: …; PMID: …), but performance often falls on scans from other devices or populations (PMID: …), and dataset-level leakage can inflate internal estimates (PMID: …).”
  理由：一句话给出共同成就、失效条件和方法学隐患，每个判断都有引用。

## 4. 创新点与意义的措辞

- 不可：“We propose a novel, powerful framework that will transform glaucoma screening.”
- 可以：“Unlike post hoc saliency methods, the model routes every prediction through clinically named intermediate features, so that each decision can be decomposed into feature contributions and checked against expert annotation.”
  理由：用与现有工作的具体区别代替评价形容词。
- 意义段，不可：“This approach could reduce screening costs and improve patient outcomes worldwide.”（材料不支持）
  可以：“Locating where transfer fails indicates which component would need site-specific adaptation before such a model is considered for use on unseen devices.”

## 4a. 设计段的详略

- 不可：“The primary endpoint distinguishes A, B and C, with a separately trained binary endpoint. B corresponds to …; C groups source labels for …. Training separates anatomical adaptation, joint learning and fitting of the final layer. External subjects are excluded from development and calibration. Matched black-box and concept-bottleneck comparators, together with ablations, …”
  问题：标签映射、训练阶段、排除规则、比较器清单都是 Methods 内容；读者读完仍不知道本研究要回答什么。
- 可以：“We developed X, a classifier that routes OCT features through retinal layers before scoring named biomarkers, and evaluated it on one internal and six external public cohorts acquired with different devices. We asked whether anatomical constraints cost accuracy, where any loss on external devices arises, and whether the resulting explanations remain stable when the model is retrained.”
  理由：一句交代设计要点，一句把分析归并为三个问题。

## 5. 背景中的数字

- 不可：“Age-related macular degeneration affects about 200 million people worldwide (PMID: …).”——若所引文献摘要中没有这个数字，或数字与摘要不一致。
- 可以：照摘要中的数字和年份写，例如摘要报告的是“2020 年预计 1.96 亿”，正文就写 “an estimated 196 million people in 2020”。

## 6. 引用与论断的对应

- 不可：把一篇在本院数据上应用 Grad-CAM 的论文引作 “saliency maps are known to be unreliable”。
  问题：该文献没有检验可靠性，元数据存在不等于支持论断。
- 可以：引用直接检验了显著性图可靠性的研究，并在核查说明的“正文用途”列写明支持的是哪句话。

## 7. 前置稿件缺失

- 情形：作者只给了大纲和 Methods，Results 和图注尚未写。
- 处理：先告诉作者引言通常最后写，缺 Results 时无法确认引言提出的问题都有对应分析，建议补齐后再写。作者坚持时按大纲的研究问题保守撰写，核查说明第 1 部分写明“Results、图注缺失，研究问题与分析的对应未核对”。
