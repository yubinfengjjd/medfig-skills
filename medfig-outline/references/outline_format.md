# outline.yaml 格式与大纲版式

## 1. 文件结构

```yaml
project: <项目名>
language: zh            # 要点语言；小节标题英文
figures_root: out/figures      # 相对项目根；source.json / pdf / png 所在
tables_root: out/tables
captions: [docs/captions_zh.md, docs/captions]   # 图注草稿（文件或目录）
upstream_root: <可选，上游分析仓库根目录>
main_figures: [fig2, fig3, ...]                  # 每个主图至少被一个 Results 节覆盖（design_assets 除外）
design_assets: [T1, Fig1, ST01]                  # Methods 能引用的设计资产：数据集表、研究设计图、方法类附表
pending: [Fig1]                                  # 可选：外部绘制、还没导出的图（引用照常排序，不查文件）
excluded:                                        # 可选：导出了但不进稿件的资产，必须写理由
  - {ref: ST12, reason: 溯源索引，属于过程材料}
allow_numbers: ["95%", "16"]                   # 可选：全大纲放行的设计常数 / 区间写法（不是结果）
methods:
  - id: "2.1"
    title: Cohorts, study design and data integrity
    short: Cohorts_design_integrity            # 文件夹短名
    focus:                                       # 写作重点：主题 -> 要点（不写结果数字）
      - topic: 研究类型与任务
        points: [...]
    foreshadow: [...]                            # 可选：为后文埋的伏笔
    allow_numbers: ["0–4", "512"]                # 可选：focus 里允许出现的非结果数字
    items:                                       # 本节引用的设计资产（只能是 design_assets）
      - {ref: T1, what: 各队列的角色、设备与规模}
    code:                                        # 只列分析代码（计算）；绘图 / 表格脚本不列
      - path: <upstream>/src/x.py
        role: 计算
        guess: true                              # 推测的上游代码
results:
  - id: "3.1"
    title: <一句话发现，英文>
    subtitle: <中文副标题>
    short: Cohorts_domain_shift
    paragraphs:
      - label: 第一段
        optional: false
        claim: 这一段要证明的结论（一句）
        points: [...]                            # 写作要点；数值写约数 / 区间
        cites: [Fig2a, Fig2b, T1]
    items:                                       # 图 / 表：本节首次引用的每个资产一行，写它在科学上说明什么
      - ref: Fig2
        what: 外部队列在骨干表示中各自成簇，域差异在概念层之前就存在
    boundaries: [...]                            # 措辞边界
    code: [...]                                  # 只列分析代码（计算）
numbers:                                         # Results 里每个数的出处
  - text: "0.983"                                # 大纲里写出的字符串（含 %, 区间两端分别登记）
    source: fig6.source.json:values.b_auc.all.backbone   # 或 table:T2.csv:<列>@<行筛选>
    tol: null                                    # 可选；默认按写出的小数位四舍五入比较
    magnitude: false                             # 可选；正文写的是带符号源值的大小（"低约 0.047"）
```

## 2. 引用写法

- 图 panel：`Fig2a`、`Fig2a-c`（展开为 a、b、c）、`S5a`；整图：`Fig2`、`S5`。
- 表：`T1`、`ST05`。
- 要点文字里写的 `Fig 3a`、`Fig S5b`、`Table 2`、`Table S5`、`图 S1`、`表 2` 也算引用，参与次序检查（§7）。
- 检查脚本按 `figures_root` 下的 `<name>.source.json` 与 `values.panels`（或 panel 文件）确认 panel 存在，按 `tables_root` 下的 `<name>.csv` 确认表存在。

## 3. 数字登记

- `source` 形式：
  - `<fig>.source.json:<键路径>`：键用 `.` 连接，列表用 `[i]`，例如 `fig4.source.json:values.b_recall_mean.Edema`。
  - `table:<name>.csv:<列>@<列>=<值>[&<列>=<值>]`，例如 `table:T2.csv:bacc_mean@cohort=Internal test&unit=scan`。
- 比较规则：按大纲里写出的小数位四舍五入后相等；百分数 `92.7%` 与源值 0.927 自动换算；`tol` 给出时改用绝对误差。
- 约数（"约 0.31"）同样登记；"约一个数量级"这类非数值说法不登记。
- 计数（n = 13,859）登记时去掉千分位逗号比较。

