# outline.yaml 格式与大纲版式

## 1. 文件结构

```yaml
project: <项目名>
language: zh            # 要点语言；小节标题英文
figures_root: out/figures      # 相对项目根；source.json / pdf / png 所在
tables_root: out/tables
captions: [docs/captions_zh.md, docs/captions]   # 图注草稿（文件或目录）
upstream_root: <可选，上游分析仓库根目录>
main_figures: [fig2, fig3, ...]                  # 每个主图至少被一个 Results 节覆盖
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
    items: [T1, S1, ST10]                        # 该节关联的图表（决定文件夹里拷什么）
    code:
      - path: tables/build_tables.py
        role: 表格
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
    items:                                       # 图 / 表清单
      - ref: Fig2a
        what: 骨干表示 PCA 密度等高线
    boundaries: [...]                            # 措辞边界
    code: [...]
numbers:                                         # Results 里每个数的出处
  - text: "0.983"                                # 大纲里写出的字符串（含 %, 区间两端分别登记）
    source: fig6.source.json:values.b_auc.all.backbone   # 或 table:T2.csv:<列>@<行筛选>
    tol: null                                    # 可选；默认按写出的小数位四舍五入比较
    magnitude: false                             # 可选；正文写的是带符号源值的大小（"低约 0.047"）
```

## 2. 引用写法

- 图 panel：`Fig2a`、`Fig2a-c`（展开为 a、b、c）、`S5a`；整图：`Fig2`、`S5`。
- 表：`T1`、`ST05`。
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
- 代码路径用等宽字体；推测项后缀"（推测）"，缺失项写"TODO"。
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
