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
