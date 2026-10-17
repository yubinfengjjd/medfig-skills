---
name: medical-sci-finalize
description: Use when a complete medical SCI manuscript needs final Word assembly and whole-manuscript English polishing or conservative removal of defensive writing, after Methods, Results, legends, Introduction, Discussion and Abstract are complete. Not for individual section drafting, research planning, or generating new results.
---

# medical-sci-finalize

流水线第 11 步，一个技能两个阶段：组装主稿与补充材料 Word；随后逐段润色全部英文并重新组装。中文不动。不用于单个章节写作、研究计划、补做分析或重绘图表。

## 入口与硬门槛

先读 [原始要求与确认选择](references/original-finalize-prompt.md)。确认项目根、版本及阶段；已有明确指令直接执行，不重复访谈。仅有完整的 Methods、Results、图注、Introduction、Discussion、Abstract 时开始；缺任一类停止并列缺项。“完整成稿”和“作者已确认”分开：保留 PROJECT.md 中待确认状态，不能把文件存在或脚本通过当作作者同意。读取口径表、作者决定、冲突台账，沿用所有未决事项。

全程本地离线，不联网，不派子代理，不调用 ARS 流水线或 humanizer。参考规则已经静态并入 references。所有 Python 命令用 `python -X utf8` 运行（PATH 上的 `python` 若是 Windows 商店空壳，改用真实解释器的完整路径）。开发/盲测时先复制获准材料到隔离工作目录；绝不把开发操作指向原项目或已安装技能目录。

## 阶段一：组装

阅读 [组装规则](references/assembly-rules.md) 和 [Word 版式](references/journal-style.md)。运行 `scripts/build_manuscript.py --project-root <项目根> --kind both --version <N>`。没有 PROJECT.md 时另传 `--output-dir`；有则固定输出 `05_final/`。

运行 `scripts/check_finalize.py --project-root <项目根> --version <N> --report <过程目录>/assembly_check.json`。批次 #10 使用新版本 v7，真实项目旧 v6 的归档由获授权的发布阶段执行，开发只构建隔离副本。默认单节 A4 纵向、Arial 12 pt 单倍行距，无行号及页眉页脚。主图表放在首次正文引用所属（子）节末、下一个同级或更高标题前；同节按首次引用顺序混排。图片满宽 14.6 cm 自然流式；表键优先取 Markdown 首行的显示编号，并核对同名 .source.json 的 presentation_trim.display_number；无显示标题才回退文件名，重复编号报错。同一表号可含多个 Markdown 表格区块，共用一次表题表注，区块间一个空段，各块独立布局与记录（含区块序号、N blocks）；单区块保持原输出。8→7.5→7→6.5 pt，地板仍超词宽时允许词内断行并 WARN。全部标题用 Normal 段落加直接格式，无 Heading/Title 样式及大纲级别；一级节与资产块间按规则留一个 Arial 12 pt 空段落，详见 Word 版式。

主稿不输出 References，正文引用标识原样保留。过程目录同时生成 `表格断行清单.md`（逐表字号、断词列与样例）及 `参考文献候选清单.md`（首次出现顺序、已有字段、缺口）；书目缺失与未核验只进入候选清单，不进入成品 WARN。必须实际打开两份 DOCX；可用本机 Word 或渲染器检查自然分页、图片、跨页表、公式及标题块。不得只凭 ZIP/XML 可解析宣称视觉验收通过。ERROR 阻断发布；WARN 逐条登记；组装检查 JSON 的 `style` 附全稿及逐节风格统计，含主/附图注与表注；直接复用 medpaper-pipeline 的检查函数，缺少依赖时明确报错。统计只读，不在组装时改写源稿。组装检查对列数 >10 或存在 >50 字符单元格的表追加发表形态 WARN，列出表号与列名（长单元格另报行号与长度；表注除外），提示按设计规则精简。此项只读提示，不改源表、组装、排版、原有 ERROR 或退出码语义。候选清单不证明文献已经核验，也不代表投稿就绪。无需改上游即可修复的排版问题在组装脚本中修复。

