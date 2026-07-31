# Adam2027

短视频「脚本 → 剪辑」工作流工作区。用 [jianying-editor](https://github.com/luoluoluo22/jianying-editor-skill) skill 驱动剪映(JianYing)专业版。

## 一次性配置(本机)

需要 macOS 或 Windows,且已安装**剪映专业版 v5.9+**。Linux 上只能生成草稿文件,没法打开。

```bash
git clone <this-repo> && cd Adam2027

python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r .claude/skills/jianying-editor/requirements.txt
playwright install chromium        # 仅「网页转视频 / Web 动效」功能需要,可先跳过
```

ffmpeg 需要单独装(skill 内部靠 `ffprobe` 读时长):

```bash
brew install ffmpeg                # macOS
winget install Gyan.FFmpeg         # Windows
```

> `pip install imageio-ffmpeg` 只提供 `ffmpeg`,**不含 `ffprobe`**。不要把 `ffprobe`
> 软链到 ffmpeg 二进制上——skill 的 `get_duration_ffprobe_cached()` 会因此静默拿到
> 错误时长。

## 剪一个视频

```bash
python edit_video.py --video ~/Movies/raw.mp4 \
                     --srt   ~/Movies/raw.srt \
                     --bgm   ~/Music/bgm.mp3 \
                     --name  "我的第一个视频"
```

`--srt` 和 `--bgm` 可选,`--bgm-volume` 默认 0.15。脚本会:

1. 用 pymediainfo 读主视频宽高,横屏建 1920x1080、竖屏建 1080x1920(避免黑边)
2. 自动探测本机剪映草稿目录(`--drafts-root` 可覆盖)
3. 导入主视频 → SRT 字幕(位置 `transform_y=-0.8`)→ BGM
4. `project.save()` 后打印各轨道片段数做验收

跑完打开剪映,草稿列表里就是 `--name` 那个项目。时间线、字幕、特效都能继续手动调。

### 验证状态

`edit_video.py` 已在 Linux 容器里用 skill 自带的 `assets/video.mp4` + `subtitle.srt` +
`audio.mp3` 跑通,生成的 `draft_info.json` 含 1 视频轨 / 1 音频轨 / 3 字幕段。**未在装有
剪映的机器上验证过实际打开效果**——那一步需要你本机跑。

## 更多能力

`edit_video.py` 只覆盖最常见的「导入 + 字幕 + 配乐」。skill 还支持 TTS 配音、云端配乐库、
特效转场、关键帧、录屏智能变焦、影视解说生成等,见:

- `.claude/skills/jianying-editor/SKILL.md` — 能力索引
- `.claude/skills/jianying-editor/rules/` — 各功能的 API 约定
- `.claude/skills/jianying-editor/examples/` — 完整示例脚本

直接在本仓库根目录开 Claude Code 说人话也行,例如「把 raw.mp4 剪成竖屏,去掉前 3 秒,加
白色字幕和轻快 BGM」。

> 已知偏差:`rules/text.md` 里写的 `add_styled_text()`(花字)和 `project.import_srt()`
> 在 v1.5.0 代码里并不存在。花字暂不可用;SRT 要走 `project.script.import_srt(...)`,
> `edit_video.py` 里已经是正确写法。

## 其他方案

[ChatCut](https://chatcut.io/claude-code-plugin) 是云端 NLE,在 Claude Code **桌面版**里
边聊边剪,不依赖剪映。安装(需在桌面版执行):

```bash
claude plugin marketplace add https://github.com/ChatCut-Inc/agent-plugin.git
claude plugin install chatcut@chatcut-inc
claude mcp login plugin:chatcut:chatcut
```

装完要**新开一个对话**才能用——Claude Code 在会话启动时锁定插件列表。
