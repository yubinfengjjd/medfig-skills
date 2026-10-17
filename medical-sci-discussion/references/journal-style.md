# 期刊语言与格式规范

作者于 2026-10-14 确认。适用于医学 SCI Discussion 的英文正文及中文对照。目标期刊或用户另有要求时，按其要求执行；与本文件冲突时取更严格者。

## 1. 语言

- 美式拼写，全文统一（tumor、edema、modeling、center）；专有名词和引用题名保留原拼写。
- 时态：本研究的发现用一般过去时（the model retained …；accuracy was lower on …）；对发现的解释和公认事实用一般现在时（this suggests …；OCT is …）；描述既往研究用一般过去时或现在完成时（Smith et al. reported …；Several studies have shown …）。
- 缩写与 Methods、Introduction 一致；Discussion 中不重新定义已定义过的缩写，期刊要求各节重新定义时除外。模型、队列、指标和分析的名称与 Methods、Results 及口径表一致，不另起名称。
- 句长和分号按下方「句长、分号与衔接」执行。
- 不用工程或项目管理词汇（pipeline 作为比喻、audit、ledger、wave、run、frozen endpoint 等内部标识）；不用规则代号、文件名、seed 编号、代码变量名。
- 不用宣传性形容词：novel、powerful、robust（作为评价词）、state-of-the-art（无引用支持时）、remarkable、excellent、significant（无统计检验时）。推断强度见 `writing-rules.md` 第 4 节。
- 以 “Our results/findings” 或 “We found” 开头的句子全文不超过 4 句；以作者名（“X et al.”）开头的句子不超过文献对比句的三分之一。
- 衔接按下方「句长、分号与衔接」执行；取消连接词全文次数死限。
- 中文对照中，英文术语首次出现时给出通行中文译名，此后统一用中文；数据集、模型等专有名称保留英文。

## 2. 引用格式

- 正文引用为纯文本标注，放在所支持论断的句末标点前或所指对象之后：`(PMID: 29474911)`；多篇用分号分隔：`(PMID: 29474911; PMID: 37704728)`。不用 [1]、上标、作者-年份或 Markdown 超链接替代。作者指定其他引用格式时按作者要求。
- 确无 PMID 的文献，按以下顺序降级：`(DOI: 10.xxxx/xxxx)`；正式出版版本没有 DOI 时用作者、年份及正式出版页 URL，如 `(Koh et al., 2020; URL: https://proceedings.mlr.press/v119/koh20a.html)`；只有预印本时用 `(arXiv: XXXX.XXXXX)`。降级引用全部列入核查说明。
- 引用本文自己的图表用 `(Fig. 3b)`、`(Supplementary Fig. S5)`、`(Table 2)`，写法与 Results 稿一致；Discussion 引本文图表的次数宜少，只在解释直接依赖某个 panel 时引用。
- 缺口占位只用 `[citation needed]`（`writing-rules.md` 第 8 节），不用其他形式。
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

- 默认约 800–1,500 个英文词（含结论段）；研究问题少、发现集中时取下限附近。目标期刊或用户给出更严格的限制时以其为准。
- 词数口径：只统计正文段落，不计标题和括号内引用标识（PMID/DOI/URL/arXiv 及作者年份）与本文图表引用；用本地脚本按空白分词计数，交付时注明口径。
- 超出上限时先删复述 Results 的句子和一句带过的次要发现，再压缩总结段；不删核心发现的文献对比和局限。

## 5. 文件格式

- 英文稿以 `## Discussion` 为唯一标题，下接各段，段与段之间空一行；结论段是最后一段，不加标题。作者或期刊要求独立 Conclusions 时，另起 `## Conclusions`。中文稿以 `## 讨论`（及 `## 结论`）为标题。对照稿按段交替：英文段、中文段。
- 默认正文不加小标题、列表或加粗；作者或期刊要求小标题时用 `###`。

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