## 阶段二：润色、归档、重新组装

阅读 [润色规则](references/polish-rules.md) 与 [判断示例](references/examples.md)。润色由当前代理逐段完成，脚本只执行确定性检查与归档覆盖，不会自动润色或自动删句。

1. 将 `04_manuscript` 的全部 `*_EN.md` 复制到过程目录的候选树，保持相对路径；保存改前快照与 SHA256。英文范围包括四节正文、Abstract（含 Keywords/Highlights）、主/附图图注、全部表题表注。不得修改 ZH、EN_ZH、02_figures、03_outline、数据和源表。
2. 建立 `protected.json`：逐文件列出原文的术语、队列/类别/模块名、统计口径、全部限定、局限和不利结果的关键句，以及带单位、范围和分析归属的关键数字。按 polish-rules 第 2 步，将关键限定与数字同补充图注、全部表题表注和各节核查说明实际交叉核对并留证。默认正则并不穷尽这些内容；逐段人工复核不能省。保护词必须来自原文，数字、单位、引用标识、图表编号和公式零改动。
3. 写候选清稿、逐段修改记录 `changes.json`、可读 `修改记录.md`，保存 `crosscheck.json` 后，用 `scripts/generate_polish_records.py` 生成三层 `作者裁决清单.md` 与完整 `附录_交叉核对审计.md`（呈现分组与命令见 polish-rules“记录呈现生成”）。每个改动块必须有原段→改段、位置、理由；无变化段保留。按 polish-rules 第 3 步记录交叉核对的执行覆盖与结果；材料不能支持的差异列“来源待查”，证据不足时明确“无法证明缺失”，保留原文、不擅补删。结构性覆盖缺口只归组计数，真正需作者动作才进入本轮问题；既有事项保留。未采用建议另列裁决，不进入清稿。
4. 用 `check_finalize.py --before <原04_manuscript> --after <候选树> --protected-json <json> --changes <json> --report <json>` 核验。ERROR 必须修复；各文件数字多重集、符号、单位、引用、图表标识、限定逐项一致；各节词数相对改前 ±10%，同时检查绝对目标，不能用其他章节抵消。
5. 检查通过后才加 `--apply --project-root <根> --decisions <清单>`。脚本先将全部变化 EN 原件归档到 `_archive/<日期>/04_manuscript/...` 并核对字节，再原子替换；I/O 失败回滚。不手动跳过归档。保留 JSON/Markdown 修改记录和裁决清单在 `_process/Finalize/<日期>_polish_v<N>/`。
6. 按下面顺序运行既有检查器：`medpaper-pipeline/scripts/consistency_check.py <项目根>`；然后 `manuscript_check.py <methods|legends|results|introduction|discussion> <EN稿> --zh <ZH稿>`，逐节执行，Results 依赖按该脚本参数传入。检查脚本只读调用，不改其安装文件。ERROR 修复，WARN 逐条说明；中文不因英文润色而自动同步。Abstract 另由本技能检查字数和证据。
7. 用递增版本重新组装与检查两份 Word。更新 PROJECT.md 第 11 行为“已润色，待作者验收”，记录实际版本/路径；仅作者明确验收后才写已确认。作者新增裁决只追加 `作者决定.md` 的 `## Finalize`，不改旧决定。不要将候选建议写成作者决定。

机械检查不证明事实未变、临床有效性、语义等价或期刊特定投稿合规；逐段证据核对、所有不利结果及局限保留、视觉验收与作者裁决均需独立完成。

## 交付前检查

- [ ] 散文分号链 0 处（同句 ≥2 个散文分号为 ERROR，结构性分号豁免）；目标平均 18–28 词/句，一般 ≤45 词、硬上限 60 词，>45 词占比 >10% 为 WARN；无连续 ≥3 个 <8 词短句的电报体连跑；WARN 已逐条说明。连接词按逻辑需要使用，不连续三句以上以同一个连接词或短语开头；按 journal-style 的「句长、分号与衔接」复核。
