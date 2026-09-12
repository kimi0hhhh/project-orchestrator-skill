"""把 `.zcode/state/board.md` 从运行时真值重新生成。

## 为什么需要它
board.md 是主 Agent 每次唤醒**第 2 步就要读**的文件。但它一直是手写的，
于是必然与 gate-log / plan.json / state.json 漂移 —— 实测踩过：gate-log 里
已经有两条 PASS 记录、open-issues 里有 7 条未决项，board.md 却整页「⬜ 待办」。
主 Agent 据此汇报，会给出完全错误的项目状态。

改成**派生文件**：board.md 由本脚本生成，头部写明「自动生成，勿手改」。
真相源是 runtime 的项目状态（plan.json / state.json）与 gate-log.md。

## 用法
    python runtime/board_sync.py                # 写回 state 目录下的 board.md
    python runtime/board_sync.py --dry-run      # 只打印，不落盘
    python runtime/board_sync.py --state-dir .zcode/state
    python runtime/board_sync.py --project board-ui
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent            # runtime/
WS = ROOT.parent                                   # 工作区根
PROJECTS = ROOT / "projects"
INDEX = ROOT / "projects.json"

STATE_DIR_CANDIDATES = (".zcode/state",)

STATUS_ICON = {
    "done": "✅", "approved": "✅", "pass": "✅",
    "working": "🔵", "doing": "🔵", "in_progress": "🔵",
    "blocked": "⛔", "concern": "⚠️",
    "fail": "❌", "rejected": "❌", "pending": "⬜", "todo": "⬜",
}
ICON_LEGEND = "⬜ 待办 · 🔵 进行中 · ✅ 通过门禁 · ⚠️ CONCERN 有条件放行 · ❌ 退回重做 · ⛔ 阻塞"


def pick_state_dir(explicit=None):
    if explicit:
        p = Path(explicit)
        return p if p.is_absolute() else WS / p
    for rel in STATE_DIR_CANDIDATES:
        p = WS / rel
        if p.is_dir():
            return p
    return WS / STATE_DIR_CANDIDATES[0]


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def current_project(explicit=None):
    if explicit:
        return explicit
    ix = read_json(INDEX, {}) or {}
    return ix.get("current")


def load_plan(pid):
    if not pid:
        return {}
    return read_json(PROJECTS / pid / "plan.json", {}) or {}


def load_state(pid):
    if not pid:
        return {}
    return read_json(PROJECTS / pid / "state.json", {}) or {}


def count_gates(state_dir):
    """从 gate-log.md 数 PASS / CONCERN / FAIL 条数。

    行格式：`2026-09-11 10:52 | G-PM-02 | 02-prd v1 | CONCERN | 理由`
    跳过示例行与表头；只认含 `|` 且第 4 段是三分档之一的行。
    """
    f = state_dir / "gate-log.md"
    counts = {"PASS": 0, "CONCERN": 0, "FAIL": 0}
    rows = []
    if not f.exists():
        return counts, rows
    for ln in f.read_text(encoding="utf-8").splitlines():
        if "|" not in ln:
            continue
        cells = [c.strip() for c in ln.split("|")]
        if len(cells) < 4:
            continue
        verdict = cells[3].upper()
        if verdict not in counts:
            continue
        if "示例" in ln or "Example" in ln:
            continue
        counts[verdict] += 1
        rows.append((cells[0], cells[1], cells[2], verdict, cells[4] if len(cells) > 4 else ""))
    return counts, rows


def count_open_issues(state_dir):
    f = state_dir / "open-issues.md"
    if not f.exists():
        return 0
    txt = f.read_text(encoding="utf-8")
    return len(re.findall(r"^#{2,4}\s*ISSUE-", txt, flags=re.MULTILINE))


def agent_lines(state, plan):
    """把在跑的 agent 与阶段绑起来，给出一句话状态。"""
    out = []
    agents = (state.get("agents") or {})
    for aid, a in agents.items():
        if aid == "orchestrator":
            continue
        st = a.get("status") or "idle"
        if st in ("idle", "done") and not a.get("task_id"):
            continue
        step = a.get("step") or ""
        pct = a.get("progress", 0)
        out.append(f"| {aid} | {STATUS_ICON.get(st, '⬜')} {st} | {pct}% | {step} |")
    return out


def build_board(pid, plan, state, state_dir):
    counts, gate_rows = count_gates(state_dir)
    issues = count_open_issues(state_dir)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    L = []
    L.append("# 进度看板")
    L.append("")
    L.append("> ⚠️ **本文件由 `python runtime/board_sync.py` 自动生成，请勿手改**——手改必与")
    L.append("> 运行时漂移。真相源：`runtime/projects/<pid>/plan.json`（阶段）、`state.json`（agent）、")
    L.append("> `gate-log.md`（门禁）。要改进度就改这些源，然后重跑本脚本。")
    L.append(f">")
    L.append(f"> 生成时间：{now}　项目：`{pid or '—'}`")
    L.append("")
    L.append("## 阶段")
    L.append("")
    L.append("| 阶段 | 负责 Agent | 状态 | 进度 | 产出 / 备注 |")
    L.append("|---|---|---|---|---|")
    stages = plan.get("stages") or []
    if stages:
        for s in stages:
            st = str(s.get("status") or "pending")
            icon = STATUS_ICON.get(st, "⬜")
            note = s.get("note") or ""
            L.append(f"| {s.get('id','')} {s.get('name','')} | {s.get('owner','')} | "
                     f"{icon} {st} | {s.get('progress', 0)}% | {note} |")
    else:
        L.append("| — | — | ⬜ 尚无规划 | 0% | 主 Agent 用 `cli.py plan --stage ...` 建立 |")
    L.append("")
    if plan.get("goal"):
        L.append(f"**本期目标**：{plan['goal']}")
        L.append("")
    if plan.get("blockers"):
        L.append(f"**当前阻塞**：{plan['blockers']}")
        L.append("")
    if plan.get("next"):
        L.append(f"**下一步**：{plan['next']}")
        L.append("")

    L.append("## 在跑的 Agent")
    L.append("")
    rows = agent_lines(state, plan)
    if rows:
        L.append("| Agent | 状态 | 进度 | 当前步骤 |")
        L.append("|---|---|---|---|")
        L.extend(rows)
    else:
        L.append("（当前没有在跑的 Agent）")
    L.append("")

    L.append("## 门禁与未决项")
    L.append("")
    L.append(f"- 门禁记录：**PASS {counts['PASS']}** · CONCERN {counts['CONCERN']} · FAIL {counts['FAIL']}"
             f"（详见 `.zcode/state/gate-log.md`）")
    L.append(f"- 未决项：**{issues}** 条（详见 `.zcode/state/open-issues.md`）")
    L.append("")
    if gate_rows:
        L.append("最近门禁：")
        L.append("")
        L.append("| 时间 | 门禁 | 工件 | 判定 |")
        L.append("|---|---|---|---|")
        for r in gate_rows[-8:]:
            L.append(f"| {r[0]} | {r[1]} | {r[2]} | {STATUS_ICON.get(r[3],'')} {r[3]} |")
        L.append("")

    L.append("状态图例：" + ICON_LEGEND)
    L.append("")
    L.append("## 返工计数")
    L.append("")
    L.append("| 模块 | 累计返工轮次 | 上限 | 备注 |")
    L.append("|---|---|---|---|")
    L.append("| — | 0 | 3（超限主 Agent 裁定重写或砍需求） | |")
    L.append("")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(prog="board-sync")
    ap.add_argument("--project", default=None, help="项目 id，缺省取 projects.json 的 current")
    ap.add_argument("--state-dir", dest="state_dir", default=None,
                    help="状态目录（默认 .zcode/state）")
    ap.add_argument("--dry-run", action="store_true", help="只打印，不写文件")
    a = ap.parse_args()

    state_dir = pick_state_dir(a.state_dir)
    pid = current_project(a.project)
    plan = load_plan(pid)
    state = load_state(pid)
    txt = build_board(pid, plan, state, state_dir)

    if a.dry_run:
        print(txt)
        return 0

    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "board.md").write_text(txt, encoding="utf-8")
    print(f"已重建 {state_dir / 'board.md'}（项目 {pid or '—'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
