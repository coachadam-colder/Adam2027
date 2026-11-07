# 一键把整套工作流装到 E 盘（Windows）。
#
# 第一次用，在 PowerShell 里粘这两行：
#   git clone -b claude/short-video-workflow-skills-6lg4lb https://github.com/coachadam-colder/Adam2027.git E:\Adam2027
#   powershell -ExecutionPolicy Bypass -File E:\Adam2027\bootstrap_e.ps1
#
# 以后要更新，再跑第二行就行——已经克隆过会改成拉取最新。
#
# 只用 Windows PowerShell 5.1 也认的语法（不用 && / ?? / 三元），
# 文件存成 UTF-8 带 BOM，否则中文系统的 5.1 会按 GBK 读、中文全乱码。

param(
    [string]$Drive  = "E:",
    [string]$Branch = "claude/short-video-workflow-skills-6lg4lb",
    [string]$Repo   = "https://github.com/coachadam-colder/Adam2027.git"
)

$ErrorActionPreference = "Stop"
$Root = Join-Path $Drive "Adam2027"

function Fail($msg) { Write-Host "❌ $msg" -ForegroundColor Red; exit 1 }

# 5.1 里原生命令失败不会抛异常，得自己看退出码
function Run($desc) {
    if ($LASTEXITCODE -ne 0) { Fail "$desc 失败（退出码 $LASTEXITCODE）" }
}

Write-Host "==> 检查 $Drive 盘"
if (-not (Test-Path "$Drive\")) { Fail "找不到 $Drive 盘。换盘符：-Drive D:" }

Write-Host "==> 检查工具"
$missing = @()
if (-not (Get-Command git    -ErrorAction SilentlyContinue)) { $missing += "Git.Git" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { $missing += "Python.Python.3.11" }
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) { $missing += "Gyan.FFmpeg" }
if ($missing.Count -gt 0) {
    Write-Host "缺这些，逐个装："
    foreach ($m in $missing) { Write-Host "    winget install $m" }
    Fail "装完关掉并重开 PowerShell（PATH 才会刷新），再跑一次本脚本。"
}

Write-Host "==> 代码 -> $Root"
if (Test-Path (Join-Path $Root ".git")) {
    Set-Location $Root
    git fetch origin $Branch;              Run "git fetch"
    git checkout $Branch;                  Run "git checkout"
    git pull --ff-only origin $Branch;     Run "git pull（本地有未提交改动的话先处理掉）"
} else {
    git clone -b $Branch $Repo $Root;      Run "git clone（私有仓库会弹浏览器让你登录 GitHub）"
    Set-Location $Root
}

Write-Host "==> 工作目录"
foreach ($d in @("素材", "成片", "refs")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $Root $d) | Out-Null
    Write-Host "    $Root\$d"
}

Write-Host "==> 剪映草稿目录"
# 脚本的自动探测只认 %LOCALAPPDATA% 下的默认位置。在剪映设置里挪过草稿位置的话，
# 探测会静默落到剪映不读的目录——草稿写了但剪映里看不到。用 JY_DRAFTS_ROOT 钉死。
$default = Join-Path $env:LOCALAPPDATA "JianyingPro\User Data\Projects\com.lveditor.draft"
$drafts  = [Environment]::GetEnvironmentVariable("JY_DRAFTS_ROOT", "User")
if ($drafts) {
    Write-Host "    已设置：$drafts"
} elseif (Test-Path $default) {
    $drafts = $default
    Write-Host "    找到默认位置：$drafts"
} else {
    Write-Host "    默认位置没有。打开剪映 → 右上角设置 → 草稿位置，把那个路径粘过来："
    $drafts = Read-Host "    草稿目录"
}
if ($drafts) {
    if (-not (Test-Path $drafts)) { Write-Host "    ⚠️ 这个目录现在不存在，确认剪映里的路径没抄错" -ForegroundColor Yellow }
    [Environment]::SetEnvironmentVariable("JY_DRAFTS_ROOT", $drafts, "User")
    $env:JY_DRAFTS_ROOT = $drafts
} else {
    Write-Host "    ⚠️ 没设置。剪辑时得每次带 --drafts-root" -ForegroundColor Yellow
}

Write-Host "==> 装依赖（setup.ps1）"
& (Join-Path $Root "setup.ps1")

Write-Host ""
Write-Host "==> 装好了" -ForegroundColor Green
Write-Host ""
Write-Host "目录："
Write-Host "    $Root\素材   你录的原片 + 剪映导出的 SRT 放这"
Write-Host "    $Root\refs   参考片摄取结果（extract.py 自动写）"
Write-Host "    $Root\成片   剪映导出的成片放这"
Write-Host ""
Write-Host "下一步：打开 Claude 桌面版 → Claude Code → 选文件夹 $Root"
Write-Host "然后直接说话就行，比如："
Write-Host "    「学一下这条：https://v.douyin.com/xxxx/」"
Write-Host "    「按第 1 条脚本剪：素材\客气.mp4 和 素材\客气.srt」"