## 4. docx 版式（照参考大纲）

- 不用 Word 标题样式编号；小节标题加粗（Methods 14 pt、Results 14 pt），Results 标题下一行中文副标题（括号，11 pt）。
- 小标题："写作重点："（Methods）、"写作要点"（Results）、"图 / 表"、"相关代码"、"措辞边界"，加粗。
- 要点用缩进层级（主题 → 要点 → 子要点），每级左缩进 0.74 cm；段落标签"第一段："单独一行加粗。
- 代码路径用等宽字体；推测项后缀"（推测）"，缺失项写"TODO"。只列分析代码（计算），不列绘图 / 表格脚本。
- "图 / 表"每行 = 资产名 + 它说明什么（`Fig 2：外部队列在骨干表示中各自成簇…`）；外部绘制、还没导出的标"（外部绘制，待交付）"。Methods 的写成"引用图 / 表："。
- 正文字号 10.5 pt，中文宋体 / 英文 Times New Roman；A4，页边距 2.54 cm。
- 文件不带宏、不嵌图（图在分节文件夹里）。
- 段落行：`第一段：` 加粗 + 本段结论 + 括注出处（`（Fig 4a、Table 2）`），要点直接列在下面；不另起"引用："行。
- 相关代码每个角色一行（`绘图：fig4.py、s03.py`），不逐文件换行。

## 5. 写法：提示作者写什么，而不是替作者写

大纲是写给作者看的提示，每条要点是一句"写什么"的指令，不是待抄进正文的结果句。数值精确值留在图注和表里，大纲只点出写正文时必须提到的那一两个数。

| 规则 | 限值（`outline_check.py` 检查，可在顶层 `style:` 覆盖） |
|---|---|
| 每节段落数 | Results ≤ 3 |
| 每段要点数 | ≤ 3（Methods 每个主题同样 ≤ 3） |
| 每条要点长度 | ≤ 70 字 |
| 每条要点里的结果数字 | ≤ 2 |
| 每段结果数字合计 | ≤ 4，其余写"完整数值见 Table X" |
| 要点开头 | 不以"引用 Fig …"开头（出处写进 `cites`）；同一节内同一开头不超过 3 次 |

- 要点用动词开头说明要做的事：说明、对比、强调、点出、交代、一句话带过、留给 Discussion。
- 一段只讲一件事；第二件事另起一段，或判断它是否该放进图注。
- 队列逐个列数值的句子改成"点出最高 / 最低的那个 + 范围"，逐队列数值交给表格。
- Methods 只写结构与选择理由（为什么用 cluster bootstrap、为什么 BH 校正），参数细节写"见补充方法"。
- 措辞边界每节 ≤ 3 条，只写这一节最容易写过头的地方。
- 引用曲线 panel（ROC / PR）的段落：点出 AUC 及其 95% CI（多 seed 写 mean ± SD）和它在跟谁比（对照模型、内部 vs 外部），不只说"曲线较好"。
- 引用病例矩阵的段落：一条要点说明矩阵里也放了误判病例、它们的图和正确病例有什么不同；不写"代表性病例表明……"这类以少概全的句子。
- 有病例矩阵的图（`source.json` 的 `values.case_selection`）：在 Methods 评估 / 统计小节用一条要点交代选例规则——按什么分层、固定 seed 随机、每组几例（其中误判几例）、候选池是什么。`outline_check.py` 要求 Methods 的 focus 里同时出现该 seed 和"随机 / random"；seed 和每组例数属于设计常数，不算结果数字。

示例（同一段，改写前 → 改写后）：

```
改写前（像数据表）
第一段：三类齐全的外部队列保持较高 BACC；Site D 最低。
  引用 Fig 5b、T2：扫描层 BACC Site A 约 0.938、Site B 约 0.929、Site C 约 0.934；
  Site D 约 0.802、Site E 约 0.859（两者只有两类）。
  组层 BACC 普遍高于扫描层，例如 Site D 约 0.894；……
  引用：Fig5b、T2

改写后（像写作提示）
第一段：多数外部队列保持较高水平，Site D 明显偏低。（Fig 5b、Table 2）
  点出三类齐全的队列 BACC 在 0.929–0.938 之间，Site D 约 0.802。
  交代 Site D、Site E 只有两类，结果只作描述。
  组层结果一句话带过，逐队列数值见 Table 2。
```

