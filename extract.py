#!/usr/bin/env python3
"""参考片摄取：链接或文件 -> 文案 + 节奏数据 + 字幕样式，存进 refs/。

    python extract.py --url https://v.douyin.com/aaa/ --url https://v.douyin.com/bbb/
    python extract.py --video 参考1.mp4 --video 参考2.mp4

每条参考片一个目录 refs/<日期>-<名字>/：

    transcript.txt   纯文案，一行一句（给写脚本时拆文案逻辑用）
    transcript.srt   带时间轴
    stats.json       语速、句长、前 3 秒说了什么、停顿——拆节奏用
    style.json       字幕位置/颜色测量值 + 换算好的 STYLE 建议
    decompose/       rea-video 原始输出（report.html 在这）

文案来自**烧录字幕的 OCR**，不是语音识别。抖音口播几乎都烧了字幕，所以通常够用；
没烧字幕的片子会提示走 ASR（--asr，需要本机能下 whisper 模型）。

--url 只能在用户本机跑：云端会话的网络策略拦截视频站。
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from calibrate import analyse, decompose, download, hex_to_rgb01

REPO = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(REPO, "refs")


def slug_for(src):
    """refs 子目录名：日期 + 文件名或链接短哈希。"""
    day = datetime.date.today().strftime("%Y%m%d")
    if re.match(r"https?://", src):
        tail = re.sub(r"[^\w]+", "-", src.rstrip("/").split("/")[-1])[:20].strip("-")
        return f"{day}-{tail or 'link'}-{hashlib.md5(src.encode()).hexdigest()[:6]}"
    base = os.path.splitext(os.path.basename(src))[0]
    # 别把 re.sub 塞进 f-string：反斜杠在 3.12 之前的 f-string 表达式里是语法错误
    name = re.sub(r"[^\w一-鿿]+", "-", base)[:30].strip("-")
    return f"{day}-{name}"


def parse_srt(path):
    def ts(s):
        h, m, rest = s.split(":")
        sec, ms = rest.replace(".", ",").split(",")
        return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000.0

    cues = []
    blocks = open(path, encoding="utf-8-sig").read().replace("\r\n", "\n").strip().split("\n\n")
    for b in blocks:
        lines = [l for l in b.split("\n") if l.strip()]
        tl = next((l for l in lines if "-->" in l), None)
        if not tl:
            continue
        a, z = [p.strip() for p in tl.split("-->")]
        text = " ".join(lines[lines.index(tl) + 1:]).strip()
        if text:
            cues.append((ts(a), ts(z), text))
    return cues


def zh_len(s):
    return len(re.findall(r"[一-鿿]", s))


def rhythm_stats(cues, duration):
    """拆节奏用的确定性数据。文案逻辑本身由 agent 读 transcript.txt 判断。"""
    chars = sum(zh_len(t) for _, _, t in cues)
    speak = sum(z - a for a, z, _ in cues)
    gaps = [cues[i + 1][0] - cues[i][1] for i in range(len(cues) - 1)]
    hook = [t for a, _, t in cues if a < 3.0]
    lens = [zh_len(t) for _, _, t in cues]
    return {
        "duration_s": round(duration, 1),
        "cues": len(cues),
        "zh_chars": chars,
        # 我们写脚本按 320 字/分钟估时长，这个数能校准那个假设
        "chars_per_min": round(chars / speak * 60) if speak else None,
        "avg_cue_chars": round(sum(lens) / len(lens), 1) if lens else None,
        "max_cue_chars": max(lens) if lens else None,
        "hook_first_3s": "".join(hook),
        "longest_gap_s": round(max(gaps), 2) if gaps else 0,
        "gaps_over_0_5s": sum(1 for g in gaps if g > 0.5),
    }


def run_asr(video, out_srt):
    """没有烧录字幕时的兜底。需要 faster-whisper 且能下模型；未在云端验证。"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("  ⚠️ 没装 faster-whisper：pip install faster-whisper")
        return False
    print("  ASR 识别中（首次会下载模型）…")
    model = WhisperModel("small", device="auto", compute_type="int8")
    segs, _ = model.transcribe(video, language="zh", vad_filter=True)

    def fmt(t):
        h, rem = divmod(t, 3600)
        m, s = divmod(rem, 60)
        return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")

    with open(out_srt, "w", encoding="utf-8") as fh:
        for i, s in enumerate(segs, 1):
            fh.write(f"{i}\n{fmt(s.start)} --> {fmt(s.end)}\n{s.text.strip()}\n\n")
    return True


