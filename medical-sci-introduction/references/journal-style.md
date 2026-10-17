# 期刊语言与格式规范

作者于 2026-10-14 确认。适用于医学 SCI Introduction 的英文正文及中文对照。目标期刊或用户另有要求时，按其要求执行；与本文件冲突时取更严格者。

## 1. 语言

- 美式拼写，全文统一（tumor、edema、modeling、center）；专有名词和引用题名保留原拼写。
- 时态：领域公认事实用一般现在时（Optical coherence tomography is …）；描述具体既往研究用一般过去时或现在完成时（Smith et al. trained …；Several studies have reported …）；本研究的目标和设计用一般现在时或一般过去时，全文一致（Here, we examine … / In this study, we examined …）。
- 缩写在引言首次出现时写全称，只出现一次的术语不缩写；模型、队列和指标名称与 Methods 稿一致。
- 句长和分号按下方「句长、分号与衔接」执行。
- 不用工程或项目管理词汇（pipeline 作为比喻、audit、ledger、wave、run、frozen endpoint 等内部标识）；不用规则代号、文件名、seed 编号。
- 不用 Methods 内部构造名或分析名（如 target-label-informed reference、signed concept-shift decomposition、representation probe、final readout、soft compartments、clinical-group level）。引言读者还没读 Methods，改用通用说法（“a reference that uses target labels”“which concepts change between cohorts”“the final classification layer”）。模型、数据集的专有名称照常使用。
- 中文对照中，英文术语首次出现时给出通行中文译名（B-scan 写作“B 扫描”），此后统一用中文；数据集、模型等专有名称保留英文。
- 不用宣传性形容词：novel、powerful、robust（作为评价词）、state-of-the-art（无引用支持时）、remarkable、significant（无检验时）。审慎措辞见 `writing-rules.md` 第 4 节。
- 综述层次中以作者名（“X et al.”）或系统名开头的句子不超过三分之一，其余以研究问题、方法类别或发现作主语，作者名放进句中或只用 PMID 指代。
- 衔接按下方「句长、分号与衔接」执行；取消连接词全文次数死限。

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

- 默认约 900–1,100 个英文词，上限 1,200 词；目标期刊或用户给出更严格的限制时以其为准。
- 词数口径：只统计正文段落，不计标题和括号内引用标识（PMID/DOI/URL/arXiv 及作者年份）；用本地脚本按空白分词计数，交付时注明口径。
- 超出上限时先删背景中的教科书内容和综述中的逐篇罗列，再压缩意义段；不删研究空白和本研究问题。

## 5. 文件格式

- 英文稿以 `## Introduction` 为唯一标题，下接各段，段与段之间空一行。中文稿以 `## 引言` 为标题。对照稿按段交替：英文段、中文段。
- 正文不加小标题、列表或加粗。

## 句长、分号与衔接

**句长**
- 目标平均 18–28 词/句；单句一般不超过 45 词，**硬上限 60 词**（任何单句不得例外）。
- 避免电报体：不连续出现 <8 词的短句；不得用"增加句子数"回避必要的从句结构，也不得为凑篇幅拉长句子。
- 超过 45 词的句子占全文句数 >10% 时 WARN；任何 >60 词 = ERROR。

**分号**
- 散文分号只允许用于**同一命题的紧密补充**（同一论断的定义、限定或统计注释）。
- **禁止分号链**：同一句内出现 ≥2 个散文分号（无论并列发现还是清单式列举）必须改写——拆为独立句，或改用并列/从属连词（and/but/whereas/because 等），或把清单写成紧凑并列（"we assessed A, B, and C"）。散文分号链 ≥1 处 = ERROR。
- **结构性分号不受限**：缩写表（"BACC, balanced accuracy; CI, confidence interval."）、统计量括号（"(ρ = 0.743; 95% CI, 0.619–0.804)"）、引用列表（"(PMID: 29474911; PMID: 37704728)"）、表格注的缩写行。

**衔接与生动（逻辑性）**
- 主动用连词与从属结构表达因果（because/thus/therefore）、对比（whereas/by contrast）、让步（although/even so）、递进（moreover/in addition）；句子内部用从句承载层次，而非用分号堆叠。
- 每段以主题句领起；段末句引出下一节点（与引言/讨论既有结构规则一致）。
- 不连续三句以上以同一个连接词或短语开头；连接词按逻辑需要选用，不为凑数堆砌。
- 仍禁：修辞性、宣传性形容词与无证据的强调（沿用 journal-style 既有清单）；口语化与演讲腔。
