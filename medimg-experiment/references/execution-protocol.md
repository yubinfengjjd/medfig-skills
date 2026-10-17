# 候选、训练协议与证据

## CLI

用已核实的 Python 运行技能实际位置下的 `controller.py`；不要假定当前目录就是技能目录，也不要用 WindowsApps 的 python 占位程序。Git Bash 示例（PowerShell 同理改变量语法）：

```bash
SKILL="<本技能实际目录>"          # 如 ~/.claude/skills/medimg-experiment 或 ~/.codex/skills/medimg-experiment
CONTROLLER="$SKILL/scripts/controller.py"
PY="<用户选定的现存Python绝对路径>"
STUDY="<用户指定的全新课题输出绝对路径>"
```

用前先确认这些路径。CLI 打印 JSON，成功退出 0，失败退出 2；错误 JSON 含 `error` 和中文 `summary_zh`。后台排队成功不等于训练成功。

| 命令 | 实际参数 |
| --- | --- |
| `init` | `--root PATH --contract FILE` |
| `approve` | `--root PATH --statement TEXT` |
| `audit` | `--root PATH` |
| `candidate` | `--root PATH --id ID --phase baseline\|explore\|verify\|matrix --command FILE --description TEXT [--entry ENTRY]` |
| `review` | `--root PATH --record FILE` |
| `run` | `--root PATH --candidate ID --seed INT` |
| `test` | `--root PATH --candidate ID --rationale TEXT` |
| `status` | `--root PATH` |
| `reported` | `--root PATH --statement TEXT` |
| `recover` | `--root PATH` |
| `resume` | `--root PATH --contract FILE --direction TEXT --statement TEXT` |
| `export` | `--root PATH` |

`candidate --command` 指向包含 argv 数组的 JSON 文件，不是 shell 命令：

```json
["{python}", "train.py", "--seed", "{seed}", "--learning-rate", "0.001"]
```

数组开头必须为 `{python}`；第二项为受管 worktree 内 `.py` 脚本；`--seed` 紧邻唯一 `{seed}`；其他长参数须在契约白名单中。不加 shell、管道、其他占位符或命令链。代码变动后原审查失效，须为新快照建立新候选并重新独立审查。

候选必须处于当前阶段；matrix 模式用 `--entry` 指明契约条目，每个条目一个候选、跑全部 seed。首个候选快照前必须已通过 `audit`，且冻结文件与审计时一致；此后冻结文件不许修改。同课题只允许一个受管训练或测试，同一候选同一 seed 不得重复覆盖。

## 训练器输入

训练器当前目录是 `worktree/`，接收：

| 环境变量 | 含义 |
| --- | --- |
| `ME_RUN_ID` / `ME_PHASE` | 当前运行身份与阶段（baseline/explore/verify/matrix）。 |
| `ME_OUTPUT_DIR` | 当前运行独立目录；本次权重、输出和指标写到这里。 |
| `ME_CONTRACT_PATH` | 本次运行保存的完整契约 JSON。 |
| `ME_DEVICE` | 契约选择的 cpu/cuda；训练代码必须实际遵守。 |
| `TMP` / `TEMP` / `TORCH_HOME` / `HF_HOME` | 当前运行目录内 tmp/cache 路径。 |
| `WANDB_MODE` | `disabled`；仍须审查代码不启用其他外部 API 或遥测。 |

训练器只读 train 与 val；不得读取 test 划分。控制器不阻止代码访问网络或任意文件，由审查核对。禁止运行外部 API、上传研究信息、修改源数据、改评估以适应结果。预训练文件只用作者已提供的本地文件。

## 指标 JSONL

训练器在 `ME_OUTPUT_DIR/metrics.jsonl` 按行追加完整 JSON 并及时 flush：

```json
{"run_id":"r-实际ID","phase":"baseline","step":0,"metric":"dice","value":0.81,"time":"2026-10-12T02:30:00.000000+00:00"}
```

必填 `run_id/phase/step/metric/value/time`。ID 与阶段须匹配当前运行；step 为非负整数；value 为有限数值；time 带时区。主要指标的 step 必须严格递增。NaN/Inf、非法 JSON、身份不符、结束时残缺尾行都属于异常。主要指标按确认规则检查暖启动、相对已验证基线的下降（仅 explore/verify）和阶段参考区间。监控约每 2 秒轮询。

## 完成结果

退出码 0 仍需完成 `result.json`，最后原子发布：

```json
{
  "run_id": "r-实际ID",
  "phase": "baseline",
  "completed": true,
  "metrics": {"dice": 0.81, "hd95": 7.2},
  "artifacts": ["weights.pt", "cases.jsonl", "checkpoint.json"]
}
```

