"""竖屏口播 / 访谈切片风格预设。

风格参数集中在 STYLE 里，改这一个 dict 就能全局调风格。所有函数都只依赖
jianying-editor skill 里**实际存在**的 API（v1.5.0 验证过），不用文档里写了但
代码没实现的 add_styled_text()。
"""

import os
import re
import shutil
import subprocess

import pyJianYingDraft as draft

# ---------------------------------------------------------------------------
# 风格参数
# ---------------------------------------------------------------------------

STYLE = {
    "canvas": (1080, 1920),          # 竖屏 9:16

    # 正文字幕：底部,大字号,黑描边(竖屏小屏幕上必须够粗才看得清)
    "sub_size": 7.0,
    "sub_y": -0.72,
    "sub_color": (1.0, 1.0, 1.0),
    "sub_border_width": 48.0,
    "sub_highlight_color": (1.0, 0.86, 0.16),   # 关键词高亮：暖黄
    "sub_highlight_scale": 1.15,                 # 高亮词放大倍数

    # 开场 hook：中上方,弹入,3 秒内抛出钩子
    "hook_size": 13.0,
    "hook_y": 0.42,
    "hook_color": (1.0, 1.0, 1.0),
    "hook_anim": "弹入",
    "hook_duration": "2.5s",

    # 金句卡：居中,最大字号,用于停顿强调
    "quote_size": 15.0,
    "quote_y": 0.0,
    "quote_color": (1.0, 0.86, 0.16),
    "quote_anim": "向上滑动",

    # 话题条：顶部,标记访谈段落
    "chapter_size": 8.0,
    "chapter_y": 0.82,
    "chapter_color": (1.0, 1.0, 1.0),
    "chapter_anim": "向上露出",

    # BGM：口播必须压得很低,否则盖住人声
    "bgm_volume": 0.10,

    # 静音切除
    "silence_noise_db": -32,      # 低于此电平算静音
    "silence_min_dur": 0.55,      # 静音持续超过这么久才切
    "keep_padding": 0.12,         # 每段语音前后保留的呼吸感
}

TRACKS = {
    "video": "Main",
    "bgm": "BGM",
    "sub": "Subtitles",
    "hook": "Hook",
    "quote": "Quote",
    "chapter": "Chapter",
}


def _border():
    return draft.TextBorder(color=(0.0, 0.0, 0.0), alpha=1.0, width=STYLE["sub_border_width"])


def _add_overlap_safe(fn, track_name, **kwargs):
    """时间重叠时自动换到 <track>_2 / _3 ... 层。

    skill 的 rules/text.md 声称 add_text_simple 有自动分层防碰撞，实测 v1.5.0
    并没有——重叠会直接抛 SegmentOverlap。这里自己兜住。
    """
    from pyJianYingDraft.exceptions import SegmentOverlap

    for layer in range(1, 6):
        name = track_name if layer == 1 else f"{track_name}_{layer}"
        try:
            return fn(track_name=name, **kwargs)
        except SegmentOverlap:
            continue
    print(f"⚠️ {track_name}: 连续 5 层都撞车,丢弃一条 -> {kwargs.get('text', '')[:20]}")
    return None


# ---------------------------------------------------------------------------
# 画面
# ---------------------------------------------------------------------------

def fit_portrait(seg, src_w, src_h, canvas_w=None, canvas_h=None, subject_x=0.0):
    """把素材缩放到填满竖屏画布(crop-to-fill),避免上下黑边。

    注意横屏转竖屏的代价：2046x1080 的源填满 9:16 需要放大 3.37 倍，画面里
    只剩约 608px / 2046px（30%）的宽度可见。人不在正中就会被切掉——用
    subject_x 左右挪（-1.0 到 1.0，正值把画面往右推），或者干脆原生竖屏拍。

    返回 (seg, factor)，factor 是实际放大倍数，调用方可以据此告警。
    """
    canvas_w = canvas_w or STYLE["canvas"][0]
    canvas_h = canvas_h or STYLE["canvas"][1]
    if not src_w or not src_h:
        return seg, 1.0
    # pyJianYingDraft 的 scale 是相对于「素材已适配画布」的倍数
    fill = max(canvas_w / src_w, canvas_h / src_h)
    fit = min(canvas_w / src_w, canvas_h / src_h)
    factor = fill / fit
    seg.clip_settings.scale_x = factor
    seg.clip_settings.scale_y = factor
    if subject_x:
        seg.clip_settings.transform_x = subject_x
    return seg, factor


# ---------------------------------------------------------------------------
# 文字
# ---------------------------------------------------------------------------

