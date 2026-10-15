# 已确认的图注写作规则

本文件细化基础提示词 `original-legend-prompt.md`，适用于医学研究的主图、附图和表格。两者冲突时以本文件为准；当前用户指令优先于本技能。语言与格式见 `journal-style.md`，判断示例见 `examples.md`。每条规则只在一处定义，其他文件只引用对应位置。

## 1. 材料与事实来源

| 材料 | 用途 |
|---|---|
| 写作大纲（Results 各节的“图 / 表”说明、写作要点、措辞边界；图表引用清单） | 决定要写哪些图表、每个 panel 的科学问题、重点与表述边界 |
| 成图（PNG/SVG） | 唯一的图面依据：panel 字母、实际显示的对象、可见的分布/趋势/差异、图内标注和符号 |
| 详细图注（如 `captions/*.md`）、源数据（如 `*.source.json`）、表格（csv/md） | 数字基准：n、估计值、区间、比例、分母；核对图中标注的数值 |
| 已有图注（修订模式，用户提供时） | 修订对象；保留作者已确认的措辞，只改违反本规则或与数据冲突之处 |
| Methods 稿（如有） | 只用于对齐模型、队列、指标名称和缩写，不把方法细节搬进图注 |
| 作者决定记录（如 `Legends_作者决定.md`，存在时） | 已裁决事项直接沿用，不再上报 |

- 不读取 Results 稿。图注先于 Results 定稿，避免把正文的结果分析搬进图注。
- 详细图注是给作者看的绘图与数据记录（配色代码、文件名、抽样规则、排除流程），不是图注草稿。只从中取数字和对象定义，不沿用其句子。
- 每个 panel 写之前先用图像查看工具打开成图，确认字母、内容和图内实际标出的数值。打开失败（路径错误等）时，用目录列出的完整绝对路径重试，不跳过；确实无法查看的图在核查说明中列出。成图不一定都在 Results 目录：示意图或外部绘制的图可能在方法节目录（如 `2_Methods/2.2_Architecture/figures/Fig1.tif`），找不到时按图号在项目内检索文件，并在核查说明中写明实际路径。只在源数据中有、图上没显示的数值，原则上不写进图注；理解该 panel 必需（如 n、主要估计值）时可写，并核对出处。
- 详细图注不是权威：它记录的是出图时的描述，可能写错拟合划分、分析归属或量的定义。涉及"拟合在哪个分区""某个量的定义""某 panel 属于哪个分析"时，回代码或回执（source.json 的 inputs、configs、ledger 键）核对，与详细图注冲突时以代码/回执为准，并把冲突写入核查说明。图中与图上标注的口径（百分比或比例）以图面为准。
- 大纲与数据冲突、详细图注与成图冲突、panel 字母与大纲不一致时，图注以成图和数据为准，并按第 9 节上报。
- 大纲列出但没有成图的图（如“外部绘制，待交付”），不凭大纲虚构图注，在核查说明中列出。

## 2. 结构与标题

- 每张图一个图注段落：`图编号 + 标题`，紧接各 panel 描述，最后是尾注（第 5 节）。整段不换行、不插空行；相邻两张图之间也不留空行。
- 标题为描述性名词短语，概括该图比较的对象和主题，不写成陈述发现的句子（“Boundary accuracy of the learned front end and graph search”，不写 “The learned front end is more accurate than graph search”）。一般不超过 15 个英文词，不加模型宣传性修饰。
- 只有一个 panel 的图不写 `(A)`，标题后直接写描述。
- 多 panel 图按字母顺序描述；合并组按第 4 节写。所有在成图中出现的 panel 都必须被覆盖，不得遗漏或新增。

## 3. Panel 描述

