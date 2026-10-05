# 医学影像 panel —— 布局规格参考

> 脚本：`scripts/image_panel.py`。输入是一份 JSON 规格；脚本负责全部排版、
> 叠加层渲染、自检、导出与溯源。Agent 的职责是**写好规格**并读懂预览图做复核。

## 1. 运行

```bash
python scripts/image_panel.py spec.json
```

写出 `<out_dir>/<name>` 的 `_preview.png`、`.qa.json`、`.pdf`、`.svg`、`.png`（600 dpi）、
`_grayscale.png`、`.provenance.json`、`.caption_methods.md`。

## 2. 顶层结构

```jsonc
{
  "figure":  {"journal": "nature", "width": "double",   // single|double|1.5
              "name": "fig2a", "out_dir": "...", "panel_label": "a"},
  "grid":    {"rows": ["Case 1", "Case 2"], "cols": ["B-scan", "Mask", "CAM"],
              "gap_mm": 1.0},
  "groups":  {"grp": {"intensity": {"mode": "percentile", "lo": 0.5, "hi": 99.5}}},
  "label_maps": {"mymap": {"source": "数据集文档第X节",
                 "classes": {"115": {"name": "IRF", "color": "#F0E442"}}}},
  "cells":   [ {"row": 0, "col": 0, "group": "grp", "image": "...png",
                "crop": [x, y, w, h],          // 原图像素坐标，可省略
                "overlays": [...], "zooms": [...], "arrows": [...],
                "scale_bar": {...}, "corner_text": {...}} ]
}
```

- `crop` 是**原图像素坐标** `[x, y, w, h]`；不同行可用不同 crop（如各患者视网膜
  位置不同），但同图跨列必须一致，否则不是同一视野。
- `group` 相同的一组格子共用同一亮度/对比度窗（percentile 在组内联池计算），
  保证可比较；参数自动写进 provenance 与图注。

## 3. 叠加层（overlays，按数组顺序绘制）

### label_mask —— 类别掩膜
```jsonc
{"type": "label_mask", "path": "semseg.png", "label_map": "mymap",
 "show": [115, 138, 161],          // 只画这些灰度值对应的类
 "draw": "fill|contour|both", "alpha": 0.5}
```
- **必须给 `label_map`** 且每个要画的灰度值都要有名字——语义靠你提供，
  绝不从灰度值猜测。缺名字的类会 FAIL。
- 掩膜与原图尺寸不一致 → FAIL 停止出图（绝不自动缩放掩膜）。

### contour —— 二值轮廓（金标准 vs 预测）
```jsonc
{"type": "contour", "path": "pred_mask.png",
 "role": "prediction",             // ground_truth→绿实线 / prediction→橙虚线 / other
 "values": [1],                    // 可选；缺省 >0
 "lw": 0.9, "label": "pred."}
```

### fill —— 单色半透明填充
```jsonc
{"type": "fill", "path": "roi.png", "color": "#009E73", "alpha": 0.35}
```

### heatmap —— Grad-CAM 等
```jsonc
{"type": "heatmap", "path": "arrays.npz", "key": "cam_predicted",
 "cmap": "magma",                  // 只允许 magma / inferno / viridis
 "normalize": "per_image",         // per_image | shared | fixed
 "norm_group": "default",          // shared 时同组共用 vmin/vmax
 "upsample": "bilinear",           // bilinear | nearest
 "alpha": 0.55, "transparent_below": 0.05,
 "exclude_image_values": [255]}    // 可选：不叠加在等于这些值的原图像素上（配准补白）
```
- `per_image` 每图归一化到自己的 max：看得清但**跨图不可比**；
  `shared`/`fixed` 可比但弱信号会消失。图注会如实写明归一化方式——**两者都要存，
  投稿用 shared 或注明 per_image 仅供定位参考**。
- 有热力图就必须有 colorbar（脚本强制，缺了 FAIL）。

## 4. 局部放大（zooms）

```jsonc
"zooms": [{"box": [130, 105, 115, 65], "factor": 2, "corner": "lower right"}]
```
- `box`：原图坐标；`factor` 整数 ≥2，放大图用 nearest 保持像素感；
  边框颜色自动与源框同色（Okabe-Ito 轮换）。
- `corner: auto`（默认）自动找不挡源区的角；放不下会 FAIL 并提示改 factor/位置。
- 放大图里叠加层照常绘制——确认配准正好靠它。

## 5. 箭头 / 角标文字 / 比例尺

```jsonc
"arrows": [{"to": [170, 150], "offset": [-60, 45], "text": "PED"}]
"corner_text": {"corner": "upper left", "text": "Pred: DME"}
"scale_bar": {"pixel_spacing_um": 11.74, "length_um": 500, "axis": "x"}
```
- 坐标一律**原图像素**；箭头自带白描边，尖端自动留偏移不压目标。
- **比例尺**：不给 `pixel_spacing_um` 就不画（记 INFO，绝不伪造）；
  各向异性像素只画横向并在图注注明轴。

## 6. 自检层级

1. `image_panel.py` 渲染时即做 Q1–Q6（尺寸不符 FAIL、ppi<300 WARN、
   无 colorbar/图例 FAIL、放大框配色 FAIL、缺 pixel_spacing INFO）。
2. `check_figure.py` 终审导出文件：影像 panel 的 SVG 位图嵌入自动豁免为 INFO
   （依据同名 `*.provenance.json` 的 `panel_type` 标记）。
3. AI 读图复核：读 `_preview.png` 与 `_grayscale.png` 对照
   `references/visual_review.md` + `image_integrity.md` 清单。

## 7. 分辨率实务

OCT B-scan 通常只有 ~500 px 宽。300 ppi 下最大显示宽度 ≈1.7 in——
双栏 2 列布局天然会触发 250 ppi 警告。**这是源分辨率上限而非缺陷**：
- 合理做法：更少列、更紧裁剪、接受 WARN 并在交付说明中写明。
- 错误做法：用 AI 超分/插值"提升"分辨率应付检查——伪造细节，绝对禁止。
