---
name: koubo-style
description: 本人的竖屏短视频剪辑风格与工作流。当用户要剪口播、访谈、Vlog、切片，或要写短视频脚本/文案/金句/钩子时使用。覆盖从脚本到剪映草稿的全流程，自动按内容类型切换口播档与 Vlog 档。
---

# 竖屏短视频剪辑（本人风格）

用户是中文短视频创作者：**以口播为主，偶尔 Vlog，一律竖屏 9:16**。
风格参照中文竖屏商业访谈切片那一路（大字幕、关键词高亮、金句卡、快节奏去停顿）。

## 完整链路

```
参考片链接(用户) → extract.py 摄取 → 拆文案逻辑(我) ─┐
                                                    ├→ 写脚本(我) → 录制(用户)
用户给的内容/观点/真事 ──────────────────────────────┘
    → 剪映智能字幕导出 SRT(用户) → make_talking_head.py 剪辑(我) → 剪映里微调(用户)
```

前半段（摄取、拆解、写稿）不依赖剪映，**任何机器都能跑**；但 `extract.py --url`
要能访问视频站，云端会话做不到，得在用户本机跑。

用户**自己出镜口播**，不要提议用 TTS 替他配音——真人声音是他的核心资产。
TTS 只用在片头包装、数据说明段、缺画面的插入段。

## 写脚本

用户说「写个关于 X 的口播脚本」时，产出**可直接照着念**的文本，不是提纲。

结构：

1. **钩子（前 3 秒）** —— 一句反常识的问句或结论。不要复述标题，不要「今天跟大家聊聊」。
2. **立论（10 秒内）** —— 把观点摆完，别铺垫。
3. **展开（2–4 个点）** —— 每个点一句话论点 + 一个具体例子或数字。抽象论述在竖屏上留不住人。
4. **金句** —— 全篇挑 1–2 句最锋利的，标出来，剪辑时做金句卡。
5. **收尾** —— 一个动作或一个反问。别喊「点赞关注」。

写完同时给出配套的 `plan.json` 草案：钩子文案、3–6 个高亮关键词、金句的大致位置。
时长按每分钟 300–350 字中文估算——`refs/*/stats.json` 里有参考片的实测
`chars_per_min`，攒够几条就拿均值替换这个假设。

## 拆参考片

用户甩链接说「学学这个」「照这个思路写」时：

```bash
python extract.py --url <链接> --url <链接>      # 用户本机跑，可批量
```

每条落到 `refs/<日期>-<名字>/`。读 `transcript.txt` 和 `stats.json`，写
`refs/<日期>-<名字>/analysis.md`，固定六项：

1. **骨架对照** —— 把文案切到钩子 / 立论 / 展开 / 金句 / 收尾五格里。对不上的地方
   比对得上的更有价值：它多了哪一格、少了哪一格、顺序怎么换的。
2. **钩子类型** —— 反常识结论 / 问句 / 悬念 / 数字 / 冲突 / 身份反差，前 3 秒原文
   在 `stats.json` 的 `hook_first_3s`。
3. **论证手法** —— 具体例子和抽象论述各占多少；有没有数字、对比、自嘲、反问、
   第二人称「你」。竖屏上抽象论述留不住人，看它怎么避开的。
4. **节奏** —— `chars_per_min` 对比我们的 320；`avg_cue_chars` 是单句长度；
   `gaps_over_0_5s` 是刻意停顿的次数（通常落在金句前后）。
5. **金句** —— 挑出来，看它出现在全片百分之几的位置。
6. **能借什么** —— 只列**结构和手法**，例如「先给结论再给反例」「用一个数字开头」。

### 借结构，不借文字

**不要复用参考片的句子**，换词改写也不行。两个原因：照搬别人文案是抄袭；
而且用户的护城河是他自己的真实经历和语气，套别人的话一听就假。
`analysis.md` 的第 6 项只写可迁移的结构，写新脚本时用的是用户给的内容。

## 字幕从哪来

**两种来源，别混：**

| 片子 | 字幕来源 | 原因 |
|---|---|---|
| **用户自己的原片** | 剪映智能字幕导出 SRT | 原片还没烧字幕，没东西可 OCR |
| **参考片**（别人的成片） | `extract.py` 里 rea-video OCR 烧录字幕 | 成片字幕已烧进画面 |

jianying-editor **没有 ASR**（`scripts/` 下没有任何 whisper/转录实现）。
用户原片走剪映智能字幕时，**在原片上识别**后导出 SRT——不要先剪再识别，
时间轴会对不上。脚本会自动把 SRT 重映射到切完静音的新时间轴。

