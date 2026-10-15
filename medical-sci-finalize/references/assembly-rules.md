# 组装与项目约定

## 输入契约

路径布局以开发任务书 §2 为默认契约：`04_manuscript/{Introduction,Methods,Results,Discussion,Abstract}/<节名>_EN.md`；`Legends/{Figure_Legends,Supplementary_Figure_Legends,Table_Titles_Notes}_EN.md`；核查说明 `*核查说明.md`；根目录口径表、PROJECT、作者决定和冲突台账。主图 `02_figures/out/figures/main/figN.tif`（**优先**；无 tif 时回退 figN.png 并出 WARN），Fig1 可来自 `03_outline/2_Methods/2.2_Architecture/figures/Fig1.tif`，仅在过程目录转 PNG；附图 `supp/sNN.png`；表 `02_figures/out/tables/{TN,STNN}.md`。不跟随 PROJECT/大纲中的外部路径读取或执行代码。

编号根据当前成稿与资产发现，必须连续且图/表/图注集合精确相等；缺图、重复图注、缺表注都阻断，不能静默跳过。验收应覆盖当前成稿的全部资产（示例：主图 1–8、主表 1–2、附图 S1–S12、附表 ST01–ST10）。图注允许 `**Figure 1. Title.** Body` 或 Markdown 标题；表注为 `**Table 1...**`、`**Supplementary Table S1...**`。表文件必须有一张标准 Markdown 表；原始表说明不替代作者确认的表题表注。CSV/TeX 保留只读，不用来擅自重算。

## 组装清单

主稿：四行占位（标题、作者、单位、通讯，无分页符）→ 摘要（Abstract 下连续四段 run-in：加粗 `Background:`/`Methods:`/`Results:`/`Conclusions:` 标签 + 同段正文，段间不空行）→ Keywords → Highlights → Introduction → Methods → Results → Discussion，不输出 References。主图、主表置于首次正文引用所属（子）节末，下一个同级/更高标题之前；同节按首次引用位置混排。图后接完整图注，表题→单表→表注；一级节及资产块边界各一个空段落。所有标题为 Normal + 直接格式，无 Heading/Title 或大纲级别。正文和原始引用格式保持；`Supplementary Table S1` 不得误作主表 `Table 1`。细则见 journal-style.md。

补充材料：Supplementary material 标题 → 附图 S1–S12 按编号自然流式配图注 → 附表 ST01–ST10 按编号配表题表注，每表一个 w:tbl。8→7.5→7→6.5 pt；地板仍超词宽允许词内断行并 WARN。单节 A4 纵向，不强制每图或每表分页。数值和空值照源表保留，空白不改为零。

引用标识按正文、图表注首次出现去重，仅输出过程文件 `参考文献候选清单.md`。采用本地核查表已有字段及行级溯源，缺失字段、无记录和未核验逐条标注，不列入成品 WARN。正文保留 PMID/DOI/URL/arXiv，不另编号、不伪造书目或核验。过程文件另有 `表格断行清单.md`，逐表列字号与估算断词列/样例。两份清单均不是投稿正文。

## 输出、重跑与归档

有 PROJECT.md：两份文件固定在 `05_final/<项目名>_{Manuscript,Supplementary}_v<N>.docx`；过程文件 `_process/Finalize/<日期>_assembly_v<N>/`，包含 assembly_manifest.json、裁决清单；PROJECT 第 11 行记录待验收状态，作者决定的 Finalize 节保存已确认的固定约定。单独 `--kind main/supp` 不更新完整阶段状态。

无 PROJECT.md：必须指定 `--output-dir`；过程目录在输出目录内 `_process/<日期>_assembly_v<N>/`，不生成或杜撰 PROJECT 状态。脚本仍要求输入采用本节布局；不同项目需先在授权范围内整理副本。

同输入、同版本输出字节确定（固定 ZIP 时间戳、固定元数据、稳定排序）；重跑同内容不重复归档。不同内容覆盖同版本前，旧文件保留到 `_archive/<日期>/<原相对目录>/<原名>_<sha12>.docx`，推荐始终递增版本。上游图表/大纲/数据绝不修改。阶段二只有 EN 成稿允许在完整归档后覆盖；候选树与改前树不能重合。ZH/EN_ZH 文件不进入覆盖清单。过程文件不是投稿正文。

## 完成条件

运行构建、check_finalize 和既有一致性脚本；所有 ERROR 消除。打开/渲染两份 Word 并核对节末插入、自然分页、单表跨页、表宽和公式；确认没有行号及页码。WARN 和未决项目逐条说明；作者信息、引用核验、文献表、伦理/披露等仍需处理，不能宣称投稿就绪。完整成稿可组装，但不把待确认章节或旧冲突标为已解决。