## 6. 骨架：按论证规划，不按图平铺

```yaml
methods:
  - id: "2.3"
    title: Training procedure
    short: Training
    subsections:                       # 小节可以继续嵌套；编号必须以父节编号开头
      - id: "2.3.1"
        title: "Stage 1: anatomy front end"
        short: Stage1
        focus: [...]
      - id: "2.3.2"
        title: "Stage 2: joint concept and classification training"
        short: Stage2
        focus: [...]
results:
  - id: "3.2"
    title: <一句话发现>                 # 大节标题必须是发现句
    subtitle: <中文副标题>
    short: External
    subsections:
      - id: "3.2.1"
        title: External performance and error direction   # 小节可用短标题
        subtitle: 外部性能与错误方向
        short: Performance
        paragraphs: [...]
```

- **Methods 顺序**：数据 → 模型结构 → 训练过程（按阶段拆小节）→ 评估与统计 → 附加分析。节数由内容决定。
- **Results**：5–8 个大节（`style.results_min_sections` / `results_max_sections`，默认 5 / 8），每节回答一个问题；一节可用多张图，一张图的 panel 可分到不同节。少于 5 节时在顶层写 `results_fewer_sections_reason: <课题思路为什么只需要这么几节>`，否则报错。
- 父节可以只有标题（内容全在小节里），也可以有一句总述段落。
- 检查脚本报错的平铺信号：Methods 与 Results 节数相同且每个 Results 节恰好一张主图；只有一个小节；末级节少于 2 条要点；小节编号不在父节之下。
- 没有文档依据、只从代码 / 配置推断的细节，要点末尾标"（待核）"。

## 7. 引用次序与编号

稿件按阅读顺序（Methods → Results，节内从上到下；段内先结论行的出处，再要点里写到的）编号。检查脚本按同一顺序找每个资产的**首次引用**：

| 规则 | 说明 |
|---|---|
| 四个序列各自从 1 连续编号 | 主图（Fig 1, 2 …）、主表（Table 1, 2 …）、附图（Fig S1, S2 …）、附表（Table S1, S2 …）首次引用的编号必须是 1, 2, 3 …，不跳号、不倒序 |
| panel 首次引用按字母顺序 | 同一张图先引 a，再 b、c …；不能先 d 后 a。引整图（`Fig3`）等于按顺序引全部 panel |
| 后续引用不限 | 首次引用之后，回指前面的图表或 panel 不受次序限制 |
| 每个资产都被引用 | `figures_root` / `tables_root` 下每张图、每个 panel、每张表都要被引用（正文和补充材料都算），`pending` 的图也要被引用；不进稿件的写进 `excluded` 并给理由（过程记录、溯源索引之类）。图的 `source.json` 必须有 `values.panels`，否则无法核对 panel 覆盖，脚本报错 |
| 引用清单 | `outline_check` 最后打印 `coverage: N/N`；`outline_build` 在大纲末尾生成"图表引用清单"表（资产、panel、首次引用、引用小节、状态） |
| Methods 只引设计资产 | 数据集表、研究设计 / 框架图、方法类附表（如不可估计项清单）列进 `design_assets`，在骨架确认时定；其余结果一律放 Results |
| 每个资产一行"图 / 表" | 在首次引用它的那一节写一行：它在科学上说明什么，不写怎么画的 |

次序不对时有两种改法，按课题叙事选：

1. **调叙事**：换段落或要点的顺序（例如把"Fig 3a 只作示意"挪到第一段开头）；或者把提前出现的引用推后（3.1 不提 Fig 6b，放到 3.5 再讲）。
2. **改编号**：叙事顺序更合理时改资产编号（交换 panel 字母、附图 / 附表改号）。检查脚本会给出改号建议（`Fig S7 → Fig S5, …`）。改号表在骨架确认时给用户确认，回到 medfig-render 改图（panel 顺序、文件名、图注和表注里的互引）并重新导出，再写大纲。大纲里的编号永远与导出文件一致。

示意图这类外部绘制、还没导出的图写进 `pending`，照常参与排序（Methods 引 Fig 1 后 Results 从 Fig 2 开始），不查文件。
