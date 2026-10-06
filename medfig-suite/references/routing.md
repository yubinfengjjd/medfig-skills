# medfig-suite 路由细则

两条分支，按顺序判定，命中即停。判定依据只看：素材类型、是否已有规格、图的数量。

## 分支 A：纯影像网格

全部满足才直接用 `scipilot-medimg-figure-skill`：
- 素材是已导出的 PNG / JPG / TIF（OCT、CT、MRI、病理、眼底等）。
- 叠加物只有掩膜、轮廓、热力图（Grad-CAM 等）、放大框、箭头、比例尺。
- 不含 ROC、森林图、混淆矩阵等统计 panel。
- 只要这一张图，不属于整套规划。

任一不满足（例如影像 + 统计混排、整套中的一张影像图）→ 分支 B。medfig-render 在影像 panel 内部仍会调用 scipilot 的能力，但由 medfig 负责整图。

## 分支 B：medfig 主线

| 现状 | 去向 |
|---|---|
| 只有结果资产，没有图表规格 | medfig-plan → 产出 `docs/<date>-figure-set-design.md`，用户审阅后再往下 |
| 规格已确认，只画一张 | medfig-render |
| 规格已确认，多张或整套 | medfig-orchestrate（逐图任务内部用 medfig-render） |
| 规格存在但与数据、文档口径冲突 | 回 medfig-plan 修规格，再继续 |
| 已出图，只要按清单复审 | medfig-orchestrate 的 `references/review_checklist.md` |
| 规格里的"示意图（外部绘制）"要画：研究设计图、架构图、流程示意图 | medfig-schematic（写生图提示词、逐轮评估） |
| 要把已有参考图 1:1 复刻成可编辑矢量，或在 Illustrator 里原生重画并保留可编辑文字 | medfig-illustrator（本地真矢量重建 + 原生播放 + 交付校验） |

"规格已确认"指：逐 panel 写了结论、数据文件与列、图型；用户已审阅。只有口头想法不算规格。

## 边界例子

| 用户说法 | 去向 |
|---|---|
| "帮我把这些结果做成论文的整套 Figure" | medfig-plan |
| "规格定好了，按 Fig 3 的 spec 画出来" | medfig-render |
| "8 张图的规格都确认了，批量出图" | medfig-orchestrate |
| "OCT B-scan 叠分割掩膜，排成 3×4 网格" | scipilot-medimg-figure-skill |
| "Grad-CAM 热力图 + ROC 曲线放一张图" | 分支 B（混排） |
| "用 ChatGPT 画 Fig 1 的研究设计和网络架构示意图" | medfig-schematic |
| "这是 GPT 出的架构图，帮我评估再出下一轮提示词" | medfig-schematic |
| "按这张参考图在 Illustrator 里 1:1 复刻，要可编辑的矢量图" | medfig-illustrator |
| "把这个流程图的空框用我们项目的真实影像填上" | medfig-illustrator（有参考图要复刻）；没有参考图、只是新画 → medfig-schematic |
| "CONSORT 流程图，带真实入组人数" | 不在范围（人数要逐格核对，交给作图软件），告诉用户 |
| "用 matplotlib 代码画网络结构图" | 不在范围，告诉用户 |
| "这组 CSV 用什么图好"（非医学、单图） | 不在范围，告诉用户 |

## 失败处理

- 下游技能未安装：告诉用户缺哪个技能及安装方式，不临时手写替代流程。
- 输入缺失（无 `figkit.toml`、无规格、掩膜语义无出处）：先问用户，不猜。
- 路由判定前后矛盾：从分支 A 重新判定。
