# 判断示例

只学习判断方式，不把示例中的对象、数值或术语迁移到新稿。示例数据为虚构。

## 绘图描述 → 结果陈述（规则第 4 节）

- 避免：“Fig. 3B presents violin plots of boundary error, colored by method, with medians marked by white dots.”
- 采用：“Median boundary error of the learned segmenter did not exceed 2.4 px in any dataset, whereas graph search reached 28.1 px at the inner boundaries (Fig. 3B).”

- 避免：“Kernel density contours (Scott bandwidth) show 50% and 90% highest-density regions for each cohort.”
- 采用：“External cohorts formed distinct clusters whose centroids lay outside the internal distribution (Fig. 2B).”

## 方法复述 → 必要条件从句（规则第 4 节）

- 避免：“We extracted 1,536-dimensional pooled features, centered them on the internal set, fitted PCA and projected all samples.”
- 采用：“In a principal component analysis fitted on internal scans only, …”

## 连接词（规则第 4 节）

- 避免：“First, … Then, … Moreover, … Finally, …”
- 采用：以内容衔接。“Recall was lowest for edema (92.7%). Most misclassified disease scans were assigned to the normal class rather than to the other disease class (Fig. 4A).”“This decline was concentrated in …”“Across seeds, …”

## 平均用力 → 突出重点（规则第 3 节）

- 避免：把表格中七个队列、三个模型、四个指标逐一写出。
- 采用：写出范围和例外。“BACC ranged from 0.929 to 0.938 in the three external cohorts with all classes represented but fell to 0.802 in Cohort X (Fig. 5A; Table 2).”

## 过度解读（规则第 5 节）

| 材料支持的事实 | 避免 | 采用 |
|---|---|---|
| 配对差值 +0.007，3 个 seed 中 2 个区间跨零 | “The proposed model outperformed the black-box model.” | “BACC differences from the black-box model were small; the 95% CI excluded zero for one of three seeds (+0.007) and crossed zero for the other two (Fig. 4C).” |
| PCA 中外部队列与内部分开 | “Device differences caused the domain shift.” | “External cohorts were separated from the internal distribution before classification.” |
| 解释图在病灶区域高亮 | “The model relies on IRF to diagnose edema.” | “Concept evidence for IRF was located over intraretinal cystoid spaces in this example (Fig. 7A).” |
| 两类队列的 BACC | “External three-class validation in Cohort Y achieved …” | “In Cohort Y, which contained two of the three classes, BACC over the observed classes was …” |

## 充分展开但不讨论化（规则第 3、5 节）

- 采用四层顺序：先报告主结果，再给出最有信息量的对比，补充例外或异质性，最后说明该模式对本节研究问题的含义。例如：“Performance was maintained in the three-class cohorts, whereas Cohort X showed a selective decline in class Y (Fig. 5A). The error direction was concentrated in Y-to-Normal assignments rather than distributed across all classes (Fig. 5B). This pattern links the aggregate performance difference to a specific class-level failure, while the cohort-level comparison remains descriptive.” 含义句增加解释时保留；若只重复前两句，则删除。
- 简短稿与详细稿对比（虚构数据）：
  - 简短（约 50 词，信息不足）：“Coverage reached the 90% target in six of seven cohorts; Cohort X was the exception (0.78) (Fig. 8A). Class Y received multiple labels more often (Fig. 8B).”
  - 详细（约 140 词，每句都有新信息）：“Marginal coverage reached the 90% target in six of seven cohorts, with point estimates of 0.91–0.98 (Fig. 8A). Cohort X was the only exception (0.78; 95% CI, 0.76–0.81), and its interval excluded the target. The shortfall occurred in the cohort with the largest classification loss, so the prediction sets missed the true class most often where top-1 errors were also most frequent (Fig. 5A; Fig. 8A). Set size differed by true class: in the internal cohort, singleton sets covered 99% of class Z scans but only 55% of class Y scans (Fig. 8B). Class Y showed the same pattern in the other cohorts (56%–66%), indicating that the cost of coverage was concentrated in the class with the greatest diagnostic overlap rather than spread evenly across classes (Fig. 8B).”
  - 详细稿增加的内容来自区间、例外的位置、跨图对应和跨队列的一致性，没有复述，也没有方法细节。

