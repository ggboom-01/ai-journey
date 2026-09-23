<#
  ai-journey · 一键接上 GitHub

  用法（双击 setup.bat，或在 D:\ai-journey 目录执行）：
      powershell -ExecutionPolicy Bypass -File .\setup-remote.ps1

  可选参数：
      -Email  "you@example.com"   不填则自动从 GitHub 读取
      -Name   "你的昵称"            不填则用 GitHub 用户名
      -RepoName "ai-journey"
      -Private                     建私有仓库（默认 public）

  前置条件：已执行过 gh auth login 并授权成功。
  脚本可重复执行，不会重复建仓库或重复提交。
#>

param(
    [string]$Email = "",
    [string]$Name = "",
    [string]$RepoName = "ai-journey",
    [switch]$Private
)

# 注意：原生命令（git / gh）在 ErrorActionPreference=Stop 时，
# 仅因往 stderr 写日志就会被当成终止性错误，所以这里必须用 Continue，
# 由脚本显式检查 $LASTEXITCODE。
$ErrorActionPreference = "Continue"
Set-Location -Path $PSScriptRoot

# ---------- 0. 找到 gh ----------
$gh = (Get-Command gh -ErrorAction SilentlyContinue).Source
if (-not $gh) {
    foreach ($p in @("$env:ProgramFiles\GitHub CLI\gh.exe", "${env:ProgramFiles(x86)}\GitHub CLI\gh.exe")) {
        if (Test-Path $p) { $gh = $p; break }
    }
}
if (-not $gh) {
    Write-Host "未找到 gh（GitHub CLI）。请先执行：winget install --id GitHub.cli，然后重开一个终端窗口。" -ForegroundColor Red
    exit 1
}

# ---------- 1. 校验登录 ----------
& $gh auth status 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "还没有登录 GitHub。请先执行下面这条命令，按提示在浏览器里授权：" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "    gh auth login" -ForegroundColor White
    Write-Host ""
    Write-Host "选项依次选：GitHub.com -> HTTPS -> Yes（用 git 凭据）-> Login with a web browser" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "授权完成后，再重新运行本脚本即可。" -ForegroundColor DarkGray
    exit 1
}

$ghUser = (& $gh api user --jq .login 2>$null | Select-Object -First 1)
if ([string]::IsNullOrWhiteSpace($ghUser)) {
    Write-Host "无法读取 GitHub 账号信息，请确认 gh auth login 已完成。" -ForegroundColor Red
    exit 1
}
$ghUser = $ghUser.Trim()
Write-Host "[1/5] GitHub 账号：$ghUser" -ForegroundColor Cyan

# ---------- 2. 确定提交身份 ----------
if ([string]::IsNullOrWhiteSpace($Name)) { $Name = $ghUser }

if ([string]::IsNullOrWhiteSpace($Email)) {
    # 依次尝试：公开邮箱 -> 账号主邮箱 -> noreply 兜底
    $Email = (& $gh api user --jq '.email // empty' 2>$null | Select-Object -First 1)
    if ([string]::IsNullOrWhiteSpace($Email)) {
        $Email = (& $gh api user/emails --jq '.[] | select(.primary) | .email' 2>$null | Select-Object -First 1)
    }
    if ([string]::IsNullOrWhiteSpace($Email)) {
        $Email = "$ghUser@users.noreply.github.com"
        Write-Host "      未能读取到你的邮箱，暂用 noreply 地址。" -ForegroundColor Yellow
        Write-Host "      若提交没关联到你的头像，请带 -Email 参数重跑本脚本。" -ForegroundColor Yellow
    }
}
$Email = $Email.Trim()

& git config --global user.name  $Name
& git config --global user.email $Email
& git config --global init.defaultBranch main
Write-Host "[2/5] git 身份：$Name <$Email>" -ForegroundColor Cyan

# ---------- 3. 本地仓库 + 首次提交 ----------
if (-not (Test-Path ".git")) { & git init 2>&1 | Out-Null }
& git branch -M main 2>&1 | Out-Null

& git add -A 2>&1 | Out-Null
& git diff --cached --quiet 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    & git commit -m "chore: 初始化 ai-journey 学习仓库" 2>&1 | Out-Null
    Write-Host "[3/5] 首次提交完成" -ForegroundColor Cyan
} else {
    Write-Host "[3/5] 无待提交改动，跳过" -ForegroundColor DarkGray
}

# ---------- 4. 远端仓库 ----------
& $gh repo view "$ghUser/$RepoName" 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[4/5] 远端仓库已存在，直接关联" -ForegroundColor Yellow
} else {
    $vis = if ($Private) { "--private" } else { "--public" }
    & $gh repo create "$ghUser/$RepoName" $vis --description "我的 AI 学习轨迹：笔记、每周练习、作品集" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[4/5] 创建仓库失败，请检查网络或 gh 授权范围。" -ForegroundColor Red
        exit 1
    }
    Write-Host "[4/5] 已在 GitHub 创建仓库（$vis）" -ForegroundColor Cyan
}

& git remote remove origin 2>&1 | Out-Null
& git remote add origin "https://github.com/$ghUser/$RepoName.git" 2>&1 | Out-Null

# ---------- 5. 推送 ----------
& git push -u origin main
if ($LASTEXITCODE -ne 0) {
    Write-Host "[5/5] 推送失败。若提示认证问题，请先执行 gh auth setup-git 后重试。" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[5/5] 全部完成！" -ForegroundColor Green
Write-Host "仓库地址：https://github.com/$ghUser/$RepoName" -ForegroundColor Green
Write-Host ""
Write-Host "下一步：去仓库 README 里把进度表的空格逐个改成已完成标记。" -ForegroundColor DarkGray
