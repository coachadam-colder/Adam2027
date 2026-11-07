#!/usr/bin/env python3
"""拿参考片反推 presets/koubo.py 的 STYLE 数值。

    python calibrate.py --url https://v.douyin.com/xxxxx/      # 本机跑，会先下载
    python calibrate.py --video 参考片.mp4                      # 已经有文件

做三件事：下载（可选）→ rea-video decompose → 把测量值换算成 STYLE 建议值。

换算依据见 .claude/skills/koubo-style/SKILL.md「校准流程」，其中位置、字号、
颜色三项已对照已知输入验证过；其余项标了「未验证」，照抄前自己看一眼。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter

REPO = os.path.dirname(os.path.abspath(__file__))


def need(cmd, hint):
    if not shutil.which(cmd):
        sys.exit(f"找不到 {cmd}。{hint}")
    return cmd


def download(url, dest_dir):
    """用 yt-dlp 把链接下成本地文件，返回路径。"""
    need("yt-dlp", "跑 ./setup.sh，或 pip install yt-dlp")
    out = os.path.join(dest_dir, "ref.%(ext)s")
    print(f"下载 {url}")
    proc = subprocess.run(
        ["yt-dlp", "-f", "mp4/best", "-o", out, "--no-playlist", url],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-4:]
        sys.exit("下载失败：\n  " + "\n  ".join(tail))
    files = [f for f in os.listdir(dest_dir) if f.startswith("ref.")]
    if not files:
        sys.exit("yt-dlp 说成功了但没产出文件，检查链接。")
    return os.path.join(dest_dir, files[0])


def decompose(video, out_dir, ocr_lang):
    need("rea-video", "跑 ./setup.sh")
    need("ffprobe", "macOS: brew install ffmpeg  /  Windows: winget install Gyan.FFmpeg")
    cmd = ["rea-video", "decompose", video, "-o", out_dir]
    if ocr_lang:
        cmd += ["--ocr-lang", ocr_lang]
    print(f"拆解 {os.path.basename(video)} …（每分钟素材约 30–50 秒）")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-6:]
        sys.exit("decompose 失败：\n  " + "\n  ".join(tail))
    return out_dir


def hex_to_rgb01(h):
    h = h.lstrip("#")
    return tuple(round(int(h[i:i + 2], 16) / 255, 3) for i in (0, 2, 4))


def analyse(out_dir):
    path = os.path.join(out_dir, "packaging", "timeline.json")
    if not os.path.exists(path):
        sys.exit(f"没有 {path}——参考片可能没有字幕，或 decompose 跳过了包装层。")
    texts = json.load(open(path, encoding="utf-8")).get("text", [])
    if not texts:
        sys.exit("timeline.json 里没有文字层，这条参考片可能没有字幕。")

    # 正文字幕 = 画面下半部、数量最多的那一群；标题/花字在别处，先不混进来
    lower = [t for t in texts if (t["bbox"][1] + t["bbox"][3] / 2) > 0.55]
    pool = lower or texts
    if not lower:
        print("⚠️ 没有落在画面下半部的文字，下面按全部文字层算，可能混进了标题。")

    ycs = sorted((t["bbox"][1] + t["bbox"][3] / 2) for t in pool)
    heights = sorted(t["bbox"][3] for t in pool)
    mid = lambda xs: xs[len(xs) // 2]

    fills = Counter(t["style"].get("fill") for t in pool if t["style"].get("fill"))
    strokes = Counter(t["style"].get("stroke") for t in pool if t["style"].get("stroke"))

    return {
        "n": len(pool),
        "y_center": mid(ycs),
        "height": mid(heights),
        "fill": fills.most_common(1)[0][0] if fills else None,
        "stroke": strokes.most_common(1)[0][0] if strokes else None,
        "anims": Counter(
            (t.get("anim_in") or {}).get("kind_zh") for t in pool if t.get("anim_in")
        ),
    }


def report(m, out_dir):
    print("\n" + "=" * 58)
    print(f"参考片字幕测量（{m['n']} 条文字层）")
    print("=" * 58)
    print(f"  y 中心      {m['y_center']:.3f}   （0=顶 1=底）")
    print(f"  字高占比    {m['height']:.4f}")
    print(f"  填充色      {m['fill']}")
    print(f"  描边色      {m['stroke']}")
    if m["anims"]:
        print(f"  入场动画    {dict(m['anims'])}")

    print("\n--- 改 presets/koubo.py 的 STYLE ---")
    print(f'  "sub_y": {1 - 2 * m["y_center"]:+.2f},          # ✅ 位置映射已验证')
    if m["fill"]:
        print(f'  "sub_color": {hex_to_rgb01(m["fill"])},   # ✅ 颜色读取已验证')
    print(f'  # 描边色 {m["stroke"]} -> 改 presets/koubo.py 的 _border()')

    print("\n--- sub_size 要跑第二轮（比例法）---")
    print("  剪映字号标度和像素没有公开对应关系，所以：")
    print("   1. 用当前 STYLE 生成一条草稿，在剪映里导出成片")
    print(f"   2. python calibrate.py --video 导出的成片.mp4")
    print(f"   3. 新 sub_size = 当前 sub_size × ({m['height']:.4f} ÷ 第二轮测到的字高)")

    print("\n--- 没自动换算的（SKILL.md 里标了未验证）---")
    print("  BGM 音量   rea-video stems 参考片.mp4 -o out/ref  后比人声/配乐电平")
    print("  静音阈值   rea-video summary 的「剪辑:」行")
    print("  描边粗细   style.stroke_ratio 不是像素宽，只能横向比较，别直接抄")

    print(f"\n完整报告：{os.path.join(out_dir, 'report.html')}")
    print("改完请在 STYLE 上方注释写明来源参考片和日期。")


def main():
    ap = argparse.ArgumentParser(description="拿参考片反推 STYLE")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--url", help="参考片链接（本机跑；云端会话的网络策略拦截视频站）")
    src.add_argument("--video", help="已经下载好的参考片")
    ap.add_argument("--out", default="out/ref", help="拆解结果目录，默认 out/ref")
    ap.add_argument("--ocr-lang", choices=["zh", "ja"], help="字幕语言，默认 zh")
    args = ap.parse_args()

    tmp = None
    try:
        if args.url:
            tmp = tempfile.mkdtemp(prefix="calib-")
            video = download(args.url, tmp)
        else:
            video = os.path.abspath(os.path.expanduser(args.video))
            if not os.path.exists(video):
                sys.exit(f"找不到 {video}")

        out_dir = os.path.abspath(args.out)
        decompose(video, out_dir, args.ocr_lang)
        report(analyse(out_dir), out_dir)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
