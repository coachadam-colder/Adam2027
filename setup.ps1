# 一次性环境配置（Windows）。macOS / Linux 用 setup.sh。
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> 检查 Python"
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Host "❌ 没有 python，先装 Python 3.10+"; exit 1 }
python --version

Write-Host "==> 建虚拟环境 .venv"
if (-not (Test-Path .venv)) { python -m venv .venv }
& .\.venv\Scripts\Activate.ps1

Write-Host "==> 装依赖"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r .claude\skills\jianying-editor\requirements.txt

Write-Host "==> 检查 ffmpeg / ffprobe"
$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
$fp = Get-Command ffprobe -ErrorAction SilentlyContinue
if ($ff -and $fp) {
    Write-Host "✅ ffmpeg 和 ffprobe 都在"
} else {
    Write-Host "❌ 缺 ffmpeg 或 ffprobe。装法： winget install Gyan.FFmpeg"
    Write-Host "   注意：pip 的 imageio-ffmpeg 只有 ffmpeg 没有 ffprobe，不够用。"
}

Write-Host "==> 检查剪映草稿目录"
python -c @"
import sys, os
sys.path.insert(0, os.path.join('.claude','skills','jianying-editor','scripts'))
try:
    from utils.formatters import get_default_drafts_root
    root = get_default_drafts_root()
except Exception as exc:
    print(f'警告 探测失败: {exc}'); sys.exit(0)
print(('OK 找到剪映草稿目录: ' if os.path.isdir(root) else '警告 没找到（探测到）: ') + root)
"@

Write-Host ""
Write-Host "==> 配置完成"
Write-Host "每次开工前激活环境:  .\.venv\Scripts\Activate.ps1"
Write-Host "Windows 独有：装了剪映 v5.9 或更低版本时，可以用 auto_exporter.py 自动导出成片。"
Write-Host "方法论在 .claude\skills\koubo-style\SKILL.md 和 content\PLAN.md"
