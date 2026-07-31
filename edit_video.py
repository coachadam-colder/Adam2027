#!/usr/bin/env python3
"""生成剪映草稿：导入主视频 + SRT 字幕 + 背景音乐。

用法（本机需已安装剪映专业版 v5.9+）：

    python edit_video.py --video ~/Movies/raw.mp4 \
                         --srt   ~/Movies/raw.srt \
                         --bgm   ~/Music/bgm.mp3 \
                         --name  "我的第一个视频"

跑完后打开剪映，草稿列表里就能看到 --name 指定的项目。
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

# --- 环境初始化：定位 jianying-editor skill（见 rules/setup.md）---
current_dir = os.path.dirname(os.path.abspath(__file__))
env_root = os.getenv("JY_SKILL_ROOT", "").strip()
skill_candidates = [
    env_root,
    os.path.join(current_dir, ".agent", "skills", "jianying-editor"),
    os.path.join(current_dir, ".trae", "skills", "jianying-editor"),
    os.path.join(current_dir, ".claude", "skills", "jianying-editor"),
    os.path.join(current_dir, "skills", "jianying-editor"),
]

scripts_path = None
attempted = []
for p in skill_candidates:
    if not p:
        continue
    p = os.path.abspath(p)
    attempted.append(p)
    if os.path.exists(os.path.join(p, "scripts", "jy_wrapper.py")):
        scripts_path = os.path.join(p, "scripts")
        break

if not scripts_path:
    raise ImportError(
        "找不到 jianying-editor/scripts/jy_wrapper.py\n已尝试:\n- " + "\n- ".join(attempted)
    )

if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

# macOS 上 Homebrew 装的 ffmpeg 不在默认 PATH 里
if sys.platform == "darwin":
    for extra in ("/opt/homebrew/bin", "/usr/local/bin"):
        if extra not in os.environ.get("PATH", ""):
            os.environ["PATH"] = extra + ":" + os.environ.get("PATH", "")

# 必须先导入 jy_wrapper：它会调用 setup_env() 把 vendor 目录挂上 sys.path
from jy_wrapper import JyProject  # noqa: E402
import pyJianYingDraft as draft  # noqa: E402


def ensure_media_tools():
    """检查 ffmpeg / ffprobe。

    注意：imageio-ffmpeg 只附带 ffmpeg，不含 ffprobe——绝不要把 ffprobe 软链到
    ffmpeg 二进制上，skill 内部的 get_duration_ffprobe_cached() 会因此静默拿到
    错误时长。ffprobe 缺失时只告警，时长改由 pymediainfo 兜底。
    """
    if not shutil.which("ffmpeg"):
        try:
            import imageio_ffmpeg

            bin_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
            os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")
        except ImportError:
            pass

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        print(
            "⚠️ 未找到完整的 ffmpeg/ffprobe。webm 转码和部分时长探测会受影响。\n"
            "   macOS: brew install ffmpeg    Windows: winget install Gyan.FFmpeg"
        )


def probe_resolution(video_path):
    """读取视频宽高，用于判断横屏还是竖屏。失败则返回 None。"""
    try:
        from pymediainfo import MediaInfo

        for track in MediaInfo.parse(video_path).tracks:
            if track.track_type == "Video" and track.width and track.height:
                return int(track.width), int(track.height)
    except Exception:
        pass

    if not shutil.which("ffprobe"):
        return None
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json", video_path,
            ],
            capture_output=True, text=True, check=True,
        ).stdout
        stream = json.loads(out)["streams"][0]
        return int(stream["width"]), int(stream["height"])
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser(description="用 jianying-editor 生成剪映草稿")
    ap.add_argument("--video", required=True, help="主视频文件路径")
    ap.add_argument("--srt", help="SRT 字幕文件路径（可选）")
    ap.add_argument("--bgm", help="背景音乐文件路径（可选）")
    ap.add_argument("--name", default="我的第一个视频", help="剪映草稿名")
    ap.add_argument("--bgm-volume", type=float, default=0.15, help="BGM 音量，0-1，默认 0.15")
    ap.add_argument(
        "--drafts-root",
        help="剪映草稿目录。不填则自动探测；Linux 等无剪映的环境必须显式指定。",
    )
    args = ap.parse_args()

    ensure_media_tools()

    video = os.path.abspath(os.path.expanduser(args.video))
    if not os.path.exists(video):
        sys.exit(f"找不到视频文件: {video}")

    # 项目分辨率必须跟主素材比例一致，否则剪映里会有黑边
    width, height = 1920, 1080
    res = probe_resolution(video)
    if res:
        src_w, src_h = res
        width, height = (1080, 1920) if src_h > src_w else (1920, 1080)
        print(f"素材分辨率 {src_w}x{src_h} -> 项目按 {width}x{height} 创建")

    project = JyProject(
        args.name,
        width=width,
        height=height,
        drafts_root=os.path.expanduser(args.drafts_root) if args.drafts_root else None,
        overwrite=True,
    )

    project.add_media_safe(video, start_time="0s")
    print(f"已导入主视频: {os.path.basename(video)}")

    if args.srt:
        srt = os.path.abspath(os.path.expanduser(args.srt))
        if not os.path.exists(srt):
            sys.exit(f"找不到字幕文件: {srt}")
        project.script.import_srt(
            srt,
            track_name="Subtitles",
            clip_settings=draft.ClipSettings(transform_y=-0.8),
        )
        print(f"已导入字幕: {os.path.basename(srt)}")

    if args.bgm:
        bgm = os.path.abspath(os.path.expanduser(args.bgm))
        if not os.path.exists(bgm):
            sys.exit(f"找不到音乐文件: {bgm}")
        project.add_audio_safe(bgm, start_time="0s", track_name="BGM", volume=args.bgm_volume)
        print(f"已导入 BGM: {os.path.basename(bgm)}（音量 {args.bgm_volume}）")

    project.save()

    # 验收检查（见 rules/core.md 的 Acceptance Checks）
    print("\n--- 验收 ---")
    print(f"草稿目录: {project.draft_dir}")
    for track_name, track in project.script.tracks.items():
        print(f"  轨道 {track_name}: {len(track.segments)} 个片段")
    print("\n打开剪映即可看到这个草稿。")


if __name__ == "__main__":
    main()
