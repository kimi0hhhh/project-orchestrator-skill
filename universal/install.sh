#!/usr/bin/env bash
# Project Orchestrator 通用版 · 工作区安装脚本
# 用法：bash install.sh <工作区绝对路径>
# 行为：把协议/契约/协议文件/模板/runtime 铺进 <工作区>/.orchestrator/ 与 <工作区>/runtime/
#       已存在的同名文件一律跳过（不覆盖工作区已有内容）
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
WS="${1:?用法: bash install.sh <工作区绝对路径>}"
BASE="${WS}/.orchestrator"

[ -d "$WS" ] || { echo "错误：工作区不存在 $WS"; exit 1; }
mkdir -p "${BASE}/agents" "${BASE}/protocols" "${BASE}/state" "${WS}/docs"

copy_new() { # copy_new <src> <dst> —— 目标已存在则跳过
  [ -e "$2" ] && { echo "  跳过（已存在）: $2"; return; }
  cp "$1" "$2" && echo "  安装: $2"
}

echo "[1/5] 协议本体 → ${BASE}/"
copy_new "${SRC}/SKILL.md"            "${BASE}/SKILL.md"
copy_new "${SRC}/platform-config.md"  "${BASE}/platform-config.md"

echo "[2/5] 角色契约 → ${BASE}/agents/"
for f in "${SRC}"/agents/*.md; do copy_new "$f" "${BASE}/agents/$(basename "$f")"; done

echo "[3/5] 协议文件 → ${BASE}/protocols/"
for f in "${SRC}"/protocols/*.md; do copy_new "$f" "${BASE}/protocols/$(basename "$f")"; done

echo "[4/5] 模板与状态 → ${BASE}/  ${WS}/docs/"
copy_new "${SRC}/templates/PROJECT_BRIEF.md" "${WS}/docs/PROJECT_BRIEF.md"
[ -e "${BASE}/state/open-issues.md" ] || touch "${BASE}/state/open-issues.md"

echo "[5/5] 运行时（可选） → ${WS}/runtime/"
RT="$(cd "${SRC}/.." && pwd)/runtime"
if [ -d "$RT" ]; then
  mkdir -p "${WS}/runtime/lib"
  for f in "${RT}"/*.py; do copy_new "$f" "${WS}/runtime/$(basename "$f")"; done
  copy_new "${RT}/lib/store.py" "${WS}/runtime/lib/store.py"
  copy_new "${RT}/lib/usage.py" "${WS}/runtime/lib/usage.py"
  [ -d "${RT}/ui" ] && [ ! -e "${WS}/runtime/ui" ] && cp -r "${RT}/ui" "${WS}/runtime/ui" && echo "  安装: ${WS}/runtime/ui"
else
  echo "  未找到 runtime/（独立分发时随包携带），跳过——看板降级为 markdown"
fi

echo ""
echo "完成。下一步："
echo "  1. 填 ${BASE}/platform-config.md（8 项原语 + 能力档位，见 ${SRC}/PORTING.md）"
echo "  2. 填 ${WS}/docs/PROJECT_BRIEF.md 产品输入书"
echo "  3. 在 ${TOOL_NAME:-你的工具} 会话里说「启动主 Agent」唤醒编排模式"
