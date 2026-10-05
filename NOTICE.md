# NOTICE

medfig-skills 以 MIT 许可证发布（见 `LICENSE`）。以下部分借用或参考了第三方项目：

| 来源 | 许可证 | 用在哪里 | 方式 |
|---|---|---|---|
| [taoge946/academic-figure-patterns](https://github.com/taoge946/academic-figure-patterns) | MIT | `stats.structure_strength`、超越曲线 / 配对散点 / 分箱中位数、规格 counterfactual 字段、反模式条目 | 改写，保留出处注释 |
| [JRBCH/spiffyplots](https://github.com/JRBCH/spiffyplots) | MIT | `figkit.journals` 的条目格式 | 格式参考，数值逐条复核 |
| [yinliang420/Scientific_Illustration](https://github.com/yinliang420/Scientific_Illustration) | MIT | `medfig-plan/scripts/spec_check.py` | 按思路重写 |
| [enesgul23/scientific-figure-skills](https://github.com/enesgul23/scientific-figure-skills) | MIT | 期刊条目 VERIFIED / ESTIMATED 状态 | 思路 |
| [O0000-code/SSCI-Plots](https://github.com/O0000-code/SSCI-Plots) | MIT | `compare.p_bracket` | 思路，改为精确 P 值 |
| [xiao-yuling/sci-figure](https://github.com/xiao-yuling/sci-figure) | MIT | Bland–Altman 图型、"红绿只表示方向"规则 | 思路，代码重写 |
| [senlanke/figures4papers](https://github.com/senlanke/figures4papers) | 未声明 | soft 主题的视觉风格 | 只借鉴风格，未使用其代码 |
| [myzhao0114-del/scientific-figure-skill](https://github.com/myzhao0114-del/scientific-figure-skill) | 未声明 | `medfig-plan/scripts/data_health.py` | 只借鉴思路，未使用其代码 |

## 包含的第三方技能

`scipilot-medimg-figure-skill/` 派生自 [Haojae/scipilot-figure-skill](https://github.com/Haojae/scipilot-figure-skill)
v2.1.0（commit `43098dd`，MIT，© 2026 Haojae），原许可证见 `scipilot-medimg-figure-skill/LICENSE`。
新增的医学影像 panel 脚本与文档、对上游文件的修改，逐项列在 `scipilot-medimg-figure-skill/NOTICE.md`；
继承文件的上游哈希见 `original_skill_hashes.txt`。`medfig-render` 的样式和导出调用它的脚本
（`setup_style.py`、`export_figure.py`、`check_figure.py` 等），由 `install.py` 一起安装。
