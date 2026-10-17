# 独立只读审查

每个候选在训练前需要一个新建、独立上下文的审查子代理。按宿主实际能力派发：

- Claude Code：用 Agent 工具新建子代理（不用 fork，不继承实现上下文），提示中给出原始文件路径与只读任务；`reviewer` 记 `claude-independent` 或 `independent-subagent`，`agent_id` 记返回的代理 ID。
- Codex：若有 `spawn_agent`，优先 `fork_turns: "none"`；`reviewer` 记 `codex-independent` 或 `independent-subagent`。

不要借用刚实现该候选的代理，不预填“应该通过”，不让同一审查者修改再自审。审查仍属同模型家族，其独立性用于减少实现者遗漏，不能宣称独立科学验证。

派发内容示例，按实际候选填写：

```text
请只读审查 <课题root>/worktree 中候选 <id> 的提交 <commit>。
研究计划：<plans/original.md>；当前契约：<plans/contract-NNN.json>；
候选与命令：<candidates/id.json>；划分审计：<evidence/audit/...json>；可用原始历史证据：<明确文件清单>。
检查实际训练/评价代码、标签与分组划分、测试数据是否在训练器中被读取、允许改动范围、冻结文件、
主要与护栏指标定义及单位、checkpoint 选择规则是否与契约一致、cases.jsonl 是否逐验证病例输出且与主要指标一致、
seed处理、设备与依赖、真实训练及权重输出、JSONL/result协议、本地运行与数据只读；
对比基线时检查调参预算、预处理与输入分辨率是否对等。
只读，不改代码、不运行训练、不安装环境、不调用网络，也不访问被隔离工程。
不使用另一审查者的意见。返回pass或block、带文件位置的findings、
实际读取的worktree文件相对路径artifacts_read及限制；不得把声明当原始证据。
```

`artifacts_read` 由控制器核验为 worktree 内真实文件，至少列出实际读过的训练/评价/划分源文件。其他已读证据可在 `additional_evidence` 说明实际路径；该附加字段未被核验，勿称为证据认证。大文件或真实敏感数据只在本机按最小必要范围读取，不能转交外部 API。

审查结果保存为 JSON，使用真实代理 ID 与候选返回的 commit：

```json
{
  "candidate_id": "base-001",
  "commit": "从候选记录取得的实际Git提交",
  "reviewer": "independent-subagent",
  "agent_id": "本次新审查代理的真实ID",
  "verdict": "pass",
  "findings": [],
  "artifacts_read": ["train.py", "model.py", "synth_data.py"],
  "limitations": "同模型家族，只读代码审查；不构成科学有效性证明"
}
```

block 时保留具体问题与严重性，按批准范围修正后建立新候选、新快照和新审查；不要改结论字符串强行通过。没有独立子代理能力时可以整理计划/环境和候选，训练保持未启动，并说明缺少必需的独立审查。

```bash
"$PY" "$CONTROLLER" review --root "$STUDY" --record "$REVIEW_JSON"
```

登记时要求候选 revision 为当前版、commit 一致、worktree 干净且仍处于同提交，reviewer 为允许值且 agent_id 存在、findings 为列表、artifacts_read 非空且全部为现存 worktree 文件。run 还检查 `verdict: pass` 和相同 commit。控制器自动补充 `identity_assurance: caller-recorded; same-family; not scientific proof`。

控制器只能核对记录的格式与文件/提交，不能证明 agent_id 是新的、代理真的独立、文件真的读过或审查质量达标；调用方必须按本协议实际派发和记录。严格审查不能取代医学标签质量、临床样本外验证、统计推断或临床效用评估。
