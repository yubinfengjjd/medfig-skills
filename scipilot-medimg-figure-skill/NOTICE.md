# NOTICE

本 skill 派生自 **scipilot-figure-skill**（MIT License，© 原作者，见 `LICENSE`）。

- 上游仓库：https://github.com/Haojae/scipilot-figure-skill
- 派生基线：commit `43098dd`（v2.1.0），派生日期 2026-09-29

## 与上游的差异

新增文件
- `scripts/image_io.py`：影像读取、位深处理、sha256、尺寸校验、整图线性调整
- `scripts/image_panel.py`：JSON 规格驱动的医学影像 panel 渲染
- `scripts/image_qa.py`：影像专用程序自检
- `references/image_panels.md`：影像 panel 的决策与规则
- `references/image_integrity.md`：图像完整性、披露与患者信息
- `requirements.txt`：依赖说明（可选依赖分开列出）
- `NOTICE.md`：本文件

修改文件
- `SKILL.md`：name/description、标题，文末新增「医学影像 panel 工作流」
- `scripts/check_figure.py`：含影像区块时豁免"SVG 嵌入位图"警告；修复 Type0 字体嵌入误报
- `references/visual_review.md`：追加影像读图清单

同步上游更新时，按上述"修改文件"清单手动合并，不要整目录覆盖。