- 长度：每个独立 panel 或合并组 1–2 句，最多 4 句（图注精简原则为最高优先级）。示意图、示例病例或流程图 1 句说明其构成与作用即可。
- 信息：自然融合“图形或比较对象 + 一项以上可见证据（分布集中区间、组间高低、离散程度、趋势方向、与参考线的关系、聚集/重叠）+ 证据直接支持的有限含义”。这是信息要求，不是固定句式；含义不强制，只在图面直接支持时加。
- 不能只写“展示什么”（“(C) Box plots of Dice scores.”），也不能只写空泛结论（“(C) Dice scores indicate high accuracy.”）。承担定量比较的 panel 至少保留一项具体的图上模式或一个关键数字。
- 数字有选择地写，图注不是表格转述：每个描述单元一般不超过 3 个数值，其中带区间的估计不超过 2 个。只写理解该 panel 必需的数字：主要估计值及区间、预设界值、最弱或例外项、范围。多个队列、类别、种子或对比的数值，写范围、极值或例外（“0.802 in Cohort B versus 0.929–0.938 in the other three-class cohorts”），不逐个列出；完整数值留给表格。不复述 Results 式的逐组差异分析。
- 比较两个量级时写出这对数字，不写“两者相近/重叠”这类判断：不写 “Mean shift norms overlap the range of decision margins”（写 “The mean shift norm in one cohort, 3.12, is close to the internal median margin, 2.96”）。
- 压缩时不用 some、several、many、a few 等模糊量词代替证据（“lie near some median margins”“higher in several cohorts”），写出具体的队列、类别名或一个数字（“the Cohort D mean shift norm, 3.12, is close to the internal median margin, 2.96”）。
- 数值格式跟随图面：图上标为百分比就写百分比，标为 0–1 比例就写比例；同一图注内同一指标格式一致。
- 主语和动词随图变化：可以用图形类型、比较对象、分布特征或结果作主语。相邻 panel 不重复同一开头（“Violin plots show …”“Analysis of …”“Distribution of …”“Showing …”），不逐句套用 reveal/indicate/demonstrate。
- 时态：描述图面内容用一般现在时（“errors cluster below …”“curves decline …”）。
- 不写方法实施细节：抽样规则、拟合流程、bootstrap 方案、阈值选择过程、软件和文件名交给 Methods。允许的方法信息只限于读懂该 panel 必需的分析单位或子集，用短语交代（“fitted on internal test scans only”“at scan level”“across three seeds”）。
- 不写内部标识：字段名、文件名、运行编号、标签版本、规则代号和项目流程用语（如 `valid__e2`、frozen endpoint、stored-ambiguous-label rule、reporting gate、rule 4、K=7 arm、seed-0、`seed0.json`），改为科学名称或描述性说法（“the prespecified endpoint”“concepts meeting the prespecified AUROC threshold”“in one seed”）。图面上印有规则编号时，可在括号中保留编号，但先给描述性名称。也不写只有作者能懂的实现性说法（“the decomposition closes algebraically”改为 “contributions sum exactly to the margin”）。
- 不评价图表质量或结果可靠性，不写分辨率、配色代码、透明度等绘图参数（颜色和符号的必要说明见第 5 节）。

## 4. 合并描述

- 多个 panel 图形相同或相近、共享比较对象、回答同一科学问题且主要趋势一致时，优先合并：连续 panel 写 `(A–C)`，不连续写 `(B, D)`。编号必须与图面一致，中英文的合并范围一致。
- 合并后先写共同模式，必要时补充最重要的一项跨 panel 差异（如最弱类别的范围），不在一句里依次重述每个小图。
- 图形相同但条件不同、差异本身有科学意义时，不合并；不同图形但共同构成一个论证时，可在不丢信息的前提下合并。
- 合并只为消除重复和突出层次，不为追求最少句数；不得编造对所有 panel 都成立的结论。

## 5. 尾注

尾注接在最后一个 panel 描述之后，同一段内，按以下顺序只写需要的项，整体一般不超过三句：

1. 读图必需的符号与颜色：参考线（“Dashed line, identity”“Dotted line, 90% nominal coverage”）、标记含义（“† …”“outlined cases are misclassified”）、颜色仅在图内无图例或图例不自明时说明（“Colors denote true class”）。不写色号、透明度、线宽。
2. 统计量含义：误差线或区间是什么（“Error bars, 95% CIs”“Points, seed means; bars, min–max across three seeds”），n 的单位（scans、eyes、participants），显著性标记的含义（`*P < 0.05, **P < 0.01, ***P < 0.001`，仅当图中实际有标记）和对应检验名称（“two-sided Wilcoxon signed-rank test”）。不写计算过程、重抽样次数或数据来源。
3. 缩写：该图注中出现的全部缩写，按出现顺序写在最后一句，格式见 `journal-style.md` 第 3 节。每个图注独立定义，不依赖其他图注或正文。
4. 大纲措辞边界要求在图注中出现的限定（如“两个队列共享重复图像，不是独立复现”），按需用 † 等标记接在相应 panel 或尾注中，每图只写一次。写成简短的事实短语（“Coverage is empirical at scan level.”“Review budgets are retrospective.”），不写成否定式清单（“support no clinical operating-threshold, workflow-benefit, or reader-performance conclusion”）。

## 6. 解读边界

- 大纲“措辞边界”与图注相关的条目逐条遵守，是硬约束；必须交代的限定（如轮廓为模型预测而非人工标注）写进对应 panel，不放进讨论式句子。
- 显著性：图中或材料中没有对应检验时，不写 significant、significantly；用 higher、lower、more variable、closely aligned、comparable 等中性措辞。非劣效、达到名义覆盖等有预设界值的判断，只在数值和界值都有出处时写，并写出界值。
- 比较的方向用 positive、negative、higher、lower 描述。不写 favor、favoring、advantage 及其中文对应“偏向、有利于、更优”：不写 “Paired BACC differences favor the proposed model in one seed”（写 “Paired BACC differences are positive in one seed”），不写“差值偏向本模型”（写“差值为正”）。
- 不写 superior、outperformed、better（无检验支持时），不写因果、机制、临床价值或泛化结论；不把相关、共现、降维分布或解释图写成机制证据；不把代理指标写成真实终点。
- 只有部分类别的队列、非独立队列、使用目标标签的参照等，在相应 panel 中用短语如实限定一次，不堆叠；只写在该限定确实影响读图的 panel 或尾注，不在无关 panel 中重复。
- 限定只有两个来源：大纲措辞边界中与该图相关的条目，以及读图必需的定义（如“轮廓为模型预测”“oracle 使用目标标签”）。每张图最多一句独立的限定句，其余并入 panel 短语。不写通用免责句：“these curves are descriptive”“do not establish a model ranking”“the overall result is mixed and not significant”“not a clinical report”“does not define an operating threshold”。没有检验就用中性措辞描述结果本身，不用免责句补救。
- 不使用宣传性词汇：remarkable、striking、excellent、robust（作评价）、clearly、显著优异。