## 限定并入结果句，不写免责尾句（规则第 5 节）

- 避免（结果后再追一句免责）：“Coverage was 0.781 in Cohort X (Fig. 8A). Empirical coverage did not establish device-level guarantees (Fig. 8A).”
- 采用：“Marginal coverage reached the 90% target in every cohort except Cohort X (0.781; 95% CI, 0.757–0.806) (Fig. 8A).” 设备层面的限定如果大纲要求，在本节只写一次，可放在含义句中。
- 避免（图注式说明搬进正文）：“The pooled matrix represented repeated predictions of the same scans across seeds rather than independent observations.”——这是图注内容，正文删除。

## 长句拆分（journal-style 第 3 节）

- 避免（一句 60 余词，两个比较、两个 CI、方法定义）：“In the binary analysis, abstained scans had an error rate 0.233 higher than retained scans (95% CI, …; P < 0.001; n = …), while scans from unseen devices had a lower abstention rate (difference −0.047; …), and the error definition differed from …”
- 采用：“Abstained scans had a 0.233 higher error rate than retained scans (95% CI, 0.153–0.319) (Supplementary Fig. S6). Scans from unseen devices, however, abstained less often than those from seen devices (difference, −0.047; 95% CI, −0.057 to −0.037).”

## 只引用呈现该结果的 panel（规则第 4 节）

- 避免：“No boundary-order violations were recorded (Fig. 3D).”——Fig. 3D 只显示配对误差，违例计数只在源数据中。
- 处理：改引显示该数值的表格；没有任何图表显示时不写。

## 比例的分母与条件方向（规则第 4 节）

虚构数据：真值 Degeneration 扫描 62,700 次预测中 18,694 次被判为 Normal（行归一化 29.8%）；Degeneration 误分类总计 32,533 次。

- 错误（条件反了）：“29.8% of Degeneration predictions were assigned to Normal.”——29.8% 的分母是真值 Degeneration 扫描，不是“Degeneration 预测”。
- 采用：“29.8% of true Degeneration scans were assigned to Normal (Fig. 5B).”
- 错误（分母含糊）：“Misclassified disease scans went to Normal more often; proportions were 3.7% vs 3.6%.”——3.7%/3.6% 的分母是该真值类的全部扫描；若读者按“误分类子集”理解，对应值应是 50.9% vs 49.1%。
- 采用：“Among all Edema scans, 3.7% were assigned to Normal and 3.6% to Degeneration; among misclassified Edema scans, the two directions were nearly balanced (50.9% vs 49.1%) (Fig. 4A).” 或只保留其中一种口径并写明。

## 复述尾句与独立指引句（规则第 4、5 节）

- 避免：“Recall was lowest for Edema (92.7%) … (Fig. 4A). The error pattern therefore combined high recognition with a tendency to miss disease as Normal.”——尾句只是复述，删除。
- 避免：“… (Supplementary Fig. S5). Performance for all rules is reported in Supplementary Table S5.”——改为在上一句括号中写 “(Supplementary Fig. S5; Supplementary Table S5)”。

## 定位与归因核对（规则第 5 节）

虚构数据：内部基线 0.97；某外部队列 X 中，骨干探针 0.60 → 概念探针 0.80 → 决策头 0.79；队列 Y 中，概念探针 0.95 → 决策头 0.83。

- 大纲写法：“外部掉点发生在决策这一步，以 X 为例。”
- 核对：X 的总差距 0.97 − 0.79 = 0.18，其中决策步只占 0.01，大部分差距在概念层已存在；Y 的决策步占 0.12，才符合大纲的说法。
- 采用：“In Y, BACC fell from 0.95 with a concept-stage probe to 0.83 at the decision head, whereas in X most of the gap to the internal level was already present at the concept stage (0.80 vs 0.79) (Fig. 6A).” 标题改为数据支持的范围，并在核查说明第 1 部分请作者裁决。

## 边界值、口径与脆弱数字（规则第 4 节）

虚构数据。跨队列极值要写全，小样本指标要给 n，同一舍入值的两个量要点明口径。

