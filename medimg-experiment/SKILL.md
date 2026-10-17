---
name: medimg-experiment
description: "Use when establishing or running a managed Windows local medical-imaging classification or segmentation experiment from a research plan and optional code (实际实验执行、模型代码探索、异常后续跑): confirm splits, lock the test set, fix metrics and statistics, set a run budget, then train, monitor, recover, test and archive through a managed controller with independent review. Not for manuscript writing, literature search, or drawing figures."
---

# 医学影像实验

把研究计划转成有证据的本地实验。先厘清意图：只解释计划或检查环境时完成对应只读工作；用户要实际运行时才准备实验契约。自然语言触发和技能调用都不等于训练许可。

## 项目约定（检测到 PROJECT.md 时）

- 从工作目录或作者给出的路径向上查找 `PROJECT.md`；找到时，study 根默认用 `01_analysis/<study-id>/`，作者另行指定的路径优先。仍须满足控制器规则：全新目录、不位于原数据目录内、不与源代码目录重叠；目录不存在即可，`init` 会创建父目录。
- 结束后（`export` 或阶段性交付时），在 `01_analysis/README.md` 登记 study 目录、`report.md` 与锁定测试状态，并在 `PROJECT.md` 的目录说明写一行；不写阶段状态表（实验不在阶段表内）。
- 论文项目侧由 medpaper-pipeline 的代码接收与整理子流程核验登记，只核验不搬家；本技能的目录结构、契约与控制器行为不变。

没有 `PROJECT.md` 时保持下文原有行为，不新建它。

## 选择模式

- `matrix`（论文实验，推荐）：执行计划中预定义的实验清单——基线、主方法、逐组件消融、近邻对比。每个条目同代码规则、全部 seed、与参照基线做患者级配对区间；不自动择优。来自 `medical-research-plan` 的实验设计通常用此模式。
- `search`（调优/探索）：基线 → 爬山式探索 → 同代码多 seed 正式复核。适合在固定评价下找可用配置；最终结论仍以锁定测试为准，并报告候选数。

用户一步步推进时，结果不好可停止、调整并以新契约版本重来；每个版本的证据独立保留。

## 流程

1. 在用户指定的新课题输出目录中工作，保留原始计划；有现成代码时只复制必要代码配置，没有代码时由当前代理在受管工程中实现。固定患者等分组单位、标签来源、train/val/test 划分、评价协议及冻结文件（划分、评价、测试脚本）。
2. 训练前取得对完整契约的明确确认：模式与矩阵条目、主要指标与 checkpoint 规则（last/best）、护栏指标、基线来源与调参对等、成功标准与最小效应、异常阈值、≥3 个 seed、配对 bootstrap 规则、测试集策略、允许修改的文件及参数、预算、解释器、设备和精确依赖版本。缺项保持待确认；数值不套通用默认。新环境或依赖安装另需具体方案批准。
3. `approve` 后先 `audit`：冻结的审计脚本列出各划分分组 ID 与类别计数，控制器拒绝任何跨划分重叠。
4. 当前代理提出模型代码或参数候选并保存不可覆盖的快照。每个候选先交给新的独立只读审查子代理，记录实际读取的文件；通过后才用控制器启动一个受管训练。后台监控器只执行当前候选、检查指标、停止和保全，不设计模型、不启动下一个候选。
5. 验收：每个候选全部 seed 完成，seed 与聚合值在正常范围、seed 样本标准差达标、护栏指标未超出允许恶化；search 的复核还需聚合达标且相对基线的患者级配对 bootstrap CI 下限满足规则。matrix 条目只需稳定性与完整性，比较结果如实报告（消融变差是正常结果）。
6. 锁定测试集只在 search 的基线、`accepted` 最终版本，或 matrix 全部完成后评估；每候选每版本一次，用冻结的测试脚本在被测提交的独立检出中运行，结果只报告、不回流选择，查看次数累计登记。
7. 异常必须先在当前对话汇报，再登记 `reported`，再 `recover`。到 `awaiting_direction` 后停止；只有用户选定新方向并确认新契约才 `resume`。导出时区分已实现、已运行、契约达标与未验证，保留全部负结果。

## 按任务读取

- 首次使用、环境检查或填契约：[setup-contracts.md](references/setup-contracts.md)，使用 [contract-template.json](assets/contract-template.json)。
- 建候选、训练器协议、测试、导出：[execution-protocol.md](references/execution-protocol.md)。
- 异常、离线重入、预算结束或恢复：[recovery.md](references/recovery.md)。
- 派发审查子代理与登记结果：[independent-review.md](references/independent-review.md)。

所有控制命令调用本技能目录下的 `scripts/controller.py`（按技能实际安装位置解析，Claude Code 与 Codex 路径不同），不直接运行 `scripts/worker.py`。本技能不调用外部模型 API，不上传研究数据，不读取、调用或引用外部流程套件的资源；如需要额外隔离，可在环境变量 `MEDEXP_BLOCKED_ROOTS` 中登记禁止根目录。训练代码同样必须本地运行、数据只读。控制器约束只覆盖经它执行的受管操作，不是操作系统沙箱；审批、汇报及审查身份由调用方记录，不能独立认证人类批准。同模型家族审查不构成科学有效性证明。
