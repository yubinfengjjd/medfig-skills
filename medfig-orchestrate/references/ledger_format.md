# 台账与报告格式（ledger format）

台账路径 `docs/_process/ledger.md`，git 跟踪，只由主控写。上下文压缩后以台账 + `git log` 恢复进度。

## 1. 文件结构
```
# medfig ledger — plan: <计划路径>

Spec: <spec 路径>（reachable / 不可达则写明，之后的 Ruling 为临时）。Repo: <说明>，base <sha7>。

## Pre-flight scan
| 任务对 / 任务 | 产出 vs 消费 | 发现 |
|---|---|---|

## Rulings
- Ruling: …

## Tasks
Task 1: dispatched (<model>), BASE <sha7>
…
```

## 2. Ruling 行
```
- Ruling: <决定了什么> — <为什么> — <cost if wrong：判断错了要付出什么>
```
- 三段缺一不可；cost if wrong 写具体返工（"panel a 重画一次"），不写"无"以外的空话。
- 任务内的 Ruling 前缀任务号：`Task 9: Ruling: …`。
- 用户决定也记，注明来源：`Ruling: … (user approved "<原话>") — …`。

## 3. 任务状态行（按时间追加，不改旧行）
| 事件 | 格式 |
|---|---|
| 派发 | `Task N: dispatched (<model>), BASE <sha7>, worktree <path>` |
| 实现回报 | `Task N: implementer DONE / DONE_WITH_CONCERNS (<sha7>; k passed; QA clean); concerns: …` |
| 审查 | `Task N: review ✅ Approved` 或 `Task N: review ❌ (k Critical, m Important: <一句话>)` |
| 主控核实 | `Task N: controller verified <事实> from source: <数值>` |
| 修复轮 | `Task N: fix round R/5 (a addressed, b open — <一句话>; commits x..y)` |
| minor | `Task N: minor (deferred): <一句话>` |
| 停放 | `Task N: parked — <发现> — Ruling: <为什么保留>` |
| 失联 | `Task N: <角色> lost (agent gone); re-dispatched` / `takeover k` |
| 合并 | `Task N: merged <sha7>; re-exported <figs> on master (reexport_check exit 0)` |
| 完成 | `Task N: complete (commits a..b, merged <sha7>, review clean after round R)` |
| 额度 | `STOPPED: 403 / insufficient balance at Task N (<阶段>); user notified` |

有 `complete` 行的任务不重派；最后一行是 fix round 的任务从下一轮续。

## 4. 终审报告 `docs/_process/final-review.md`
```
# Final whole-set review (<base>..<head>)
## Passes completed
1. 共享库 + 测试：completed（读了哪些文件，全读 / grep）
2. 主图：targeted pass（方法）。Not every line of every script was read.
3. 附图：…   4. 表 + 图注 + QA_SUMMARY + DELIVERY：…
Checked and clean: <事实> (<file:line>) ; …
## Critical / ## Important / ## Minor
I1. <问题>。<file:line 证据>。Fix: <具体修法>。
## Deferred-minor triage
must-fix: … / verified fixed at HEAD: … / acceptable: …
## Verdict
Ready / Ready after fixes / Not ready
```
覆盖范围要如实：没读的写"没读"。

## 5. 修复报告 `docs/_process/final-fix-report.md`
逐条镜像终审编号：`I1 <标题>: DONE / REJECTED / SKIPPED — <做了什么或理由>，<file:line>，测试 <名字>`。
REJECTED 必须附主控回源核实的数值与 Ruling。末尾 `## Verification`：测试命令与通过数、全部脚本退出 0、QA_SUMMARY 已更新。
