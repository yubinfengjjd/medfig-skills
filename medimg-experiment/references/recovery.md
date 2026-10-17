# 异常、离线重入与恢复

正常无改善按[执行协议](execution-protocol.md)自动回退并继续。环境预检失败、NaN/Inf、下降阈值、连续区间越界、超时、训练崩溃、输出协议错误、监控丢失、代码变化、正式复核失败等进入这条异常链：

```text
running/ready → awaiting_report
             → 当前对话中的异常汇报
             → reported
             → recover：回退 → 失败记录 → 有效计划更新
             → awaiting_direction
             → 用户选定方向 + 新契约明确确认 → resume → baseline
```

## 先停、保全、汇报

后台worker停止当前受管训练及其归属子进程，保留部分日志、权重/输出、运行记录和incident，设置`awaiting_report`。它不回退、不自动重试、不改变计划、不启动下一候选，也不通过外部服务通知。若对话不活跃，保留待报告状态；下次当前对话执行`status`先处理它。

在当前对话清楚说明：当前阶段与run ID、异常类型、实际指标及对照/阈值、退出或超时情况、已做的检查、证据位置、尚未确定的原因。报告要基于原始记录；没有数值就说明未产出，不编造。检查控制状态、run record、metrics尾部、train/monitor日志、契约和候选快照；诊断不得偷偷改变冻结评价或训练重跑。

实际汇报后登记：

```bash
"$PY" "$CONTROLLER" reported --root "$STUDY" --statement '实际已在当前对话汇报的阶段、异常、数值与排查摘要'
"$PY" "$CONTROLLER" recover --root "$STUDY"
```

`reported`只能从`awaiting_report`进入，`recover`只接受`reported`；已处于`awaiting_direction`时recover保持该状态。记录由调用方提供，控制器不能证明对话汇报真的送达；必须先实际报告再登记。

## 回退和等待方向

有已验证稳定提交时，recover先保全受管工作树的迟到改动，再回退到稳定提交，保存失败详情和报告语句，更新有效计划与时间线，进入`awaiting_direction`。没有稳定提交时只保全，明确“暂无可回退目标”，不捏造稳定模型。原始计划、旧契约、候选和原运行证据不覆盖。

此时可继续只读分析，提出有依据的后续选项，例如允许范围内减小模型/批量、修正训练器错误、调整已诊断的不适当训练设置，或停止实验。不要擅自替用户选方向，也不把沉默当恢复许可。任何新环境方案另需具体批准。

用户选定方向后，准备完整的新契约和新预算，让用户明确确认，再调用：

```bash
"$PY" "$CONTROLLER" resume --root "$STUDY" --contract "$NEW_CONTRACT" --direction '用户实际选定的方向' --statement '用户对新契约与预算的实际确认'
```

resume可从`awaiting_direction`、`budget_exhausted`、`accepted`或`matrix_complete`使用（后两者用于在已完成结果上开下一版本，例如加入新消融）。课题ID、模式、原plan_path、code导入规则，以及data、task、split_audit、test对象和frozen_paths列表须保持不变；冻结文件内容仍受首个候选提交保护。若要改变数据、划分、标签规则、评价协议、测试集或冻结文件，应新建课题工程，不能在原循环混用证据。

新契约增加revision，保留旧稳定证据但清空当前版本stable和baseline，重置本版本时间/候选/无改善计数。search从baseline重新执行全部seed。matrix在主要指标、护栏和verification规则都不变时，沿用定义未变的已完成条目（标注carried_from_revision），只需执行新增或修改的条目；规则变化则全部重跑。旧版达标结果不得写成当前新版达标。锁定测试的查看次数跨版本累计，不因新版本清零。预算结束后的加预算也需要新方向和新契约确认，不在state.json里直接改数字继续。

## 重入与状态协调限制

每次对话重入先运行`status --root ...`，读取当前版本和stage。不要依据旧对话的“running”继续训练。status在已登记的worker PID及创建token不再存活时登记`monitor_lost`；保留queued运行后超过10秒仍没有登记worker身份时，也进入awaiting_report并保全证据。迟到worker启动前检查当前run归属，归属已改变不得训练。这些协调不自动重跑。Windows Job Object在监控进程退出时会关闭，终止其受管成员；它不按PID扫描并杀死其他任务。

状态JSON原子写入，控制命令与worker协同记录加锁，但多文件和Git操作不是一个整体事务，极端中断可能留待人工核对的部分记录；Job归属之外的进程也不在控制范围。遇到孤立/不一致状态，先保存证据并核对run、事件、进程身份和Git，不把它算作成功或擅自清空active_run；在当前对话报告后决定修复方案。恢复流程不是通用系统崩溃修复器，不保证任何外部应用Job策略下都能持续运行。

监控丢失时，最近心跳的实测墙钟耗时保留；协调程序按截至发现时、受单次和剩余预算限制的保守墙钟估计扣预算一次，并明确记录`elapsed_seconds_estimated`与说明。这是预算控制估计，不是精确GPU用时；不得在报告中隐去估计标记。

控制器的awaiting_report门只阻止新的受管候选/训练；不能阻止人为直接执行Python或改文件。技能调用方须遵守等待与批准顺序。
