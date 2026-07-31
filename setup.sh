#!/usr/bin/env bash
# 一次性环境配置（macOS / Linux）。Windows 用 setup.ps1。
set -euo pipefail
cd "$(dirname "$0")"

echo "==> 检查 Python"
command -v python3 >/dev/null || { echo "❌ 没有 python3，先装 Python 3.10+"; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
  || { echo "❌ Python 版本太低，需要 3.10+"; exit 1; }
python3 --version

echo "==> 建虚拟环境 .venv"
[ -d .venv ] || python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> 装依赖"
pip install --quiet --upgrade pip
pip install --quiet -r .claude/skills/jianying-editor/requirements.txt || {
  echo "⚠️ 完整依赖装失败（uiautomation 只支持 Windows，macOS 上失败是正常的）"
  echo "   改装剪辑必需的子集..."
  pip install --quiet pymediainfo requests psutil imageio numpy edge-tts opencv-python
}

echo "==> 检查 ffmpeg / ffprobe"
if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then
  echo "✅ $(ffmpeg -version | head -1 | cut -c1-40)"
else
  echo "❌ 缺 ffmpeg 或 ffprobe。装法："
  echo "   macOS:  brew install ffmpeg"
  echo "   Linux:  sudo apt install ffmpeg"
  echo "   注意：pip 的 imageio-ffmpeg 只有 ffmpeg 没有 ffprobe，不够用，"
  echo "        也千万别把 ffprobe 软链到它的二进制上（会静默读到错误时长）。"
fi

echo "==> 检查剪映草稿目录"
python3 - <<'PY'
import sys, os
sys.path.insert(0, os.path.join(".claude", "skills", "jianying-editor", "scripts"))
try:
    from utils.formatters import get_default_drafts_root
    root = get_default_drafts_root()
except Exception as exc:
    print(f"⚠️ 探测失败: {exc}")
    sys.exit(0)
if os.path.isdir(root):
    print(f"✅ 找到剪映草稿目录: {root}")
else:
    print(f"⚠️ 没找到剪映草稿目录（探测到 {root}）")
    print("   剪映装了吗？没装的话脚本还能生成草稿，但打不开。")
    print("   路径不对可以跑脚本时用 --drafts-root 显式指定。")
PY

cat <<'EOF'

==> 配置完成

每次开工前先激活环境：
    source .venv/bin/activate

跑一条：
    python make_talking_head.py --video 原片.mp4 --srt 字幕.srt \
                                --plan content/01-keqi/plan.json --name "客气"

方法论在 .claude/skills/koubo-style/SKILL.md 和 content/PLAN.md。
EOF
