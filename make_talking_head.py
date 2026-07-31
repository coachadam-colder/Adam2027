#!/usr/bin/env python3
"""竖屏口播 / 访谈切片：按 presets/koubo.py 的风格生成剪映草稿。

    python make_talking_head.py --video raw.mp4 --plan plan.json \
                                --srt raw.srt --bgm bgm.mp3 --name "访谈01"

plan.json（全部字段可选）:

    {
      "hook":     "为什么大厂出来创业的人九成都死了",
      "keywords": ["认知", "壁垒", "现金流"],
      "chapters": [{"t": "0s",  "text": "① 他到底在赌什么"}],
      "quotes":   [{"t": "12s", "text": "别把平台的能力当成自己的能力", "d": "3s"}],
      "subtitles":[{"t": "0s", "d": "2.5s", "text": "..."}]
    }

plan 里的时间轴按**原素材**计时。开了静音切除时，脚本会把这些时间点重映射到
切完之后的新时间轴上。落在被剪掉的静音里时：金句和话题条顺延到下一段语音，
字幕直接跳过（字幕跟着语音走，硬挪会对不上口型）。两种情况都会打印告警。
"""

import argparse
import json
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
_skill = os.path.join(current_dir, ".claude", "skills", "jianying-editor")
if not os.path.exists(os.path.join(_skill, "scripts", "jy_wrapper.py")):
    sys.exit(f"找不到 jianying-editor skill: {_skill}")
sys.path.insert(0, os.path.join(_skill, "scripts"))
sys.path.insert(0, current_dir)

if sys.platform == "darwin":
    for extra in ("/opt/homebrew/bin", "/usr/local/bin"):
        if extra not in os.environ.get("PATH", ""):
            os.environ["PATH"] = extra + ":" + os.environ.get("PATH", "")

from jy_wrapper import JyProject  # noqa: E402
from presets import koubo  # noqa: E402
from edit_video import ensure_media_tools, probe_resolution  # noqa: E402


def probe_duration(path):
    try:
        from pymediainfo import MediaInfo

        for t in MediaInfo.parse(path).tracks:
            if t.track_type == "Video" and t.duration:
                return float(t.duration) / 1000.0
    except Exception:
        pass
    return 0.0


def parse_time(v):
    """'12.5s' / 12.5 / '12500' -> 秒(float)。"""
    if isinstance(v, (int, float)):
        return float(v)
    v = str(v).strip()
    return float(v[:-1]) if v.endswith("s") else float(v)


def parse_srt(path):
    """返回 [(start_sec, end_sec, text), ...]。"""
    def ts(s):
        h, m, rest = s.split(":")
        sec, ms = rest.replace(".", ",").split(",")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000.0

    out = []
    with open(path, encoding="utf-8-sig") as fh:
        blocks = fh.read().replace("\r\n", "\n").strip().split("\n\n")
    for block in blocks:
        lines = [l for l in block.split("\n") if l.strip()]
        if len(lines) < 2:
            continue
        time_line = next((l for l in lines if "-->" in l), None)
        if not time_line:
            continue
        start_s, end_s = [p.strip() for p in time_line.split("-->")]
        text = " ".join(lines[lines.index(time_line) + 1:]).strip()
        if text:
            out.append((ts(start_s), ts(end_s), text))
    return out


def build_remapper(speech_ranges):
    """原素材时间 -> 成片时间。

    snap=False（字幕用）：落在被剪掉的静音里返回 None。字幕是跟着语音走的，
    硬挪位置只会和画面对不上。
    snap=True（金句/话题条用）：顺延到下一段语音的开头。这类标记是人手标的，
    丢掉不如挪一下。
    """
    offsets = []
    acc = 0.0
    for start, end in speech_ranges:
        offsets.append((start, end, acc))
        acc += end - start

    def remap(t, snap=False):
        for start, end, base in offsets:
            if start <= t <= end:
                return base + (t - start)
        if snap:
            for start, _end, base in offsets:
                if start > t:
                    return base
        return None

    return remap


