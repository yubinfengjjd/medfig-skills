# 机器登记的最小用法

仅在启用完整登记时读取；默认轻量模式不需要这些 JSON。精确字段/枚举与原型在 [records-template.json](../assets/records-template.json)。首次访谈先写真实 session.md，不为发问一次性复制全部机器原型或假装方案已经完备。到需要结构检查时创建五个 JSON 输入；只按当前内容填实际记录。G1–G3 的含义以访谈参考为准（G1 临床问题与约束，G2 方向、任务与定位，G3 实验与可行性），登记结构不变。

资产的 `files` 包含 state.json、constraints.json、evidence.json、data-register.json、plan-contract.json 的未确认启动内容。分别保存 `files[文件名]` 的对象，不把整个资产复制为一个输入。五个文件的 schema_version 为 1.0，version 一致；更新当前方案版本时同步登记，但不自动升级旧确认。

`record_templates` 是尚未填充的原型，不是完成记录。先填实际数据再加入相应 records 数组，不能用空壳或编造来源满足计数。记录 ID 用稳定的规范键；模态/变量也用统一规范键，并保留与真实数据字典名称的映射，不能为通过检查改变实际变量含义。

## 文件与内容

- state：stage、status、version、gates.G1/G2/G3、unknowns；局部改版时可添加 changes，不能用全局 version 改写历史确认。artifacts 可覆盖 session/main_plan/review 的默认文件名，使用项目内相对 .md 路径；默认分别为 session.md、project-plan.md、review.md。不接受绝对路径、.. 越界或解析后逃出项目的链接。
- constraints：records，含 kind（HARD/TARGET/PREFERENCE/DEFAULT/UNKNOWN）、明确规则、来源、确认和影响。QUANTITY 对已登记 ID 计数；NUMBER 对显式实际值比较。TARGET 不足是提示，不自动变硬条件。
- evidence：records，含 title、状态、影响、source、verification 与支持/挑战主张。书目、作者、年份、DOI、检索 ID、阅读范围/原文定位等科学字段按证据参考补充；这些额外域并不全由结构脚本核验。
- data-register：records，含 name/version、role、uses、available_inputs、证据、独立单位与 group_ids。官方访问、样本规模/单位、标签/时间、许可、访问流程等按数据参考补充并保留核验范围。
- plan-contract：平坦 records，每条有 record_type；sections 为主文覆盖索引，每节有 summary 与 ref_ids。section 文字与主文一致需要人/agent 复核，脚本不能读标题就证明科学一致。

## 确认来源

CONFIRMED 记录需 source.kind=USER、decision=CONFIRM、scope 包含相应 G 节点或约束 ID、实际答复和 session 定位。部分答案用 ANSWER，不构成节点确认。执行授权用独立 AUTHORIZE_EXECUTION，不用科学确认替代。

确认版本通常等于当前方案版本。局部改版保留原确认 version 和 USER 来源，在 state.changes 显式记录连续变更链。每条 GATE_CHANGE 填 id、record_type、from_version、to_version、reason、source（kind/locator/summary）、affected_gate_ids、preserved_gate_ids、affected_constraint_ids、preserved_constraint_ids。gate 两数组须无重叠、无遗漏地划分 G1–G3；constraint 两数组不得重叠，ID 指向实际约束。

旧确认仅在从原版本到当前版本的每一条变更都明确保留该 gate 或该约束 ID 时适用。保留 G1 不自动保留其中所有约束；G1 内一项约束变化可以保留另一项未变约束的原确认。受影响决定标 INVALIDATED，再取得真实的新确认；不得把历史答复改日期或改成当前版答复。changes 的来源记录实际用户变更或助手在已确认边界内的细化，只说明保留/影响判定，不创造新确认；scope 真实正确性仍需复核。

结构检查仅检查已登记 provenance 的形状与关系，不会认证答复真的是用户说的；审查必须回查源记录。用户确认研究假设不等于假设已实证成立。

## 方法、主张与实验

METHOD 链接 dataset_ids、required_inference_inputs、evidence_ids；可用模态或变量必须满足使用时输入。CLAIM 链接方法、证据和 experiment_ids，明确 falsification。EXPERIMENT 链接主张、方法、数据、metric_ids 和 task_ids。METRIC 明确 target/definition/unit/aggregation/uncertainty/primary。

训练与分析任务需 CONFIG 的 method_id/settings；评估与 profiling 若声明 CONFIG，同样需要对应预算行，不能漏出总账本。TASK 写 scientific_purpose、claim_ids、depends_on、inputs 的 ref_id/schema、outputs 的 path/schema、scope、planned_files、config_ids、command、acceptance、failure_handling、stop_conditions 和独立执行/授权状态。命令只是字符串，检查器不执行。

计划命令与任务为 PLANNED/NOT_STARTED；没有真实实现不能标 executable。真实运行过还需授权来源和 execution_evidence_ids。不能为通过检查虚构执行日志。

## 数据角色与成本

明确 EXTERNAL_TEST 不能 TRAIN/TUNE/CALIBRATE/THRESHOLD，也不能成为训练任务的输入。group_ids 只有实际可比较的脱敏分组键才填写；无键用 null，缺键意味着待核查独立性，不能证明无重叠。

BUDGET 填 config_id、runs、duration_hours 和 memory_gb 的上下限、measurement_status、basis、profile_task_id 与影响。未知预测用 UNKNOWN、null 上下限、真实未能估算原因和后续 PROFILING 任务；不强制 GPU。实际全部配置运行数、搜索、评价及重跑仍需完整账本审查，不能把一个预算行当作所有成本已核实。

READY_FOR_HANDOFF 需适用于当前版的三个确认、HANDOFF 阶段、可读取且非空的 session.md、project-plan.md、review.md（或 artifacts 登记的实际路径）和实质方案登记内容，没有影响成立条件的未解决问题。关键科学可行性证据为 PROVISIONAL/UNKNOWN/CONFLICTED 时不能称为可正式交接；未检验的科学假设按计划处理，不自动列为关键可行性未知。文件存在不证明正文或独立审查真实充分，仍需语义审查。正确暂定登记可以结构通过，但仍是暂定；报告中的 needs_review 和 limitations 必须保留。