- 避免（只给一个极值）：“Agreement fell to 0.800 in Cohort X.”——Cohort Z 更低（0.788）。
- 采用：“Agreement fell to 0.79–0.80 in Cohorts Z and X (Supplementary Fig. S9).”
- 避免（脆弱数字当发现）：“Attribution instability detected errors with an AUROC of 0.288.”
- 采用：“Attribution instability detected errors weakly in Cohort Y (AUROC 0.288; 95% CI, 0.09–0.52; 17 errors among 261 scans) (Supplementary Table S10).” 事件数过少时也可只作定性描述，不给数字。
- 避免（同一数字两个含义）：“Internal BACC was 0.948 at clinical-group level (Table 2), and component averaging also gave 0.948 (Supplementary Table S2).”——读者会当成同一个量。
- 采用：“Clinical-group BACC was 0.948 (Table 2), whereas averaging within components gave 0.948 on a different evaluation unit (Supplementary Table S2).”
- 避免（把子集分析写成全局结论）：“The concept probe reached a BACC of 0.800.”
- 采用：“In seed 0, the concept probe reached a BACC of 0.800 (Fig. 6A).”

## 段末阐释句的密度（规则第 5 节）

- 避免（每段都以阐释收尾，句句正确但读起来模式化）：
  “……（结果句）……illustrating the sensitivity of performance summaries to the evaluation unit.”
  “……（结果句）……separating average displacement from the observed frequency of incorrect decisions.”
  “……（结果句）……highlighting the distinction between aggregate inclusion and inclusion within each diagnosis.”
- 采用：每两段最多一段保留阐释尾句，其余段落以结果句结束；同一节内不用同一句式（“illustrating …”“separating …”“highlighting …”）承接尾句。

## 跨图关联与特别发现（规则第 5 节）

虚构数据。回指前文结果时用内容指代，不写节号，也不预告后文。

| 情形 | 避免 | 采用 |
|---|---|---|
| 回指前文结果 | “As shown in Section 3.4, Cohort X had the lowest BACC.”“如 3.4 节所示……” | “Cohort X, which also showed the largest decline in classification performance (Fig. 5A), had the lowest coverage (Fig. 8A).”“分类性能下降最明显的 Cohort X，覆盖率也最低（图 5A；图 8A）。” |
| 节末预告 | “The next section examines where this signal is lost.”“下一节将分析……” | 删除；直接在后文给出该分析的结果。 |
| 特别发现：方向与预期相反 | “Interestingly, unseen-device scans abstained less.” | “Contrary to the expected enrichment, scans from unseen devices abstained less often than those from seen devices (difference, −0.05; 95% CI, −0.06 to −0.04) (Supplementary Fig. S6).” |
| 特别发现：例外队列 | “Notably, Cohort Y was different.” | “Cohort Y departed from this pattern: most of its loss arose between the concept representation and the final decision (0.96 to 0.83), whereas in Cohort X the gap was already present at the concept stage (Fig. 6A).” |
| 两张图的描述性并置 | “The concept shift caused the coverage failure.” | “The cohort with the largest concept shift was not the one with the lowest coverage (Fig. 6B; Fig. 8A), so the two summaries did not rank the cohorts in the same order.” 未检验的关联只写并置，不写原因。 |

- 特别发现靠内容本身提示（方向相反、例外队列、两种指标排序不一致、某一类集中承担代价），而不是靠 Notably、Interestingly、Importantly 这类标签词。

## 含义句的分寸（规则第 5 节）

- 避免（讨论化、外推）：“These findings indicate that the model is ready for clinical deployment across devices.”
- 采用（限于本节问题）：“The interpretable structure therefore did not come at a measurable cost in internal performance.”

## 中文对照：直译与重组（规则第 6 节）

英文：“Most misclassified disease scans were assigned to the normal class rather than to the other disease class (Fig. 4A).”

- 直译（避免）：“大多数被错误分类的疾病扫描被分配到了正常类别，而不是被分配到另一个疾病类别（图 4A）。”
- 重组（采用）：“误分类的病变扫描大多被判为 Normal，而非另一病变类别（图 4A）。”