def main():
    ap = argparse.ArgumentParser(description="竖屏口播/访谈切片")
    ap.add_argument("--video", required=True)
    ap.add_argument("--plan", help="剪辑单 JSON")
    ap.add_argument("--srt", help="字幕文件；会自动套用关键词高亮")
    ap.add_argument("--bgm")
    ap.add_argument("--name", default="口播切片")
    ap.add_argument("--drafts-root")
    ap.add_argument("--no-cut-silence", action="store_true", help="保留原始停顿,不做静音切除")
    ap.add_argument("--subject-x", type=float, default=0.0,
                    help="横屏转竖屏时水平挪动画面,-1~1,正值往右推。默认 0(居中)")
    args = ap.parse_args()

    ensure_media_tools()

    video = os.path.abspath(os.path.expanduser(args.video))
    if not os.path.exists(video):
        sys.exit(f"找不到视频: {video}")

    plan = {}
    if args.plan:
        with open(os.path.expanduser(args.plan), encoding="utf-8") as fh:
            plan = json.load(fh)
    keywords = plan.get("keywords", [])

    total = probe_duration(video)
    if total <= 0:
        sys.exit("读不出视频时长,检查文件是否损坏或缺少 pymediainfo。")
    src_wh = probe_resolution(video)

    if args.no_cut_silence:
        speech = [(0.0, total)]
    else:
        speech = koubo.detect_speech_ranges(video, total)
    remap = build_remapper(speech)

    cw, ch = koubo.STYLE["canvas"]
    project = JyProject(
        args.name, width=cw, height=ch,
        drafts_root=os.path.expanduser(args.drafts_root) if args.drafts_root else None,
        overwrite=True,
    )

    segs, final_dur, crop = koubo.lay_speech_segments(
        project, video, speech, src_wh, subject_x=args.subject_x
    )
    removed = total - final_dur
    print(f"主轨: {len(segs)} 段,原片 {total:.1f}s -> 成片 {final_dur:.1f}s（剪掉 {removed:.1f}s 静音）")
    if crop > 1.05 and src_wh:
        visible = src_wh[0] / crop
        print(
            f"⚠️ 横屏转竖屏:画面放大 {crop:.2f}x,只剩约 {visible:.0f}px / {src_wh[0]}px 宽度可见。"
            f"人不在正中就会被切掉,用 --subject-x 左右挪(-1~1)。"
        )

    if plan.get("hook"):
        koubo.add_hook(project, plan["hook"])
        print(f"开场钩子: {plan['hook']}")

    dropped = {"overrun": 0, "silence": 0}
    snapped = 0

    def resolve(orig, snap=False):
        """原素材时间 -> 成片时间,并记录被丢弃的原因。"""
        nonlocal snapped
        if orig > total:
            dropped["overrun"] += 1
            return None
        t = remap(orig, snap=snap)
        if t is None:
            dropped["silence"] += 1
        elif snap and remap(orig) is None:
            snapped += 1
        return t

    for item in plan.get("chapters", []):
        t = resolve(parse_time(item["t"]), snap=True)
        if t is None:
            continue
        koubo.add_chapter(project, item["text"], f"{t:.3f}s", item.get("d", "3s"))

    for item in plan.get("quotes", []):
        t = resolve(parse_time(item["t"]), snap=True)
        if t is None:
            continue
        koubo.add_quote(project, item["text"], f"{t:.3f}s", item.get("d", "3s"))

    subs = []
    if args.srt:
        subs = parse_srt(os.path.expanduser(args.srt))
    elif plan.get("subtitles"):
        subs = [
            (parse_time(s["t"]), parse_time(s["t"]) + parse_time(s.get("d", "2.5s")), s["text"])
            for s in plan["subtitles"]
        ]

    # 字幕本不该重叠；ASR 导出的 SRT 偶尔会有毫秒级交叠，收尾到下一条开头。
    subs.sort(key=lambda s: s[0])
    subs = [
        (start, min(end, subs[i + 1][0]) if i + 1 < len(subs) else end, text)
        for i, (start, end, text) in enumerate(subs)
    ]
    subs = [s for s in subs if s[1] > s[0]]

    placed = 0
    for start, end, text in subs:
        ns = resolve(start)
        if ns is None:
            continue
        # 字幕尾巴可能跨进被剪掉的静音,收缩到该语音段末尾而不是整条丢弃
        ne = remap(min(end, total))
        if ne is None or ne <= ns:
            ne = ns + min(end - start, 2.5)
        koubo.add_subtitle(project, text, f"{ns:.3f}s", f"{ne - ns:.3f}s", keywords)
        placed += 1
    if subs:
        print(f"字幕: {placed}/{len(subs)} 条（高亮词 {keywords or '无'}）")
    if dropped["overrun"]:
        print(f"⚠️ {dropped['overrun']} 条时间点超出素材时长（{total:.1f}s）,已跳过")
    if snapped:
        print(f"ℹ️ {snapped} 个标记原本落在被剪掉的静音里,已顺延到下一段语音")
    if dropped["silence"]:
        print(f"⚠️ {dropped['silence']} 条落在被剪掉的静音段里,已跳过")

    if args.bgm:
        bgm = os.path.abspath(os.path.expanduser(args.bgm))
        if os.path.exists(bgm):
            project.add_audio_safe(
                bgm, start_time="0s", track_name=koubo.TRACKS["bgm"],
                duration=f"{final_dur:.3f}s", volume=koubo.STYLE["bgm_volume"],
            )
            print(f"BGM: {os.path.basename(bgm)}（音量 {koubo.STYLE['bgm_volume']}）")
        else:
            print(f"⚠️ 找不到 BGM: {bgm}")

    project.save()

    print("\n--- 验收 ---")
    print(f"画布: {project.script.width}x{project.script.height}")
    print(f"草稿: {project.draft_dir}")
    for name, track in project.script.tracks.items():
        print(f"  {name}: {len(track.segments)} 段")


if __name__ == "__main__":
    main()
