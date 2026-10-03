# 并行 worktree 规则（parallel rules）

适用：共享层与锚点测试已绿之后的逐图任务波。通用做法是串行派 implementer；本规则是出图项目的受控例外：独立任务各占一个 worktree 并行。

## 1. 开波条件
- 共享库（figkit）稳定：共享层任务 complete，锚点测试绿。
- 本波任务之间冲突扫描无未裁决行。
- 一波约 4 个；用户明确要求更多时写 Ruling（含 cost if wrong）。

## 2. 建 worktree
```
python scripts/new_worktree.py --repo <主checkout> --task N --wt-root <dir>
```
- 分支 `taskN`，从 master HEAD 建；输出 JSON 的 `base_sha` 记为 BASE。
- 幂等：分支和 worktree 已存在则 `status: exists`，不会重建；分支在但 worktree 不在则 `attached`。
- 目标路径被无关文件占用时报错退出，不覆盖。

## 3. 文件所有权
| 文件 | 写者 |
|---|---|
| `figures/<fig>.py`、`tests/test_<fig>.py`、`docs/captions/<fig>.md` | 该图任务独占 |
| 共享库 `lib/figkit/**` | 并行期间无人写；主控合并时提升 helper |
| `docs/_process/ledger.md` | 只由主控写 |
| `docs/_process/tasks/task-NN-*` | 该任务独占 |
| 汇总文件（QA_SUMMARY、汇总图注、README） | 主控；或每任务一个分节，只追加自己的分节 |

- 需要共享库没有的 helper：在本任务脚本里本地写一份，report 里标 "lift candidate"，主控合并时提升，写 Ruling。
- 分节追加格式：`<!-- task NN begin -->` … `<!-- task NN end -->`，只改自己的分节，合并冲突时保留两节。
- 两个任务同时追加同一文件导致重复行是已知故障；台账不交给子代理写。

## 4. 合并顺序
1. 该任务 review clean（或 breaker 裁决完）。
2. master 上 `git merge --no-ff taskN`；冲突只可能出现在共享汇总文件，按分节保留。
3. 主分支重导出：
   ```
   python scripts/reexport_check.py --root <主checkout> --python <解释器> \
       figures/<fig>.py=out/figures/<kind>/<fig>.pdf,out/figures/<kind>/<fig>.svg,out/figures/<kind>/<fig>.png,out/figures/<kind>/<fig>.source.json,out/panels/<fig>/<fig>_<panel>.pdf,out/panels/<fig>/<fig>_<panel>.svg
   ```
   `<kind>` = `export.save` 的 `kind`（`main` / `supp`）；每个 panel 列一对 pdf/svg。
   退出 0 才继续；1 = 脚本失败 / 产物缺失 / 产物未被刷新（stale）；2 = 在 linked worktree 上跑（拒绝）。
4. 台账写 merge 行（含 "re-exported … on master"）。
5. 最后才 `git worktree remove` 与删分支。

## 5. 禁止
- 在 worktree 里导出后直接删 worktree。
- 并行任务改共享库、改其他任务的文件、写台账。
- 子代理再派子代理（含 reviewer）。
