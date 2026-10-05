# schematic.yaml 格式

一张示意图一个工作目录（放在项目之外），目录里放 `schematic.yaml`。三个脚本都读它：`prompt_check` 用它核对提示词，`image_check` 用它核对出图，`round_pack` 在打包时自动调用前者。

```yaml
figure: Fig 1
size: {width_mm: 180, aspect: "3:2"}

# 每个提示词里可能出现的色值都要登记；prompt_check 发现未登记的 #RRGGBB 就报错
palette:
  class:   {ClassA: "#009E73", ClassB: "#0072B2", ClassC: "#D55E00"}
  method:  {accent: "#AA3377"}
  stage:   {s1: "#D9D2E9", s2: "#D6E4EE", s3: "#F0D5E2"}
  role:    {development: "#E0E0E0", auxiliary: "#E6D9F2", external: "#FDECD4"}
  neutral: {text: "#333333", line: "#4D4D4D", slot: "#F2F2F2"}
distinct_groups: [class]        # 这些颜色必须在图里出现，且转灰度后仍可区分

# 图里允许出现的全部文字；按行分组只是为了好读
labels:
  a: ["Study design", "Development", "External test", "frozen model", ...]
  b: ["Model", "ViT encoder", "16 × 16 patches", "12 transformer blocks", ...]
  c: ["One external scan, explained", "{ClassB}", ...]
allowed_numbers: ["1", "2", "3", "12", "16", "768", "90%"]
image_slots: ["Input scan", "External scan", "Attribution map"]

forbidden_patterns: ['\bE[0-2]\b', '\bH[1-5]\b']     # 内部代号，大小写敏感
ignore_quotes: ["Keep everything else"]           # 提示词里加引号、但不是图内文字的短语
```

## 字段规则

| 字段 | 规则 |
|---|---|
| `labels` | 图内出现的每一个字符串，原样写（含大小写、空格、× 号）。提示词里所有加引号的文字都必须在这里，否则 `prompt_check` 报错 |
| `allowed_numbers` | 只放**设计数字**：结构参数（层数、维度、patch 数）、方法设定（90% 目标覆盖率）、阶段编号。结果数字（AUC、准确率、样本量）不放，示意图不出现结果 |
| `image_slots` | 必须也在 `labels` 里；提示词提到影像位时必须写明是空框 |
| `palette` | 和数据图共用一套色板（`figkit.toml` 的类别色、方法色）；阶段色、角色色是低饱和底色 |
| `distinct_groups` | 一般只放类别；`image_check` 检查每个颜色都出现、两两之间 L* 差 ≥ 10 |
| `forbidden_patterns` | 抄 `figkit.toml [qa] forbidden_patterns`，再加只在示意图里出现的代号 |

## 结构事实不放在 yaml 里

层数、维度、哪个阶段训练哪个模块，这些写进第一轮的 `round1.md` 的"结构事实"表。每条注明出处（配置文件键、代码文件与函数），从代码核对，不只信文档。用户的口述与代码冲突时，先按代码写，再把冲突告诉用户。