参考片的 OCR 实测：竖屏噪点背景、白字黑描边单行字幕，6 句 58 字 **100% 准确**，
时间轴误差 ≤0.1 秒。花字、彩色高亮词、双行字幕、表情包没测过，准确率会低一些。
没烧字幕的参考片用 `extract.py --asr`（faster-whisper，云端下不了模型，**未验证**）。

## 先判断档位

| 信号 | 档位 | 处理 |
|---|---|---|
| 对镜说话、访谈、观点输出、知识分享 | **口播档** | 静音切除开启，字幕全程，金句卡 + 话题条 |
| 出行、探店、生活记录、多场景空镜 | **Vlog 档** | 静音切除**关闭**，字幕按需，BGM 提到 0.25，靠转场推进 |

拿不准就问一句，别猜。

## 口播档

```bash
python make_talking_head.py --video <素材> --plan plan.json \
                            --srt <字幕> --bgm <音乐> --name "<草稿名>"
```

先写 `plan.json`，这是我的活儿：

```json
{
  "hook": "开头 3 秒的钩子，一句反常识的问句或结论",
  "keywords": ["高亮词1", "高亮词2"],
  "chapters": [{"t": "0s", "text": "① 段落标题"}],
  "quotes": [{"t": "12s", "text": "金句原文", "d": "3s"}]
}
```

写 plan 的原则：

- **hook** 必须是问句或反常识结论，不要复述标题。落在成片前 2.5 秒。
- **keywords** 3–6 个，挑观点承重的名词，不要挑虚词。高亮是暖黄 + 加粗 + 放大 1.15 倍。
- **quotes** 一条切片最多 2 条，挑情绪或认知转折点，多了就廉价。
- **chapters** 只在内容确实分段时加，短切片（<60s）通常不需要。
- 所有 `t` 按**原素材**计时，脚本会自动重映射到静音切除后的时间轴。

## Vlog 档

用 `edit_video.py`（不切静音、不带钩子/金句那套）：

```bash
python edit_video.py --video <素材> --srt <字幕> --bgm <音乐> --name "<草稿名>"
```

要竖屏就在 `presets/koubo.py` 的 `STYLE["canvas"]` 之外单独指定，`edit_video.py`
会按素材比例自动判横竖。

## 改风格

所有视觉参数集中在 `presets/koubo.py` 的 `STYLE` dict：字号、位置、高亮色、
BGM 音量、静音阈值。用户说「字幕再大点」「高亮换成红色」「停顿留多一点」，
改这一个 dict，不要散落到脚本里。

## 校准流程（拿参考片反推 STYLE）

`STYLE` 里的数值**最初是按品类惯例设的，没有依据**。用 `.claude/skills/rea-video`
把它们换成测量值。用户给一条他想对标的参考片就能跑。

### 0. 一条命令跑完（推荐）

```bash
python calibrate.py --url https://v.douyin.com/xxxxx/   # 本机：先下载再拆
python calibrate.py --video 参考片.mp4                   # 已有文件
```

它会下载（可选）→ decompose → 直接打印换算好的 `sub_y` / `sub_color`。
**`--url` 只能在用户本机跑**：云端会话的网络策略在 CONNECT 层拦截抖音 /
B站 / 小红书 / YouTube，yt-dlp 装得上但够不着。

下面是手动步骤，`calibrate.py` 不够用时照着做。

### 1. 拆解参考片

```bash
source .venv/bin/activate
rea-video decompose 参考片.mp4 -o out/ref           # 离线免费
rea-video decompose 参考片.mp4 -o out/ref --ocr-lang ja   # 日文字幕用这个
```

**不需要配 Gemini / 豆包的 key。** 跑完用 `rea-video review out/ref` 生成看图任务，
你自己（多模态 agent）看 `shots/` 里的帧填答案，再 `rea-video apply-review out/ref --by claude`
并入。VLM 那条路是给看不了图的 agent 准备的。

### 2. 读测量值

样式在 `out/ref/packaging/timeline.json` 的 `text[]` 里，每条含
`bbox`（`[x, y, w, h]`，归一化，y 从**顶部**算）、`style.fill`、`style.stroke`、
`style.stroke_ratio`、`style_zh`（人话版，含字高百分比和像素数）、`anim_in` / `anim_out`。

### 3. 映射到 STYLE

