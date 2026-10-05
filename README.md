# medfig 技能集合

[![tests](https://github.com/yubinfengjjd/medfig-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/yubinfengjjd/medfig-skills/actions/workflows/tests.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

面向医学 / 临床 AI 论文的图表技能：五个 medfig 技能，加上它们依赖的 `scipilot-medimg-figure-skill`，一条命令装到 Claude Code 与 Codex 的技能目录后按触发条件自动使用。

| 技能 | 作用 |
|---|---|
| `medfig-suite` | 入口与路由：判定任务交给哪个技能，列出下游需要的输入，本身不画图 |
| `medfig-plan` | 规划整套图表：panel 选型、图型多样性、表格规划，产出 `docs/<date>-figure-set-design.md` |
| `medfig-render` | 按规格渲染单张图；自带 `lib/figkit`（配置、样式、QA、导出与各类 panel） |
| `medfig-orchestrate` | 批量出多张图：并行 worktree、审查清单、台账与交付模板 |
| `medfig-outline` | 图表定稿后写 Methods / Results 写作大纲（docx + md），数字对照 `source.json` 回核，并按小节归档图、表、图注与代码 |
| `scipilot-medimg-figure-skill` | 依赖技能：期刊样式、导出与文件自检脚本（`medfig-render` 调用），以及医学影像 panel（影像 + 掩膜 / 轮廓 / 热力图，JSON 规格驱动）。派生自 [Haojae/scipilot-figure-skill](https://github.com/Haojae/scipilot-figure-skill)（MIT），差异见其 `NOTICE.md` |

## 路由

- 只要一张纯影像网格（已导出的 PNG/JPG/TIF + 掩膜/轮廓/热力图/放大框/比例尺，无统计图混排）→ `scipilot-medimg-figure-skill`。
- 其他情况：还没有规格 → `medfig-plan`；已有规格、单张图 → `medfig-render`；图表定稿后写作大纲 → `medfig-outline`；多张图 → `medfig-orchestrate`（内部逐张调用 `medfig-render`）。

示意图、流程图、架构图和非医学图表不在范围内。

## 前置条件

- Python ≥ 3.11（低于 3.11 需安装 `tomli`，`requirements.txt` 已按版本处理）。
- Python 依赖：`pip install -r requirements.txt`（版本固定为测试通过的组合）；跑测试另装 `pip install -r requirements-dev.txt`。
- `scipilot-medimg-figure-skill` 已包含在本仓库，由 `install.py` 一起安装，不需要另外下载。
- 可选：Arial 字体（期刊默认字体；缺失时 matplotlib 回退到 DejaVu Sans 并给出警告）。

## 安装 / 更新 / 卸载

```bash
git clone https://github.com/yubinfengjjd/medfig-skills.git
cd medfig-skills
pip install -r requirements.txt
python install.py
```

以后更新：`git pull && python install.py --update`。

`install.py` 只用标准库，只复制上述六个技能目录，并排除 `__pycache__`、`*.pyc`、`.pytest_cache`、`.git` 以及 `examples/**/out`、`examples/**/data` 等生成物。默认目标为 `~/.claude/skills` 和 `~/.codex/skills`。

```bash
python install.py --dry-run          # 只打印计划（复制、备份、目标），不改动任何文件
python install.py                    # 安装；已有的同名技能先备份
python install.py --update           # 仅重装清单哈希有变化的技能
python install.py --verify           # 对比源与已安装文件的 SHA-256
python install.py --uninstall        # 把已安装的这六个技能移到备份目录（从不删除）
python install.py --target D:/x/skills --target D:/y/skills   # 覆盖默认目标，可多次给出
```

- 备份位置：`~/skill_backups/medfig_<时间戳>/<目标名>/<技能名>`（可用 `--backup-root` 修改），运行时会打印。
- 复制后逐文件做 SHA-256 校验，并写入 `<目标>/<技能>/.medfig_install.json`（版本 = 源仓库 git 短 SHA，取不到时为 `unknown`；时间戳；文件数；清单哈希）。
- 任何校验失败时退出码非零。
- 只处理这六个技能目录，目标根目录中的其他技能不会被读写。已装过上游或旧版 `scipilot-medimg-figure-skill` 的，安装时会先备份再替换。

## Codex 用户：设置 FIGKIT_LIB 与 scipilot_scripts

图脚本模板默认从 `~/.claude/skills/medfig-render/lib` 导入 figkit。只装在 Codex 时需设置环境变量：

```bash
export FIGKIT_LIB=~/.codex/skills/medfig-render/lib          # bash / Git Bash
```

```powershell
$env:FIGKIT_LIB = "$HOME\.codex\skills\medfig-render\lib"  # PowerShell（当前会话）
[Environment]::SetEnvironmentVariable("FIGKIT_LIB", "$HOME\.codex\skills\medfig-render\lib", "User")  # 永久
```

`scipilot_scripts` 默认指向 `~/.claude/skills/scipilot-medimg-figure-skill/scripts`。scipilot 只装在 Codex 时，在项目的 `figkit.toml` 里写：

```toml
scipilot_scripts = "~/.codex/skills/scipilot-medimg-figure-skill/scripts"
```

`FIGKIT_TOML` 可指向项目的 `figkit.toml`；figkit 不含硬编码路径，一律从该配置读取。

## 运行测试

```bash
python -m pytest tests -q -p no:cacheprovider                 # 技能格式校验、泄露扫描 + 安装器测试
python -m pytest medfig-render/tests -q -p no:cacheprovider   # figkit 库、回归与最小示例
python -m pytest medfig-orchestrate/tests -q -p no:cacheprovider
python -m pytest medfig-outline/scripts -q -p no:cacheprovider
python -m pytest scipilot-medimg-figure-skill/tests -q -p no:cacheprovider   # 影像 panel / 样式 / 导出冒烟测试
```

测试全部使用合成数据；安装器测试只写入临时目录。`medfig-render` 的部分测试需要先运行 `python install.py`（它们调用已安装的 scipilot 脚本），未安装时这些测试会跳过。

## 只呈现主线版本

全部技能共用一条规则：早期版本、修复前模型和开发流程（wave、closure、修复、预注册假设编号等）不进图、表、图注和写作大纲；按内部计划组织的分析改成按科学问题组织。细则见 `medfig-plan/references/mainline_rules.md`，figkit 导出时默认拦截相关措辞。

## 经验来源

各技能中的规则来自真实论文出图过程中积累的缺陷与修正，整理为通用规则并按编号引用（见 `medfig-plan/references/lessons.md`）。借用的第三方思路和代码见 [`NOTICE.md`](NOTICE.md)。

## 版本

变更记录见 [`CHANGELOG.md`](CHANGELOG.md)。
