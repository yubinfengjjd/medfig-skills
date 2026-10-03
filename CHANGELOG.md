# Changelog

## 0.1.0 (2026-10-07)

首个公开版本。

- 四个技能：`medfig-suite`（路由）、`medfig-plan`（规划）、`medfig-render`（单图渲染，内含 figkit 库）、`medfig-orchestrate`（批量出图）。
- figkit：配置、样式、溯源（source.json + SHA-256）、导出与质检闸门（几何、字号、真减号、留白、纯文字 panel、S3 着色、色差、图内文字审计、柱轴截断）。
- 20 个 panel 配方（`medfig-render/examples/gallery/INDEX.md`）。
- 可选 soft 主题（一主多淡、平涂柱、柱顶数值、断轴标记）。
- `figkit.journals` 期刊规格表（Nature、npj、Science、Cell、Elsevier、Medical Image Analysis、IEEE），每条带来源、核对日期和 VERIFIED / ESTIMATED 状态。
- 规划自检脚本 `data_health.py`、`spec_check.py`。
