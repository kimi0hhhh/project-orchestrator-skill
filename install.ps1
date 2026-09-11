# Project Orchestrator Skill 安装脚本（ZCode / Windows）
# 用法：powershell -File install.ps1
$ErrorActionPreference = "Stop"

$Src       = $PSScriptRoot
$SkillDir  = Join-Path $env:USERPROFILE ".zcode\skills\project-orchestrator"
$AgentsDir = Join-Path $env:USERPROFILE ".zcode\agents"

Write-Host "[1/3] 安装 skill -> $SkillDir"
New-Item -ItemType Directory -Force -Path $SkillDir | Out-Null
Copy-Item (Join-Path $Src "SKILL.md") (Join-Path $SkillDir "SKILL.md") -Force

Write-Host "[2/3] 安装角色契约 -> $AgentsDir"
New-Item -ItemType Directory -Force -Path $AgentsDir | Out-Null
Copy-Item (Join-Path $Src "agents\*.md") $AgentsDir -Force

Write-Host "[3/3] 完成。"
Write-Host "  - 重启 ZCode 会话（角色清单在会话启动时加载）"
Write-Host "  - 新会话里说「启动主 Agent」即可唤醒编排模式"
Write-Host "  - 可选：安装 pm-skills / Matt Pocock skill 集以获得完整 skill 引用（见 docs/CREDITS.md）"
