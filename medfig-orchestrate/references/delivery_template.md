# 交付模板（delivery template）

交付在终审修复 + 范围复审之后、主 checkout 上全部重导出（reexport_check 退出 0）之后写。
文件：`out/DELIVERY.md`（中文项目可用 `DELIVERY_ZH.md`）与 `out/QA_SUMMARY.md`。

## DELIVERY
```
# <项目> 图表交付说明（<日期>）

## 目录
- out/figures/main/：主图，每图 .pdf / .svg / .png（600 dpi）/ _grayscale.png / .source.json
- out/figures/supp/：附图，同上
- out/panels/<fig>/：每个 panel 的独立导出 <fig>_<panel>.pdf / .svg（可编辑，尺寸同组图中该 panel，无 a/b/c 序号）
- out/tables/：每表 .csv / .md / .tex / .source.json
- out/QA_SUMMARY.md：逐图 QA
- 生成脚本、共享库、图注文件的位置
- 复跑：<解释器> figures/main/figN.py；<解释器> -m pytest tests -q

## 主图 / 附图 / 表
| 图 | 科学作用（一句话结论） |
|---|---|

## 相对规格的偏离
- <图/panel>：<改了什么> —— <为什么>（对应台账 Ruling）
- 非标准宽度、增减 panel、换图型都要列。

## 全部裁决（Rulings）
按台账时间顺序，台账里每一条 `Ruling:` 都在这里，一条不漏：
1. <决定> — <为什么> — cost if wrong: <代价>

## 已知局限
- 研究设计限制（如无前瞻队列、部分队列类别不全、样本重叠；探索性质写进稿件 Methods，不写开发史）
- 工具限制（如某项检查被跳过及原因、PNG 未经 agent 目视）

## 目视检查清单（eye-check，请用户亲自看）
自动 QA 只查几何与文字，看不出拉伸、色阶、视觉拥挤。
| 文件 | 重点看什么 |
|---|---|
| out/figures/main/figN.png | 影像是否拉伸；共享色阶是否一致；标签是否拥挤 |
| out/figures/main/figN_grayscale.png | 灰度下各组是否可区分 |
| out/figures/main/figN.png | panel 内左右留白是否过多（内容应占约 85% 以上）；图例是否单独占侧栏 |
| out/figures/main/figN.png | 每个 panel 的数据图元是否有彩色（Okabe-Ito），而非全黑白灰 |
| out/panels/figN/*.pdf | 与组图中对应 panel 尺寸一致、无序号、文字可选 |
```

## QA_SUMMARY
```
# QA summary（<日期>，HEAD <sha7>）
测试：<命令> → <k> passed
| 图/表 | audit_layout | geometry | banned | check_figure | 尺寸 (in) | 备注 |
|---|---|---|---|---|---|---|
```
每行数字来自本次重导出的 source.json，不从旧报告抄。

## 最终回复给用户（主控）
- 交付文件路径
- "Rulings I made"：与 DELIVERY 裁决节同一清单，每条带 cost if wrong
- 目视检查清单的文件与重点
- 残留未决项（终审残留、parked 项）
