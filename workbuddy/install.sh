#!/usr/bin/env bash
# ============================================================
#  多 Agent 协作体系 · 安装到目标工作区
#  用法: bash install.sh <目标工作区路径>
#  例:   bash install.sh ~/WorkBuddy/my-project
#  特性: 不覆盖已存在的同名文件 (cp -n)
# ============================================================
set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="${1:-}"

if [[ -z "$DST" ]]; then
  echo "[!] 用法: bash install.sh <目标工作区路径>"
  exit 1
fi
mkdir -p "$DST"

copy_dir() {
  local from="$1" to="$2"
  mkdir -p "$to"
  cp -rn "$from"/. "$to"/ 2>/dev/null || true
  echo "  [ok] $to"
}

echo
echo "源:   $SRC  (project-orchestrator v4.1 / WorkBuddy 版)"
echo "目标: $DST"
echo

copy_dir "$SRC/agents"          "$DST/.workbuddy/agents"
copy_dir "$SRC/protocols"       "$DST/.workbuddy/protocols"
copy_dir "$SRC/templates/state" "$DST/.workbuddy/state"
_HAD_PROJ=0
if [[ -e "$DST/runtime/projects" ]]; then _HAD_PROJ=1; fi
copy_dir "$SRC/runtime"         "$DST/runtime"
# 首次安装时清掉源机的运行时状态：否则别人的 demo 项目、端口记录、日志会被一起
# 拷进新工作区 —— 用户一打开看板看到的是陌生项目（2026-09-12 实测踩到）。
# 只在「装之前目标里没有 projects」时清，避免误删已有工作区的真实数据。
if [[ "$_HAD_PROJ" == "0" ]]; then
  rm -rf "$DST/runtime/projects" "$DST/runtime/projects.json"
  rm -f  "$DST/runtime/.port" "$DST/runtime/.pid" "$DST/runtime/.server.pid" \
         "$DST/runtime/server.log" "$DST/runtime/board.log" "$DST/runtime/.lock"
fi
copy_dir "$SRC/docs"            "$DST/docs"

echo "--- 根目录文件 ---"
for f in ORCHESTRATOR.md README.md SKILL.md AGENTS.md; do
  if [[ -e "$DST/$f" ]]; then
    echo "  跳过（已存在）: $f"
  else
    cp -n "$SRC/$f" "$DST/$f" && echo "  已复制: $f"
  fi
done

echo
echo "==========================================================="
echo " 安装完成。下一步："
echo "  1. 填  $DST/docs/PROJECT_BRIEF.md  （必填四项）"
echo "  2. 起看板: python runtime/board.py wmi    (本机手动可用 board.py open)"
echo "  3. 告诉主 Agent: 「按 ORCHESTRATOR.md 跑 S1」"
echo "==========================================================="

# --- 移植完整性自检（v4.2）：四类文件齐 + cli.py 可用 + 契约可解析 ---
echo
echo "--- 移植完整性自检 ---"
_MISS=0
_chk() {  # $1=标签  $2=路径
  if [[ -s "$2" ]]; then echo "  [ok]   $1"; else echo "  [MISS] $1  ($2)"; _MISS=$((_MISS+1)); fi
}
_chk "契约 00-orchestrator"      "$DST/.workbuddy/agents/00-orchestrator.md"
_chk "契约 01-product-manager"   "$DST/.workbuddy/agents/01-product-manager.md"
_chk "契约 02-architect"         "$DST/.workbuddy/agents/02-architect.md"
_chk "契约 03-frontend-dev"      "$DST/.workbuddy/agents/03-frontend-dev.md"
_chk "契约 04-backend-dev"       "$DST/.workbuddy/agents/04-backend-dev.md"
_chk "契约 05-dev-lead"          "$DST/.workbuddy/agents/05-dev-lead.md"
_chk "契约 06-qa"                "$DST/.workbuddy/agents/06-qa.md"
_chk "协议 gate-rules"           "$DST/.workbuddy/protocols/gate-rules.md"
_chk "协议 handoff-schema"       "$DST/.workbuddy/protocols/handoff-schema.md"
_chk "协议 revision-loop"        "$DST/.workbuddy/protocols/revision-loop.md"
_chk "state board"               "$DST/.workbuddy/state/board.md"
_chk "state gate-log"            "$DST/.workbuddy/state/gate-log.md"
_chk "state open-issues"         "$DST/.workbuddy/state/open-issues.md"
_chk "runtime cli.py"            "$DST/runtime/cli.py"
_chk "runtime server.py"         "$DST/runtime/server.py"
_chk "runtime daemon.py"         "$DST/runtime/daemon.py"
_chk "runtime board.py"          "$DST/runtime/board.py"
_chk "runtime serve.cmd"         "$DST/runtime/serve.cmd"
_chk "runtime lib/store.py"      "$DST/runtime/lib/store.py"
_chk "runtime lib/contract.py"   "$DST/runtime/lib/contract.py"
_chk "runtime registry.json"     "$DST/runtime/registry.json"
_chk "运行时手册 ORCHESTRATOR"    "$DST/ORCHESTRATOR.md"

PY_BIN="$(command -v python || command -v python3 || true)"
if [[ -n "$PY_BIN" ]] && [[ -s "$DST/runtime/cli.py" ]]; then
  if (cd "$DST" && "$PY_BIN" runtime/cli.py --help >/dev/null 2>&1); then
    echo "  [ok]   cli.py --help 可用"
  else
    echo "  [WARN] cli.py --help 执行失败（检查 python 环境）"
  fi
  # v4.2：契约内联链路自检 —— 7 份契约能被 contract.py 解析、且 pre-flight 校验生效
  if (cd "$DST" && "$PY_BIN" runtime/cli.py contracts >/dev/null 2>&1); then
    _N=$(cd "$DST" && "$PY_BIN" runtime/cli.py contracts 2>/dev/null | grep -c '^  \[ok \]')
    echo "  [ok]   cli.py contracts 可用（解析到 $_N/7 份契约）"
    [[ "$_N" == "7" ]] || { echo "  [WARN] 契约解析数不是 7，检查 .workbuddy/agents/"; _MISS=$((_MISS+1)); }
  else
    echo "  [WARN] cli.py contracts 执行失败（契约内联派发将不可用）"
    _MISS=$((_MISS+1))
  fi
  # pre-flight 必须能拦住缺项（故意给空任务，期望 exit 1）
  if (cd "$DST" && "$PY_BIN" runtime/cli.py dispatch --agent qa --check >/dev/null 2>&1); then
    echo "  [WARN] dispatch --check 未拦住缺项（预期 exit 1）"
    _MISS=$((_MISS+1))
  else
    echo "  [ok]   dispatch --check 正确拦下缺项"
  fi
else
  echo "  [SKIP] 未找到 python，跳过 cli.py 检查"
fi

if [[ "$_MISS" -eq 0 ]]; then
  echo "  —— 自检通过：0 项异常 ——"
else
  echo "  —— 自检发现 $_MISS 项异常，请检查上面 [MISS]/[WARN] ——"
fi
