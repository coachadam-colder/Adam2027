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

## 竖屏口播 / 访谈切片（主力流程）

```bash
python make_talking_head.py --video raw.mp4 --plan plan.json \
                            --srt raw.srt --bgm bgm.mp3 --name "访谈01"
```

做的事:

1. **静音切除** —— ffmpeg `silencedetect` 找出说话段,只保留语音,前后各留 0.12s
   呼吸感。原片 9.5s → 成片 6.5s 这种压缩很常见。
2. **时间轴重映射** —— `plan.json` 里的时间点按原素材写,脚本自动换算到剪完之后
   的新时间轴。金句/话题条落进被剪掉的静音会顺延到下一段语音;字幕则直接跳过
   (字幕跟着语音走,硬挪会对不上口型)。
3. **关键词高亮字幕** —— `keywords` 里的词自动加粗放大、染成暖黄。
4. **开场钩子 / 金句卡 / 顶部话题条** —— 各占独立轨道,剪映里能单独调。
5. **BGM 压到 0.10** —— 口播盖不住人声。

`plan.json` 格式见 `make_talking_head.py` 顶部文档。风格参数全在
`presets/koubo.py` 的 `STYLE` dict 里,改一处即可全局生效。

Vlog 加 `--no-cut-silence`(保留原始停顿),或用下面的通用流程。

### 横屏素材转竖屏的代价

竖屏画布是 1080x1920。横屏源填满它需要大幅放大——实测 2046x1080 的素材要放大
**3.37 倍**,画面里只剩约 **608px / 2046px(30%)** 的宽度可见。人不在正中就会被切掉。

脚本会在放大超过 1.05 倍时打印警告。用 `--subject-x` 左右挪(-1~1,正值往右推):

```bash
python make_talking_head.py --video 横屏.mp4 --subject-x 0.15 ...
```

**能原生竖屏拍就原生拍**,这一步没有无损方案。

## 剪一个视频（通用）

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

在 Linux 容器里跑通的部分:

- `edit_video.py` —— 用 skill 自带的 `video.mp4` + `subtitle.srt` + `audio.mp3`,
  生成的 `draft_info.json` 含 1 视频轨 / 1 音频轨 / 3 字幕段,canvas 自动贴合素材比例。
- `make_talking_head.py` —— 用合成的「2s 音 + 2s 静 + 2s 音 + 1.5s 静 + 2s 音」测试片:
  silencedetect 准确识别出 2.02–4.02 与 6.01–7.50 两段静音,主轨切成 3 段,
  9.5s → 6.5s;画布锁定 1080x1920;超出素材时长、落入静音、顺延标记三种边界都按预期处理。

**没验证的**:草稿在剪映里实际打开的效果、TTS 配音、云端配乐库、自动导出——
容器里没有剪映,且微软 TTS 端点和云端素材库被网络策略拦截。这些要你本机确认。

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
