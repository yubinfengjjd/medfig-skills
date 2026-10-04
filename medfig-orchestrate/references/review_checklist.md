# 出图审查清单（review checklist）

供 medfig-orchestrate 自己的 task reviewer 与终审使用：可以把这份文件单独交给审查子代理，审一张图或一整套图。
不依赖 medfig 的其他文件；提到 figkit 的地方，换成项目自己的导出/QA 工具同样适用。

## 审查输入（缺一项就在报告里写"无法核实"）
- 规格 spec（绑定权威）与该图/表的规格段落
- 任务 brief（仅作参考；与 spec 冲突时以 spec 为准）
- 实现 diff 或脚本、测试文件、`<name>.source.json`（provenance）、QA 结果
- 图注草稿

## 严重度
- Critical：违反完整性红线或数字错误，会误导读者 → 必须修
- Important：违反 spec、缺必要声明、QA 门被绕过 → 必须修
- Minor：可读性、代码整洁 → 记台账 deferred，便宜时顺手修

每条发现写：位置（file:line 或 panel 字母）、问题、依据（spec 段落 / 本清单编号）、具体修法。

## 1. Spec 绑定
- [ ] 每个 panel 的内容、分层（如 队列 × 真实类别）、编码与 spec 一致；brief 写得少不是理由
- [ ] 有理由的偏离（尺寸、换行、改编码）已写成 Ruling，并会进交付"偏离"清单
- [ ] 一 panel 一结论；图型与 spec 的选型理由一致

## 2. 影像完整性红线
- [ ] 影像保持原生纵横比（aspect equal + 留白），不拉伸、不裁掉内容
- [ ] 掩膜/分割不缩放插值；上游若已重采样，图注说明
- [ ] 多张显著性图/CAM 共用同一色阶；不对极小值图做 per-image 放大（避免把噪声画成证据）
- [ ] 共享色阶下限为负时，≤ 0 的区域透明，图注说明只显示正激活
- [ ] 比例尺只画有文档依据的轴；预测轮廓与金标准轮廓都标明来源
- [ ] 结构性零 / 缺失类用斜线阴影或 n/a 标注，不画成 0

## 3. 数字
- [ ] 图中和图注里的每个 n、估计值、区间都由数据计算，脚本里没有写死的展示数字（字面值只出现在断言里）
- [ ] provenance 的 `values` 与数值锚点测试一致；同一队列在所有图注中的 n 一致，不一致处有代码计算并断言的差额与说明
- [ ] 区间注明类型（95% CI / SD / IQR）、n、bootstrap 方式与单位（scan / eye / 患者 / 组）
- [ ] 共享组件或重叠样本的队列不被写成独立复现；重叠事实在代码里断言
- [ ] 只有部分类别的队列标明"（2-class）"等，classes_present 来自数据
- [ ] 不同分析族（如两种保形/校准定义）各有名字、定义句与独立分块，不混在一个 panel

## 4. 措辞（图内文字 + 图注）
- [ ] 禁用词（项目唯一一份表，图与表共用）在图内与图注中均未出现，例如 validated / superior / clinical benefit / diagnostic / clinically proven / deployment
- [ ] 只呈现主线：没有任何图、表、图注用到规格 §0 版本清单里的丢弃版本（不当对照、补充实验或"修复前后"比较）
- [ ] 次要分析按科学问题组织，不出现内部计划编号（H1–H5、E1/E2、R0–R5 等）和"预注册 / 假设状态"
- [ ] 图注、表题不写开发史（wave、closure、修复、重拟合、口径裁决）和逐图探索性声明（`medfig-plan/references/mainline_rules.md`）
- [ ] 类别限制、样本单位（"组"指临床组还是推断组）写清
- [ ] P 值、阈值、闸门类结果不被写成疗效或有效性结论
- [ ] 图注里的每个事实能在数据或 provenance 中找到对应值

## 5. 排版
- [ ] 最终尺寸下字号 ≥ 6 pt（仅 inset 刻度允许 5 pt）
- [ ] 负号为真减号 U+2212（含自动刻度），SVG 中无 ASCII 负号
- [ ] 宽度为期刊单栏/双栏（例如 3.46 / 7.09 in），其他宽度有偏离记录
- [ ] 配色按语义保留（队列、类别、方法、顺序各一套），不同语义不撞色
- [ ] 灰度下可读（冗余 marker / 线型 / 阴影对比）；斜线阴影颜色对底色有对比
- [ ] 文字不重叠、不出画布、图例不压数据

## 5b. Panel 样式与组图（spec §9，绑定）
- [ ] S1 留白：影像 panel 列宽按图像宽高比分配；图例放图像内角或紧贴上方，不单独占侧栏；每个 panel 内容 bbox 左右空白合计 ≤ panel 宽度 15%（内容约占 ≥ 85%）；`qa.whitespace_audit` 通过
- [ ] S2 无纯文字 panel：只含文字、没有数据图元的 axes 一律删除，信息也不迁到图注；`qa.text_only_panel` 通过
- [ ] S3 数据图元有彩色：每个 panel 的线、点、柱、区间、热图 cmap 至少一种非灰（饱和度 > 0.15），用 Okabe-Ito；只有坐标轴、网格、参考线、对照阴影/参考带可为灰；区分方法/排序用 Okabe-Ito 色 + 线型/标记冗余编码，不用黑/灰区分；`qa.colour_audit` 通过
- [ ] S4 单 panel 独立导出：每个 panel 有 `out/panels/<fig>/<fig>_<panel>.pdf` 与 `.svg`（可编辑，fonttype 42），尺寸与组图中该 panel 一致，不带 a/b/c 序号；已写入 source.json
- [ ] S5 ROC 样式：正方形坐标；虚线对角机会线（chance line）；多次重复（seed/fold）在共同 FPR 网格上用 `np.interp` 插值得平均曲线 + ±SD 阴影带；图例写 "AUC = mean ± SD"、放右下角；x 轴标 "1 − specificity"（不是 "Specificity"）；Okabe-Ito 配色；只有单条曲线时不画 SD 带并在图注说明

## 6. QA 与导出
- [ ] 唯一导出出口在最终尺寸上跑 QA，失败即抛错；没有 try/except 包住导出
- [ ] provenance 列出全部输入（路径 + SHA-256 + 行数），输入只来自只读数据根或白名单目录
- [ ] 产物（pdf/svg/png/灰度/source.json）在主 checkout 存在且为本次导出，不是 worktree 里的旧文件
- [ ] QA 误报要修审计器并加回归测试，不靠改图绕过

## 7. 代码与测试
- [ ] 无私有 API 调用、无死 helper、无硬编码绝对路径
- [ ] 脚本暴露 `build() -> (fig, prov)`，测试断言在 `prov.values` 上并与独立读取的源数据交叉核对
- [ ] 测试不空（真的会在错误实现上失败）；不写死 `fig.axes[5]` 之类索引；关闭所有 figure
- [ ] 没有越出本任务文件所有权的改动

## 报告格式
```
Spec compliance: ✅ / ❌（逐条列未满足项）
Task quality: Approved / Needs fixes
Critical: …   Important: …   Minor: …
Cannot verify: …（需主控或跨任务上下文才能确认的项）
Checked and clean: <清单编号> — <file:line 证据>
```
审查者只报告，不自己改代码；建议涉及数字时注明"需回源核实"。
