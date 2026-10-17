# 建工程与确认契约

入口：`controller.py init --root <新输出目录> --contract <实际契约.json>`。`--root` 是每个课题显式指定的全新目录；不写在契约内，不能位于原数据目录内，也不能与源代码目录重叠。`init` 只建立工程与证据，不启动训练。既有目录被拒绝。

## 现有环境

先只读核实 Windows、Git、用户选择的真实 Python 可执行文件、已安装包版本、数据可读性及剩余磁盘。不使用 Windows 应用别名（WindowsApps 下的 python 占位程序），不借用被隔离工程的解释器。控制器本身只用 Python 标准库和本机 Git。

```bash
"$PY" -c 'import sys, importlib.metadata as m; print(sys.executable); print(m.version("numpy"))'
```

把实际版本填入 `environment.dependencies`；每次 run 核对版本完全一致。GPU 任务显式选 `device: "cuda"`，控制器检查 `torch.cuda.is_available()` 与设备名，不自动改为 CPU。驱动、CUDA/PyTorch 兼容、数据容量和显存需实际检查。环境不满足时先准备可审阅方案（路径、Python 版本、精确包版本、CPU/CUDA、磁盘、安装命令），用户明确批准后才安装。

## 开工前与用户逐项确认

按研究实际讨论，不套默认数值：

1. 模式：`matrix`（执行计划中的实验清单）或 `search`（调优）。matrix 条目逐一列出 id、角色和内容，指定参照基线条目。
2. 划分与测试：分组单位；train/val/test 划分方式与来源；是否设锁定测试集，或为何不设。外部测试集如另有数据，通常建独立课题或在测试脚本中单列，并在计划中说明。
3. 基线：来源（如 nnU-Net、领域预训练模型、现行方法）、为何足够强、调参预算是否与主方法对等。
4. 指标：主要指标、方向、checkpoint 规则；护栏指标及允许恶化量；逐病例统计（mean_per_case 或 binary_auroc）。
5. 统计：≥3 个 seed、聚合方式、正常范围、seed SD 上限、配对 bootstrap 次数/置信水平、search 的 CI 下限规则与最小效应。
6. 改动范围、冻结文件、允许参数、异常阈值、时间与候选预算、解释器与依赖。

## 契约字段

复制 `assets/contract-template.json` 填写。`null` 与空列表故意不可运行；不要为通过校验擅自发明阈值、预算或数据规则。

| 字段 | 约束与含义 |
| --- | --- |
| `schema_version` / `study_id` | 2；ID 为 1–64 个字母、数字、下划线或连字符，首字符为字母/数字。旧版 1 契约不被接受，需按新模板建新课题。 |
| `task` / `mode` / `hypothesis` / `plan_path` | `classification`/`segmentation`；`matrix`/`search`；明确假设；原始计划绝对路径（复制为 plans/original.md）。 |
| `stages` | search 为 `["baseline","explore","verify"]`；matrix 为 `["matrix"]`。 |
| `matrix.entries` / `matrix.reference` | 仅 matrix：每条 `{id, role, description}`，role 为 baseline/proposed/ablation/comparison；reference 指向一个 baseline 条目，作为配对比较参照。 |
| `code.source_root` / `files` | 可选源目录及逐文件复制清单；无代码时 `null` 与 `[]`。只复制代码/配置，禁止数据、权重、凭证、符号链接。 |
| `primary_metric` | `name` 与训练输出一致；`direction` higher/lower；`selection` last/best；search 需 `target` 与非负 `min_effect`（指标本身单位）。 |
| `guard_metrics` | 列表，每项 `{name, direction, max_degradation}`；相对基线/参照的聚合值恶化超过阈值即拒绝（search）或标注（matrix）。无护栏写 `[]`，需在确认时说明理由。 |
| `baseline` | `source`、`strength_rationale`、`tuning_parity` 均为必填文字；写入报告。 |
| `data.*` | 非空现存绝对数据路径（只读）；标签来源；划分引用；分组单位；评价协议。 |
| `split_audit` | `command` 为 `{python}` + 冻结脚本 + 一次 `{output}`；`timeout_seconds`。脚本写 `{"group_unit": ..., "splits": {"train": {"group_ids": [...], "class_counts": {...}}, "val": ..., "test": ...}}`；group_unit 须等于 `data.group_unit`；使用脱敏 ID。 |
| `test` | `policy: locked` 需 `reference`（测试集来源说明）、`command`（冻结脚本，含一次 `{run_dir}` 与 `{output}`）和 `timeout_seconds`；`policy: none` 需 `rationale`。 |
| `scope.editable_paths` | 非空，worktree 相对路径或模式；不得含绝对路径、盘符、`..` 或 `.git`。 |
| `scope.frozen_paths` | 非空的明确相对路径；划分、评价、审计与测试脚本都应在内，审计与测试命令脚本必须在内。首个候选快照后不许变动。 |
| `scope.parameters` | 允许的长参数列表；不列 `--seed`。 |
| `anomaly.*` | `max_drop` 正阈值、`unit` absolute/relative（小数比例）、`warmup_steps`、`reference_ranges`（键为阶段名，`{}` 不启用）、`consecutive_outside_range`。下降规则只用于 explore/verify。 |
| `budget.*` | `total_seconds`、`run_timeout_seconds` 正数；search 另需 `max_candidates`、`max_no_improvement` 正整数。测试评估时间不计入训练预算。 |
| `verification.seeds` | ≥3 个不重复整数；每个候选跑全部 seed（search 的 explore 除外）。 |
| `verification.aggregation` / `normal_range` / `max_std` | mean/median/worst；各 seed 与聚合值的正常范围；seed 样本标准差上限。 |
| `verification.ci` | `method: paired_bootstrap`；`statistic` mean_per_case/binary_auroc（后者仅分类）；`resamples` 200–100000；`level` 如 0.95；`seed` 整数；search 需 `lower_bound_rule` min_effect/zero。 |
| `environment.*` | 真实解释器绝对路径；cpu/cuda；包名到精确版本；最低可用字节数。 |
| `retention.mode` | `necessary`。 |

主指标下降相对当前契约的已验证基线计算：higher 为 `baseline - value`，lower 为 `value - baseline`；relative 再除以 `abs(baseline)`。

## 初始化、生成代码与确认

`init` 建立独立 Git 仓库 `code/` 和关联 `worktree/`，源仓库保持原样。无现成代码时，在 `worktree/` 按计划建立训练器、模型、固定划分/评价、审计与测试脚本；训练器只读 train/val。

在当前对话展示完整契约、实际路径、主要命令和预算，取得明确确认后：

```bash
"$PY" "$CONTROLLER" approve --root "$STUDY" --statement '用户实际确认的契约版本、范围与预算'
"$PY" "$CONTROLLER" audit --root "$STUDY"
```

`audit` 只能在首个候选快照前运行，失败（如分组跨划分重叠）时修正冻结脚本后重跑；通过后才能建候选。`approve` 仅登记调用方提供的文字，不独立认证用户；没有确认不得用编造语句开门。后续新方向用恢复协议，不能修改旧契约冒充原批准。