def add_subtitle(project, text, start, duration, keywords=None):
    """一条正文字幕。keywords 里的词会被高亮放大。"""
    keywords = [k for k in (keywords or []) if k and k in text]
    common = dict(
        text=text,
        start_time=start,
        duration=duration,
        style=draft.TextStyle(size=STYLE["sub_size"], color=STYLE["sub_color"]),
        border=_border(),
        clip_settings=draft.ClipSettings(transform_y=STYLE["sub_y"]),
    )
    if keywords:
        return _add_overlap_safe(
            project.add_rich_text,
            TRACKS["sub"],
            highlights=[
                {
                    "word": k,
                    "color": STYLE["sub_highlight_color"],
                    "bold": True,
                    "size": STYLE["sub_size"] * STYLE["sub_highlight_scale"],
                }
                for k in keywords
            ],
            **common,
        )
    return _add_overlap_safe(project.add_text_simple, TRACKS["sub"], **common)


def add_hook(project, text, start="0s", duration=None):
    """开场钩子标题。"""
    return _add_overlap_safe(
        project.add_text_simple,
        TRACKS["hook"],
        text=text,
        start_time=start,
        duration=duration or STYLE["hook_duration"],
        style=draft.TextStyle(size=STYLE["hook_size"], color=STYLE["hook_color"], bold=True),
        border=_border(),
        clip_settings=draft.ClipSettings(transform_y=STYLE["hook_y"]),
        anim_in=STYLE["hook_anim"],
    )


def add_quote(project, text, start, duration="3s"):
    """金句卡：居中大字,用在停顿或情绪高点。"""
    return _add_overlap_safe(
        project.add_text_simple,
        TRACKS["quote"],
        text=text,
        start_time=start,
        duration=duration,
        style=draft.TextStyle(size=STYLE["quote_size"], color=STYLE["quote_color"], bold=True),
        border=_border(),
        clip_settings=draft.ClipSettings(transform_y=STYLE["quote_y"]),
        anim_in=STYLE["quote_anim"],
    )


def add_chapter(project, text, start, duration="3s"):
    """顶部话题条,标记访谈段落。"""
    return _add_overlap_safe(
        project.add_text_simple,
        TRACKS["chapter"],
        text=text,
        start_time=start,
        duration=duration,
        style=draft.TextStyle(size=STYLE["chapter_size"], color=STYLE["chapter_color"]),
        border=_border(),
        clip_settings=draft.ClipSettings(transform_y=STYLE["chapter_y"]),
        anim_in=STYLE["chapter_anim"],
    )


# ---------------------------------------------------------------------------
# 节奏：静音切除
# ---------------------------------------------------------------------------

_SIL_START = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SIL_END = re.compile(r"silence_end:\s*(-?[\d.]+)")


def detect_speech_ranges(video_path, total_duration):
    """用 ffmpeg silencedetect 找出说话段,返回 [(start, end), ...] 秒。

    ffmpeg 不可用时返回整段,调用方不会因此崩掉。
    """
    if not shutil.which("ffmpeg"):
        print("⚠️ 没有 ffmpeg,跳过静音切除,保留整段。")
        return [(0.0, total_duration)]

    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-nostats", "-i", video_path,
            "-af", f"silencedetect=noise={STYLE['silence_noise_db']}dB:d={STYLE['silence_min_dur']}",
            "-f", "null", "-",
        ],
        capture_output=True, text=True,
    )
    log = proc.stderr

    silences = []
    cur = None
    for line in log.splitlines():
        m = _SIL_START.search(line)
        if m:
            cur = max(0.0, float(m.group(1)))
        m = _SIL_END.search(line)
        if m and cur is not None:
            silences.append((cur, float(m.group(1))))
            cur = None
    if cur is not None:
        silences.append((cur, total_duration))

    pad = STYLE["keep_padding"]
    speech = []
    pos = 0.0
    for s_start, s_end in silences:
        seg_end = min(total_duration, s_start + pad)
        if seg_end - pos > 0.3:
            speech.append((pos, seg_end))
        pos = max(0.0, s_end - pad)
    if total_duration - pos > 0.3:
        speech.append((pos, total_duration))

    return speech or [(0.0, total_duration)]


def lay_speech_segments(project, video_path, speech_ranges, src_wh=None, subject_x=0.0):
    """按说话段依次拼到主轨上,自动去掉中间的静默。

    返回 (片段列表, 成片时长秒, 裁切放大倍数)。
    """
    segs = []
    timeline = 0.0
    factor = 1.0
    for start, end in speech_ranges:
        dur = end - start
        seg = project.add_media_safe(
            video_path,
            start_time=f"{timeline:.3f}s",
            duration=f"{dur:.3f}s",
            track_name=TRACKS["video"],
            source_start=f"{start:.3f}s",
        )
        if seg is None:
            continue
        if src_wh:
            seg, factor = fit_portrait(seg, *src_wh, subject_x=subject_x)
        segs.append(seg)
        timeline += dur
    return segs, timeline, factor
