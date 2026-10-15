# 期刊语言与格式规范

作者于 2026-10-14 确认。适用于医学 SCI Introduction 的英文正文及中文对照。目标期刊或用户另有要求时，按其要求执行；与本文件冲突时取更严格者。

## 1. 语言

- 美式拼写，全文统一（tumor、edema、modeling、center）；专有名词和引用题名保留原拼写。
- 时态：领域公认事实用一般现在时（Optical coherence tomography is …）；描述具体既往研究用一般过去时或现在完成时（Smith et al. trained …；Several studies have reported …）；本研究的目标和设计用一般现在时或一般过去时，全文一致（Here, we examine … / In this study, we examined …）。
- 缩写在引言首次出现时写全称，只出现一次的术语不缩写；模型、队列和指标名称与 Methods 稿一致。
- 句长：英文单句一般不超过 40 词，硬上限 50 词（冒号或分号引出的列举除外）。
- 不用工程或项目管理词汇（pipeline 作为比喻、audit、ledger、wave、run、frozen endpoint 等内部标识）；不用规则代号、文件名、seed 编号。
- 不用 Methods 内部构造名或分析名（如 target-label-informed reference、signed concept-shift decomposition、representation probe、final readout、soft compartments、clinical-group level）。引言读者还没读 Methods，改用通用说法（“a reference that uses target labels”“which concepts change between cohorts”“the final classification layer”）。模型、数据集的专有名称照常使用。
- 中文对照中，英文术语首次出现时给出通行中文译名（B-scan 写作“B 扫描”），此后统一用中文；数据集、模型等专有名称保留英文。
- 不用宣传性形容词：novel、powerful、robust（作为评价词）、state-of-the-art（无引用支持时）、remarkable、significant（无检验时）。审慎措辞见 `writing-rules.md` 第 4 节。
- 综述层次中以作者名（“X et al.”）或系统名开头的句子不超过三分之一，其余以研究问题、方法类别或发现作主语，作者名放进句中或只用 PMID 指代。
- 避免连续三句以上以 However、Moreover、Furthermore、Additionally 开头的转折或递进；全文每个这类连接词最多两次。

## 2. 引用格式

- 正文引用为纯文本标注，放在所支持论断的句末标点前或所指对象之后：`(PMID: 29474911)`；多篇用分号分隔：`(PMID: 29474911; PMID: 37704728)`。不用 [1]、上标、作者-年份或 Markdown 超链接替代。
- 确无 PMID 的文献，按以下顺序降级：`(DOI: 10.xxxx/xxxx)`；正式出版版本没有 DOI 时用作者、年份及正式出版页 URL，如 `(Koh et al., 2020; URL: https://proceedings.mlr.press/v119/koh20a.html)`；只有预印本、没有正式出版版本时用 `(arXiv: XXXX.XXXXX)`。会议论文通常有 DOI，先确认再考虑 URL。降级引用全部列入核查说明。
- 标识必须属于正文所引的那个版本；不用同一作品其他版本的标识代替。
- 中文对照中引用标识用全角括号：“……（PMID: 29474911）”；多篇用分号分隔。

## 3. 期刊层级（用于文献优先级，不写 IF）

同等相关性下按以下层级优先：

1. 综合医学顶刊：N Engl J Med、Lancet、JAMA、BMJ、Nat Med、Nature、Science、Cell。
2. 领域顶刊与 Lancet/JAMA/Nature 子刊：如 Lancet Digit Health、npj Digit Med、Nat Biomed Eng、Nat Commun、JAMA Ophthalmol、Ophthalmology、Prog Retin Eye Res、Med Image Anal、IEEE Trans Med Imaging、Radiology、J Clin Oncol 等对应领域的主刊。
3. 该领域其他同行评审期刊的原始研究与系统综述。
4. 会议论文与预印本：仅用于方法的原始出处或领域内无期刊版本的关键工作。

- 层级只决定同等相关文献之间的取舍，不为提高层级而引用相关性较弱的文献。
- 不在正文、核查说明或对话中写影响因子数值或分区。

## 4. 篇幅

- 默认约 800–1,000 个英文词，上限 1,000 词；目标期刊或用户给出更严格的限制时以其为准。
- 词数口径：只统计正文段落，不计标题和括号内引用标识（PMID/DOI/URL/arXiv 及作者年份）；用本地脚本按空白分词计数，交付时注明口径。
- 超出上限时先删背景中的教科书内容和综述中的逐篇罗列，再压缩意义段；不删研究空白和本研究问题。

## 5. 文件格式

- 英文稿以 `## Introduction` 为唯一标题，下接各段，段与段之间空一行。中文稿以 `## 引言` 为标题。对照稿按段交替：英文段、中文段。
- 正文不加小标题、列表或加粗。
