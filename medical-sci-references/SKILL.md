---
name: medical-sci-references
description: "Use when a medical manuscript is ready for submission and needs Zotero reference collection, native Word citation fields and a bibliography, or insertion-position checks (参考文献收集与注入、投稿前引用格式化、Zotero 引文字段、参考文献表). Applies after final manuscript assembly, and to standalone main DOCX files."
---

# 参考文献收集与注入

将主稿的 PMID/DOI/arXiv 标识收集进 Zotero，在原位置替换为原生字段，文末加 References 文献表字段。只处理主稿（正文、主图注、主表题表注）。不处理补充材料，不重写正文，不代替写作阶段的证据核验。

## 开始前

完整读 [运行与连接](references/zotero-setup.md)、[收集规则](references/collect-rules.md)、[字段格式](references/field-format.md)、[核对规则](references/verification-rules.md)。[原始需求](references/original-request.md) 保存范围和作者动作。

定位主稿、项目根及 `PROJECT.md`、`口径表.md`、`04_manuscript/作者决定.md`，读取作者决定的通用与 References 节。阶段11须已确认；本项目明确书面先行授权可用 `--authorization <文件>`。无 PROJECT 时必须由作者给输出目录和集合，不新建 PROJECT。集合默认项目标题；References 节若有作者指定集合，优先用 `--collection` 显式传入。

Word 验收的时间点：作者在 **apply 之后的新版主稿**上打开、Zotero Refresh 并确认阶段12；本技能**不要求在 apply 前由作者预检候选稿**。Agent 自己若能启动 Word，可在 apply 前顺手打开候选稿做一次无损检查；**启动失败只如实记录“Word 未自动验证”，不构成 apply 的阻断条件**，也不得用 ZIP 可解析冒充 Word 打开实证。

运行 Python 脚本用 `D:\Anaconda\python.exe -X utf8`；缺少时定位真实解释器，不用 Windows 商店空壳。依赖 Python 3.10+、lxml、python-docx；离线测试另需 Pillow。所有临时文件放显式 `_tmp/`；设 `PYTHONDONTWRITEBYTECODE=1`、TEMP/TMP 指向可写 `_tmp/`。

Zotero 由作者保持运行。**不得自行启动、重启、关闭或改设置。** 连接失败总计试3次、间隔5秒；仍失败记录并继续可离线完成的脚本、夹具、测试、格式说明，连接依赖步骤列待办。不得把连接故障当作整个开发/准备工作的停止条件。实际收集与注入仍须有效库快照。

## 执行

下列命令中的路径均由当前任务填写。`<S>` 为本技能目录，`<P>` 为项目根，`<R>` 为新建过程目录 `_process/References/<日期>_v<N>/`，`<M>` 为当前主稿，`<B>` 为 `<S>/assets/baseline-sample.docx`，`<T>` 为显式可写 `_tmp/`。先运行各脚本 `--help`。

1. `scripts/zotero_collect.py probe --output-dir <R>`：记录就绪状态、读库、版本、无条目写入的能力探测与 connector 落点。认证失败停止写入，不静默换通道。
2. `scripts/extract_citations.py <M> --project-root <P> --output-dir <R>`：按出现顺序抽取、去重，与 finalize 候选及各节核验表交叉核对。重跑字段版加 `--previous-manifest <上一轮引用清单.json>`。
3. `scripts/zotero_collect.py collect --manifest <R>/引用清单.json --project-root <P> --output-dir <R> --collection <集合> --work-dir <T> [--resolve-file <作者映射.json>]`：自动查重、补齐、写入及回查；可选作者映射将指定URL复用到已存在条目，单列“作者指定”、记录来源及WARN；无效key硬错误，不为映射新增条目。映射语义与精确匹配规则见collect-rules；A 不可用时选 B。开发测试显式限制集合，B 落点不符即停下报告，等作者改选；不要自动操作 Zotero UI。
4. **停下汇报并等作者点头**：既有/新增/人工数及作者指定数（若有）、逐条 WARN、将注入字段数（非人工标识处数）、文献表位于 Discussion 后文末。元数据与本地核验材料冲突先裁决。写后失败先用清单回查，禁止直接重发 POST。已经明确授权完整隔离夹具测试时按该授权执行。作者已整体授权一次跑完（含无人值守但获授权的情形）时，跳过交互等待直接继续，并在报告中记为“已获整体授权”。
5. `scripts/inject_zotero_fields.py candidate <M> --manifest <R>/引用清单.json --snapshot <R>/zotero条目快照.json --baseline <B> --candidate <R>/candidate.docx --project-root <P> --approved`：只生成新候选，结果仍显示原标识；不改源稿。缺少主样例拒绝注入；类型样例缺失仅标注 preprint 未经样例验证。
6. `scripts/check_references.py <M> <R>/candidate.docx --manifest <R>/引用清单.json --snapshot <R>/zotero条目快照.json --baseline <B> --gaps <R>/缺口与人工清单.md --output-dir <R>`：ERROR 必须清零，WARN 逐条说明。
7. `scripts/inject_zotero_fields.py apply <M> ...`：用第5步同样参数，只把模式改为 apply；脚本再次核对，归档旧稿，发布版本 N+1，失败回滚。PROJECT 第12行只写“待确认”。apply 的阻断条件只有：核对报告 ERROR、写入或跟踪失败、未经授权；**Word 未能自动打开候选稿不构成阻断**（如实记录即可）。

独立使用：抽取/收集不传 `--project-root`；注入/apply 改传 `--output-dir <作者指定输出目录>`，候选和过程材料均放该目录内。源稿仍需命名 `<项目名>_Manuscript_v<N>.docx`。书面先行授权参数按需同时传给 collect/candidate/apply。字段源重跑给 extract/candidate/check/apply 一致的 previous-manifest。

## 交付与边界

交付新版本主稿、引用清单、Zotero写入报告、条目快照、字段注入报告、核对报告和缺口清单。字段未刷新、文献表待刷新；请作者在 Word 打开新稿、点 Zotero 的 Refresh（引文随即变为编号），再检查至少3处引用及文献表，最后由作者确认阶段12。**作者实测（2026-10-16）：若 Refresh 后文末文献表仍为空，点一次 Zotero 的 Add/Edit Bibliography 即生成**——把这一步写进给作者的验收说明。不能代签或宣称期刊排版、临床/科学支持已验证。重新 finalize 后阶段12置需返工，不改 finalize 检查脚本；字段版以本技能核对器为准。

离线回归：`scripts/test_references.py --work-dir <T> --report <可写路径>/test-results.json`。自测不等于无上下文行为盲测；作者另开全新会话验证技能发现、执行和边界。
