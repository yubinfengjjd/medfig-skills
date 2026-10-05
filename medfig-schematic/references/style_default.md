# 默认画风（用户给参考图时以参考图为准）

这套画风经过多轮人工迭代，用户已经确认。三行版式：研究设计 / 模型 / 一例推断与解释。模型行画成克制的 3D 网络，另外两行是实色浅底方块。下面的英文块可以直接拼进提示词，`<…>` 处换成规格里的内容。

## 1. 全局

```text
GLOBAL STYLE
- Canvas <width_mm> mm wide, landscape <W:H>, white background. Rows labelled with bold lowercase panel letters a, b, c at the top-left of each row, followed by a short bold row title on the same line (horizontal, not rotated). Rows are separated by whitespace only.
- Typography: Arial-like sans-serif, sentence case, only two text sizes (labels and smaller annotations), dark-grey text #333333, never coloured text.
- Arrows: about 2 pt, dark grey #4D4D4D, small solid arrowheads, orthogonal routing. No fat block arrows, no gradient arrows.
- No drop shadows, no glow, no glass, no reflections, no gradients, no cartoon icons, no people, no robots. At most a few simple line icons (for example a lock or a flag).
- Colour encodes meaning only: <class colours> are used only for the classes; <method accent> only for the method's own pathway; light stage tints only for training stages; everything else greys.
```

## 2. 流程行（研究设计、推断与解释）：实色方块

```text
FLAT ROWS (rows a and c)
- Each module is a rounded rectangle (small corner radius) with a solid pastel fill and no or a very thin outline; its title in bold and its content sit on that colour.
- One pastel fill per role, kept across rows (for example development / segmentation / external cohorts, training, evaluation, explanation, uncertainty).
- Cohort or dataset names as one or two lines of small text inside the card, not one box per name.
- Charts inside a module (waterfall, bars, prediction-set chips) are drawn flat inside that module's block.
```

## 3. 模型行：克制的 3D

```text
3D RULE (row b only)
- 3D is used ONLY for tensors and network layers: thin tilted slabs and stacks in one consistent oblique projection, light from the top-left, each slab with a slightly lighter top face and a slightly darker side face, flat colours.
- Operation blocks are small rounded rectangles; operators in small circles (⊗, ⊕); a tensor's shape as small text under it (for example "16 × 16 × 768").
- Frozen parts are light grey with a small snowflake above them; trained parts use the stage tint of the stage that trains them.
- Under the network: one thin line per training stage, starting with a small numbered circle (light stage tint, dark-grey numeral), spanning exactly the modules that stage trains, with a short label.
- Under the stage lines: a one-line legend in a light-grey strip explaining each symbol (slab = feature tensor, ⊗ = <operation>, × = not used, snowflake = frozen).
```

## 4. 影像位

```text
IMAGE SLOTS
- Every image is an EMPTY slot: a light-grey rectangle (#F2F2F2) with a thin dashed border, aspect ratio <2:1 for an OCT B-scan / 1:1 for a fundus or CT slice>, with its label in small text below it. Draw nothing inside the slots.
```

## 5. 文字规则

```text
TEXT RULES
English only; use exactly the labels given in this prompt and no other text; no figure title; no numbers except <allowed_numbers>; no logos, no watermarks; check spelling, especially <hard words>.
```

## 6. 为什么这样定

| 规则 | 原因 |
|---|---|
| 3D 只给模型行 | 能看出网络的形状（层数、张量、分支），但整张都 3D 会像海报，并且会和后贴的真实影像抢视觉重心 |
| 流程行用实色方块 | 白底细框太弱，模块散开以后看不出边界；浅底方块让每一步自成一块 |
| 箭头约 2 pt 实心 | 0.5 pt 细线方向感太弱；粗渐变箭头又是信息图的语汇 |
| 两级字号、sentence case、深灰字 | Title Case 加多级粗体显得像商务幻灯片 |
| 颜色只表达含义 | 阶段色用饱和蓝时会和类别蓝混淆；类别色只给类别 |
| 影像只留空框 | 生成模型画的视网膜不真实，审稿人一眼能看出；真实 B-scan 在 Illustrator 里贴入 |
| 行标题横排在字母后 | 竖排行标题占宽度、难读；顶刊多用 "a Study design" |
