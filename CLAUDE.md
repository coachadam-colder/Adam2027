# Adam2027

竖屏短视频「脚本 → 剪辑」工作区。创作者在东京，主做中文竖屏口播，
运营「日中语言交流会」线下活动。

## 先读这两个

- `.claude/skills/koubo-style/SKILL.md` —— 剪辑风格、写脚本规范、拆参考片、档位路由、校准、硬约束
- `content/PLAN.md` —— 内容策略：三条线、两个产能池、固定三问、选题表

这两份是这个仓库的方法论本体。动手之前先读，不要凭对话上下文猜。

## 在哪台机器上干活

**主战场是用户的 Windows 电脑，仓库在 `E:\Adam2027`**（`bootstrap_e.ps1` 装的）。
只有那里同时具备：能访问抖音等视频站、装着剪映、素材在本地。

云端会话能做：写脚本、拆文案逻辑（用户贴文本或 `refs/` 已有内容）、改代码和方法论。
云端会话**做不到**：下载视频（网络策略在 CONNECT 层拦截视频站）、打开剪映、
碰 E 盘。遇到这些别硬试，告诉用户换到本机的 Claude 桌面版。

## 目录

```
.claude/skills/jianying-editor/   剪映自动化 skill（vendored，v1.5.0，别改）
.claude/skills/koubo-style/       剪辑风格 + 写脚本 + 拆参考片 + 校准（本仓库自有）
.claude/skills/rea-video/         参考片逆向拆解（vendored，去掉了 83M 演示素材）
presets/koubo.py                  所有视觉参数集中在 STYLE dict
extract.py                        参考片摄取：链接/文件 -> 文案 + 节奏 + 样式，写进 refs/
calibrate.py                      参考片 -> STYLE 建议值（extract.py 也会顺带算）
make_talking_head.py              主力剪辑：静音切除 + 时间轴重映射 + 高亮字幕 + 金句卡
edit_video.py                     通用剪辑：导入 + 字幕 + BGM
bootstrap_e.ps1                   Windows 一键装到 E 盘
content/PLAN.md                   内容策略
content/NN-slug/                  每条视频：script.md（逐字稿）+ plan.json（剪辑单）
refs/  素材/  成片/                本机工作目录，gitignored
```

## 工作循环

```
参考片链接 → extract.py → 拆文案逻辑(Claude) ─┐
用户给的观点/真事 ─────────────────────────────┴→ 写脚本(Claude) → 录制(用户)
→ 剪映智能字幕导出 SRT(用户) → make_talking_head.py(Claude) → 剪映微调(用户)
```

- 参考片文案来自 rea-video **OCR 烧录字幕**；用户自己的原片没烧字幕，走剪映智能字幕。
- 用户原片的字幕必须**在原片上**识别后导出，不要先剪——`make_talking_head.py`
  会把 SRT 时间轴自动重映射到切完静音之后的新时间轴。
- 拆参考片**借结构，不借文字**。规则在 koubo-style「拆参考片」一节。

## 环境

- 首次配置：Windows 跑 `bootstrap_e.ps1`（会调 `setup.ps1`）；macOS/Linux 跑 `./setup.sh`。
- 剪映草稿目录：优先 `--drafts-root`，其次环境变量 `JY_DRAFTS_ROOT`，最后自动探测。
  自动探测只认 `%LOCALAPPDATA%` 默认位置，用户在剪映里挪过草稿位置就必须设 `JY_DRAFTS_ROOT`，
  否则草稿会静默写到剪映不读的目录。
- `.ps1` 文件必须存成 **UTF-8 带 BOM**，只用 PS 5.1 也认的语法。否则中文 Windows
  自带的 PowerShell 5.1 会按 GBK 读，中文全乱码。
- 写脚本、拆文案不需要任何环境。

## 已知的上游坑

调用前先看 `.claude/skills/koubo-style/SKILL.md` 的「硬约束」一节，
那里记了 jianying-editor v1.5.0 三处文档写了但代码没有/行为不符的地方，照文档写会直接报错。