| timeline.json | → STYLE | 验证状态 |
|---|---|---|
| `bbox[1] + bbox[3]/2`（y 中心） | `sub_y = 1 - 2 × y中心` | ✅ 实测精确（设 0.859 测得 0.8594） |
| `bbox[3]`（字高占比） | `sub_size`，按下面的比例法 | ✅ 实测准确（72px 字测得 79px） |
| `style.fill` | `sub_color`（十六进制转 0–1 三元组） | ✅ 实测准确 |
| `style.stroke` | 描边色（`presets/koubo.py` 的 `_border()`） | ✅ 实测准确 |
| `style.stroke_ratio` | 只做横向比较，**别直接当 `sub_border_width`** | ⚠️ 它有自己的定义，不是像素宽 |
| `anim_in` / `anim_out` | `hook_anim` / `quote_anim` | 未验证 |
| `rea-video summary` 的「剪辑:」行 | `silence_noise_db` / `silence_min_dur` / `keep_padding` | 未验证 |
| `rea-video stems` 的 vocals vs music 电平 | `bgm_volume` | 未验证 |

**`sub_y` 换算**：剪映的 `transform_y` 是 -1（底）到 +1（顶），rea-video 的 y 是
0（顶）到 1（底），所以 `transform_y = 1 - 2 × y中心`。
例：y中心 0.88 → `sub_y = -0.76`。

**`sub_size` 用比例法，不要猜绝对值**：剪映的字号标度和像素没有公开对应关系。做法是
闭环——用当前 `STYLE` 生成一条草稿、导出、对导出的成片也跑一次 `decompose`，
拿到「我们的字高%」，然后

```
新的 sub_size = 当前 sub_size × (参考片字高% ÷ 我们的字高%)
```

一轮就能收敛到个位数误差。`hook_size` / `quote_size` / `chapter_size` 同法。

### 4. 改完要做的

改 `presets/koubo.py` 的 `STYLE`，在 dict 上方注释里写明**这组值来自哪条参考片**
（文件名 + 跑 decompose 的日期），否则下次没人知道哪些是测量值、哪些还是猜的。

### 已知限制

- **文字内容识别不可靠**，但校准不需要它——只用位置、字号、颜色，这三样准。
- `rea-video` 要完整 ffmpeg + ffprobe，和剪辑脚本同一套依赖。
- 人脸检测模型首次运行要联网下载；下不动会回退到 Haar，不影响字幕样式提取。
- 参考片要先下载成本地文件，它不收 URL。

## 硬约束

- **竖屏 1080x1920**，创建 `JyProject` 时必须显式传 `width=1080, height=1920`，
  否则画布会被素材比例覆盖。
- **别用 `add_styled_text()` 和 `project.import_srt()`** —— jianying-editor v1.5.0
  的 `rules/text.md` 写了但代码里没有，调用会 `AttributeError`。花字目前不可用；
  SRT 走 `project.script.import_srt(...)` 或本仓库的 `parse_srt()`。
- **文字轨没有自动分层防碰撞** —— `rules/text.md` 声称 "Auto-Layering
  (Anti-Collision)"，实测重叠会直接抛 `SegmentOverlap`。走
  `presets/koubo.py` 的 `_add_overlap_safe()`，它会自动降到 `<track>_2` 层。
- **时间一律传整数微秒，别传 `"8.200s"` 这种字符串** —— skill 的 `safe_tim()` 把
  `"8.200s"` 解析成 `int(8.2×1e6) = 8199999`，截断丢 1µs。首尾相接的两句字幕
  （剪映导出的 SRT 几乎全是这样）会因此被判重叠、后一句挤到 `Subtitles_2`。
  实测 40 句相接的 SRT，旧写法 39 对里错 1 对，而且错不错取决于浮点数往哪边舍——
  不稳定。用 `presets/koubo.py` 的 `us()`，时长写成 `us(end) - us(start)`。
- **横屏转竖屏会裁掉约 70% 画幅**（2046px 宽的源只剩约 608px 可见）。用
  `--subject-x` 挪，或建议用户原生竖屏拍。
- **别把 ffprobe 软链到 imageio-ffmpeg 的二进制上** —— 那个包只有 ffmpeg，
  skill 的 `get_duration_ffprobe_cached()` 会静默拿到错误时长。
- 业务脚本写在**仓库根目录**，不要写进 `.claude/skills/jianying-editor/` 里。
- 剪映必须是**专业版 v5.9+**，且脚本要在装了剪映的本机跑。

## 还没做的

TTS 配音、云端配乐库、自动导出成片都还没接进这套流程。用户提出来再按
`.claude/skills/jianying-editor/rules/audio-voice.md` 和 `core.md` 接。