- 主要指标须等于 checkpoint 规则对应的原始事件：`selection: last` 为最后一个主要指标事件；`best` 为全程最优事件（按 direction）。训练器保存的权重必须就是该 checkpoint。
- `metrics` 必须包含契约中每个护栏指标（同一 checkpoint）。
- `cases.jsonl`：验证集逐病例一行，`case_id` 集合必须与审计登记的 val 分组 ID 完全一致。`mean_per_case` 统计每行含 `value`（例如该病例 Dice，或分类正确为 1/错误为 0），均值须复现主要指标；`binary_auroc` 每行含 `label`(0/1) 与 `score`，AUROC 须复现主要指标。
- artifacts 为输出目录内非空文件，至少一个权重后缀 `.npz/.pt/.pth/.safetensors`。不得写假权重或以文件存在冒充训练。运行结束还检查工作树干净、提交与已审查版本一致。

## 验收规则

所有阶段：候选全部 seed（≥3）完成，各 seed 与聚合值在 `normal_range` 内，seed 样本标准差 ≤ `max_std`。

- search / baseline：达标后建立稳定基线并记录其逐病例结果。
- search / explore：通常先跑一个 seed；相对基线无改善，或任一护栏恶化超过 `max_degradation`，记拒绝、回退到稳定提交、增加无改善计数。改善且达 target 与 min_effect 进入 verify。
- search / verify：必须与达标探索候选同 commit、同命令，只变 seed。另需聚合达 target、护栏不超恶化、且对基线的患者级配对 bootstrap Δ 的 CI 下限满足 `lower_bound_rule`（`min_effect`：≥ min_effect；`zero`：> 0）。全部满足为 `accepted`；否则保存有效负结果并进入异常报告流程。
- matrix：每个条目达到稳定性规则即完成；与 `matrix.reference` 的配对 CI 和护栏提示在导出时计算并如实报告，不作为通过门槛。全部条目完成为 `matrix_complete`。条目复核不稳定（seed 越界或 SD 过大）进入异常报告。

配对 bootstrap：对病例有放回重采样，每次在各 seed 上分别计算统计量，再按 `aggregation` 聚合后求差；百分位区间。病例数少、AUROC 重采样常出现单一类别时会报错，而不是给出虚假区间。

预算耗尽是 `budget_exhausted`，目标未达成，不写完成结论。

## 锁定测试集

`test.policy: locked` 时：

- 允许时机：search 的本版本稳定基线（作为最终对照）与 `accepted` 版本；matrix 全部条目完成后任一条目。每候选每版本只评估一次；控制器累计 `test_looks`，超过 2 次在报告中写明乐观偏倚风险。
- 执行：控制器把被测提交检出到独立目录，确认冻结文件与冻结版本一致，对候选每个 seed 的运行目录调用冻结测试命令（`{run_dir}` 为该运行目录，`{output}` 为测试输出目录）。测试脚本加载该运行的权重，写 `cases.jsonl` 与 `result.json`；case_id 必须与审计登记的 test 分组完全一致。
- 结果只写入 `tests/` 与报告，不改变任何阶段、稳定版本或选择。导出时给出测试集上候选对参照的配对 CI。

`test.policy: none` 须写理由；报告注明所有结果均来自用于选择的验证集。

## 文件与导出

```text
<root>/
  plans/                original.md、版本契约/批准、有效计划、revisions.jsonl
  code/                 独立Git仓库与稳定分支
  worktree/             受管工作树
  candidates/           候选快照、命令、审查及run ID
  runs/<run-id>/        record/contract/candidate.json、code.bundle、metrics.jsonl、
                        result.json、cases.jsonl、权重、train/monitor.log
  tests/<test-id>/      test.json、summary.json、<run-id>/cases.jsonl 与 result.json
  evidence/             audit、incidents、reviews、stable、rejections、failures、negative-results
  state.json / events.jsonl / report.json / report.md
```

`export` 可在各状态执行。报告包括数据与基线声明、划分审计摘要、全部运行、matrix 表（聚合、seed SD、Δ 与配对 CI、护栏提示）、当前有效方法及其相对基线的 CI、锁定测试记录与比较、限制。不删除不利证据。

每次 run 的 `code.bundle` 保存候选提交及历史。在全新目录恢复：

```bash
git init "$NEW_DIR"
git -C "$NEW_DIR" fetch "$CODE_BUNDLE" "refs/medexp/candidates/<ID>"
git -C "$NEW_DIR" checkout --detach "<commit>"
```

bundle 不是完整环境镜像，不含源数据或预训练权重。

## 合成示例

`assets/synthetic/` 是 CPU NumPy 协议演示，不是医学验证：

- 冻结：`synth_data.py`（80 名合成患者、按患者 48/16/16 固定划分、共享评价函数）、`audit_split.py`、`evaluate_test.py`。
- 可编辑：`model.py`（tanh MLP）、`train.py`（逐 epoch 记录 val 指标、保存 best-val checkpoint、输出 cases.jsonl 与护栏指标 brier/area_error）。
- 参数：`--task classification|segmentation --seed --epochs --width --learning-rate`。

使用时核实并固定实际 NumPy 版本、声明 CPU 与合成数据，仍需真实契约确认和独立审查。`tests/demo_acceptance.py`（开发副本内）演示两种模式端到端流程。
