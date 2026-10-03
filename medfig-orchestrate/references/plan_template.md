# 实施计划模板（figure-set plan）

文件名：`docs/<date>-figure-set-plan.md`。计划是 spec 的论证，spec 是绑定权威。

```markdown
# <项目> 图表集 实施计划

**Spec:** `docs/<date>-figure-set-design.md`（绑定权威）
**项目根:** <path>（含 figkit.toml；git 仓库，master = 主 checkout）
**解释器:** <python 路径>（全程固定）
**只读数据根:** 见 figkit.toml `data_root`；白名单外部目录：`external_dirs`

## Global Constraints
- spec 优先于 brief；偏离需 Ruling + DELIVERY 偏离行。
- 所有图经 `export.save` 导出，禁止 try/except 包裹。
- 图中数字全部由数据计算，字面值只出现在断言里。
- 宽度 <期刊双栏> / <单栏> in，或记录偏离；字号 ≥ 6 pt。
- 并行任务不改共享库（见 parallel_rules.md）。

## Tasks
### Task 1 共享层：figkit 扩展 / 配置（标准模型以上）
文件：… 测试：… 完成判据：pytest 全绿。
### Task 2 数值锚点测试（number anchors）
先对源数据核一次，冻结为测试；失败说明数据根不对，停下报告。
### Task 3..K 逐图任务（每图一个）
- 输出：`figures/<fig>.py`、`tests/test_<fig>.py`、`docs/captions/<fig>.md`
- 每 panel：结论一句 | 数据文件与列 | 变换 | 图型 | GridSpec 参数
- 必须写进 `prov.values` 并断言的数：n per cohort、比例和、闭合误差……
- 完整性限制：aspect、共享色阶、absent 行、区间类型
- 每 panel 样式约束（spec §9）：留白 ≤ 15%、无纯文字 panel、数据图元 Okabe-Ito 彩色、ROC 用 mean ± SD 样式
- 预期导出（给 reexport_check 用）：`out/figures/<kind>/<fig>.{pdf,svg,png,source.json}`（`<kind>` = main / supp） + 每个 panel 的
  `out/panels/<fig>/<fig>_<panel>.{pdf,svg}`（尺寸同组图中该 panel，不带 a/b/c 序号）
### Task K+1 依赖全部图的收尾（来源索引表、QA_SUMMARY）
合并全部图后在主分支重建。

## 执行顺序
共享层 → 锚点 → 并行波（每波 ≈4）→ 收尾 → 终审。

## 自检
- [ ] spec 每个 panel / 表都有任务覆盖
- [ ] 偏离已列出并有理由
- [ ] 无占位符（TBD、…）
- [ ] 接口一致：任务间函数签名、文件名、prov 键名一致
```

## 冲突扫描表（写进台账，派 Task 1 前完成）

| Pair / task | Produces vs consumes | Finding | Ruling |
|---|---|---|---|
| T1 → 全部 | Reader / export.save 签名 | … | … |
| T3 self | 测试断言 vs 代码 | … | … |
| Tk ↔ Tj | 同写一个图注文件？ | … | 拆分为 per-fig 文件 |

必查项：QA 审计与 panel 标签误报；只读根之外的数据；依赖全部图的任务；非 git 目录；共享文件写者。
