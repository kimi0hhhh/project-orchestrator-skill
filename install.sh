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

echo "[2/4] 安装角色契约 → ${AGENTS_DIR}"
mkdir -p "${AGENTS_DIR}"
for f in "${SRC}"/agents/*.md; do
  cp "${f}" "${AGENTS_DIR}/$(basename "$f")"
done

echo "[3/4] 安装协作运行时（看板/账本/看门狗） → ${SKILL_DIR}/runtime"
mkdir -p "${SKILL_DIR}/runtime"
cp "${SRC}"/runtime/*.py "${SKILL_DIR}/runtime/"
cp -r "${SRC}/runtime/lib" "${SRC}/runtime/ui" "${SKILL_DIR}/runtime/"
find "${SKILL_DIR}/runtime" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

echo "[4/4] 完成。"
echo "  - 重启 ZCode 会话（角色清单在会话启动时加载）"
echo "  - 新会话里说「启动主 Agent」即可唤醒编排模式"
echo "  - 看板：在项目工作区跑 python ${SKILL_DIR}/runtime/daemon.py 8788"
echo "  - 可选：安装 pm-skills / Matt Pocock skill 集以获得完整 skill 引用（见 docs/CREDITS.md）"
