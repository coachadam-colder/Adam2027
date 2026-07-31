# Skills

本目录存放本仓库启用的 Claude Code Skills。

## jianying-editor

短视频「脚本 → 配音 → 字幕 → 配乐 → 特效 → 导出」全流程自动化 Skill，直接操作剪映(JianYing / CapCut 国内版)草稿。

- 来源：https://github.com/luoluoluo22/jianying-editor-skill
- 版本：v1.5.0（commit `f421c8a`，2026-06-12）
- 许可：见 `jianying-editor/LICENSE`

### 本地使用前置条件

这个 Skill 需要在**装有剪映专业版的本机**（macOS 或 Windows）上运行，云端容器里跑不了。克隆本仓库到本地后：

```bash
cd .claude/skills/jianying-editor
pip install -r requirements.txt
playwright install chromium      # Web 动效 / 网页转视频功能需要
```

要求 Python 3.10+、剪映专业版 v5.9+（新版 `draft_info.json` 架构）。

### 用法

在仓库根目录启动 Claude Code，直接用自然语言描述需求即可，例如：

> 写一段关于秋天第一杯奶茶的文案，配温柔女声旁白和暖色 BGM，生成剪映草稿

Skill 约定：生成的剪辑脚本写到**项目根目录**（或 `scripts/`），不要写进 Skill 目录内部。

更多说明见 `jianying-editor/SKILL.md`、`jianying-editor/usage.md` 和 `jianying-editor/docs/agent-playbook.md`。
