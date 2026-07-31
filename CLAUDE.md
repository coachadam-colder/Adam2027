# Adam2027

竖屏短视频「脚本 → 剪辑」工作区。创作者在东京，主做中文竖屏口播，
运营「日中语言交流会」线下活动。

## 先读这两个

- `.claude/skills/koubo-style/SKILL.md` —— 剪辑风格、写脚本规范、档位路由、硬约束
- `content/PLAN.md` —— 内容策略：三条线、两个产能池、固定三问、选题表

这两份是这个仓库的方法论本体。动手之前先读，不要凭对话上下文猜。

## 目录

```
.claude/skills/jianying-editor/   剪映自动化 skill（vendored，v1.5.0，别改）
.claude/skills/koubo-style/       剪辑风格 + 写脚本规范（本仓库自有）
presets/koubo.py                  所有视觉参数集中在 STYLE dict
edit_video.py                     通用：导入 + 字幕 + BGM
make_talking_head.py              主力：静音切除 + 时间轴重映射 + 高亮字幕 + 金句卡
content/PLAN.md                   内容策略
content/NN-slug/                  每条视频：script.md（逐字稿）+ plan.json（剪辑单）
```

## 工作循环

```
写脚本(Claude) → 录制(用户) → 剪映智能字幕导出 SRT(用户) → 剪辑(Claude) → 剪映微调(用户)
```

字幕必须**在原片上**识别后导出，不要先剪——`make_talking_head.py` 会把 SRT
时间轴自动重映射到切完静音之后的新时间轴。

## 环境

跑剪辑脚本需要**本机装有剪映专业版 v5.9+**（macOS 或 Windows）。
首次配置跑 `./setup.sh`（Windows 用 `setup.ps1`）。

写脚本不需要任何环境，任何机器都能做。

## 已知的上游坑（jianying-editor v1.5.0 文档与代码不符）

调用前先看 `.claude/skills/koubo-style/SKILL.md` 的「硬约束」一节，
那里记了三处文档写了但代码没有/行为不符的地方，照文档写会直接报错。