def probe_duration(video):
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=nw=1:nk=1", video],
            capture_output=True, text=True, check=True,
        ).stdout
        return float(out.strip())
    except Exception:
        return 0.0


def ingest(src, is_url, ocr_lang, asr, keep_video):
    slug = slug_for(src)
    dest = os.path.join(REFS, slug)
    os.makedirs(dest, exist_ok=True)
    print(f"\n━━ {slug}")

    tmp = None
    try:
        if is_url:
            tmp = tempfile.mkdtemp(prefix="ref-")
            video = download(src, tmp)
        else:
            video = os.path.abspath(os.path.expanduser(src))
            if not os.path.exists(video):
                print(f"  ❌ 找不到 {video}")
                return None

        dec = os.path.join(dest, "decompose")
        decompose(video, dec, ocr_lang)
        duration = probe_duration(video)

        srt = os.path.join(dec, "packaging", "subtitles.srt")
        source = "ocr"
        if not os.path.exists(srt) or not parse_srt(srt):
            print("  ⚠️ 没识别到烧录字幕")
            srt = os.path.join(dest, "asr.srt")
            if asr and run_asr(video, srt):
                source = "asr"
            else:
                print("  文案为空。这条片子可能没烧字幕——加 --asr 走语音识别。")
                srt = None

        meta = {"source": src, "ingested": datetime.datetime.now().isoformat(timespec="seconds"),
                "transcript_from": source if srt else None}

        if srt:
            cues = parse_srt(srt)
            shutil.copy(srt, os.path.join(dest, "transcript.srt"))
            with open(os.path.join(dest, "transcript.txt"), "w", encoding="utf-8") as fh:
                fh.write("\n".join(t for _, _, t in cues) + "\n")
            stats = rhythm_stats(cues, duration)
            json.dump(stats, open(os.path.join(dest, "stats.json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print(f"  文案 {stats['cues']} 句 / {stats['zh_chars']} 字 / "
                  f"语速 {stats['chars_per_min']} 字/分钟（来源：{source}）")
            print(f"  前 3 秒：{stats['hook_first_3s'] or '（无）'}")

        try:
            m = analyse(dec)
            style = {
                "measured": m | {"anims": dict(m["anims"])},
                "suggest": {
                    "sub_y": round(1 - 2 * m["y_center"], 2),
                    "sub_color": hex_to_rgb01(m["fill"]) if m["fill"] else None,
                    "stroke_hex": m["stroke"],
                },
            }
            json.dump(style, open(os.path.join(dest, "style.json"), "w", encoding="utf-8"),
                      ensure_ascii=False, indent=2)
            print(f"  字幕样式：sub_y={style['suggest']['sub_y']:+.2f}  填充 {m['fill']}  描边 {m['stroke']}")
        except SystemExit as e:
            print(f"  （样式跳过：{e}）")

        if keep_video:
            shutil.copy(video, os.path.join(dest, "video" + os.path.splitext(video)[1]))

        json.dump(meta, open(os.path.join(dest, "source.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        return dest
    except SystemExit as e:
        print(f"  ❌ {e}")
        return None
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="参考片摄取：文案 + 节奏 + 字幕样式")
    ap.add_argument("--url", action="append", default=[], help="参考片链接，可重复（本机跑）")
    ap.add_argument("--video", action="append", default=[], help="本地参考片，可重复")
    ap.add_argument("--ocr-lang", choices=["zh", "ja"], help="字幕语言，默认 zh")
    ap.add_argument("--asr", action="store_true", help="没烧字幕时用 faster-whisper 兜底（未在云端验证）")
    ap.add_argument("--keep-video", action="store_true", help="把原片也存进 refs/")
    args = ap.parse_args()
    if not args.url and not args.video:
        ap.error("至少给一个 --url 或 --video")

    done = []
    for u in args.url:
        done.append(ingest(u, True, args.ocr_lang, args.asr, args.keep_video))
    for v in args.video:
        done.append(ingest(v, False, args.ocr_lang, args.asr, args.keep_video))

    ok = [d for d in done if d]
    print(f"\n完成 {len(ok)}/{len(done)} 条，存在 {REFS}")
    for d in ok:
        print(f"  {os.path.relpath(d, REPO)}")
    if ok:
        print("\n下一步：让 Claude 读 refs/*/transcript.txt 拆文案逻辑（koubo-style「拆参考片」一节）。")


if __name__ == "__main__":
    main()