## 7. 表格标题与表注

- 表格标题：`Table 1.` 加描述性标题，写明表格内容、对象和单位层级（如 “… by cohort and analysis unit”），不写发现，一般不超过 15 个英文词，不逐个列出表中各列。
- 表注放在表格下方，一个段落，按以下顺序只写需要的项：数值的含义（“Values are means with min–max across three seeds”“95% CIs are …”）→ 符号与占位（“—, class absent”“†, …”）→ 读表必需的限定（部分类别队列、非独立队列）→ 缩写。
- 表注不重复表头已经写明的信息，不写结果解读，不写方法流程。表格内容本身（列名、数值）不改动；发现列名中有内部标识或与图注术语不一致时，在核查说明中上报，不擅自改表。

## 8. 中英对照

- 英文为正式图注；中文对照按中文学术语序重组，事实、数值、限定、panel 编号和合并范围逐句一致，不增删信息。
- 避免“被……所”“对……进行……”“……的……的……”堆叠；中文标题同样是描述性名词短语。
- 图面上的类别、分带和队列标签（如 Normal、Edema、RPE/drusen）在中文稿中保持英文原样，全文一致，不在同一稿中混用“正常”与“Normal”；英文中的 seed 写作“种子”，“seed 0”写作“种子 0”。
- 专有名称（数据集、模型、软件）保留英文；通用术语首次出现用通行中文译名（B-scan 写作“B 扫描”）；指标缩写可保留英文，中文尾注同样给出缩写释义（“BACC，平衡准确率”）。
- 模型、队列、类别和指标名称与 Methods 稿一致；Methods 与大纲或详细图注用名不同时，统一用 Methods 的名称，并在核查说明中注明。

## 9. 核查说明

出现以下任一情况时输出核查说明，否则在交付时说明“未触发”：

1. 大纲、详细图注与成图或数据冲突（panel 字母、数值、对象）。
2. 大纲列出但无成图的图表，或成图中有大纲未提的 panel。
3. 大纲措辞边界与数据不完全相符，图注已按数据收窄。
4. 名称不一致（Methods、大纲、详细图注、表格列名之间）。
5. 修订模式下改动了作者原有的数字或限定。

## 10. 材料冲突：以谁为准

写作时最常遇到六类冲突，按此顺序判定，判定过程写入核查说明：

| 冲突 | 以谁为准 | 怎么查 |
|---|---|---|
| 拟合在哪个数据划分（探针、偏置、阈值） | 代码与回执 | 找到计算函数与调用处（如 `information_loss_ladder(cal, ...)`、`cal = stores["calib"]`），看 `n_fit`/`n calibration` 与哪一分区规模一致 |
| 某个量的定义（概率、分数/logit、负荷、均值是否有权重） | 代码 | 看预测存储的注释与生成函数（如 `# (N, C) logits`）；训练期量与图内分析量常常不是同一个 |
| 某 panel 或图属于哪个分析（哪个端点、哪次分析） | 图的源数据 inputs 与回执键 | 读 `*.source.json` 的 inputs 清单、ledger 键与运行回执，不按图名推断 |
| 规则编号、阶段数、内部代号 | 代码/配置键 | 代号（R0–R5、no_d2、gate 等）先写科学名称，编号只作括注；"5 个阶段"要数清探针数与模型输出 |
| 队列名、指标拼写、表头 | Methods 稿 | 统一为 Methods 名称（Cohort B、Cohort C、BACC）；表格标签的改动在生成侧完成，图注引用改后名称，数字不动 |
| panel 字母大小写 | 图面 | 打开成图看是大写还是小写，全稿一致；与图面不符先上报 |

- 大纲写"待交付""见 Table X"的项，先检索项目内是否已有成图或表；存在就写，不存在才在核查说明中列出。
- 表注或图注里出现的内部名称（配置键、消融代号、规则代号）一律换成科学描述，必要时在括号里保留代号。

核查说明只含两部分：需要作者裁决的事项（每条写出位置、原文、改后或建议、依据）；数字出处表（只列需要说明来源的数字，如从源数据换算、图面与详细图注不一致或图面未标出的数字，写到具体文件和字段）。不写合规声明（“已遵守措辞边界”“术语已统一”“未修改数据”），不按目录笼统列出处。一般不超过一页。
