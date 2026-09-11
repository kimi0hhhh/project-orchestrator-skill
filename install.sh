#!/usr/bin/env bash
# Project Orchestrator Skill 安装脚本（ZCode）
# 用法：bash install.sh
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
SKILL_DIR="${HOME}/.zcode/skills/project-orchestrator"
AGENTS_DIR="${HOME}/.zcode/agents"

echo "[1/3] 安装 skill → ${SKILL_DIR}"
mkdir -p "${SKILL_DIR}"
cp "${SRC}/SKILL.md" "${SKILL_DIR}/SKILL.md"

echo "[2/3] 安装角色契约 → ${AGENTS_DIR}"
mkdir -p "${AGENTS_DIR}"
for f in "${SRC}"/agents/*.md; do
  cp "${f}" "${AGENTS_DIR}/$(basename "$f")"
done

echo "[3/3] 完成。"
echo "  - 重启 ZCode 会话（角色清单在会话启动时加载）"
echo "  - 新会话里说「启动主 Agent」即可唤醒编排模式"
echo "  - 可选：安装 pm-skills / Matt Pocock skill 集以获得完整 skill 引用（见 docs/CREDITS.md）"
