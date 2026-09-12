#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""宿主机能力探测 —— 换宿主 / 升级后先跑这个。

## 为什么需要

v4.1 的教训：当时把上游 ZCode 版协议逐条搬过来，**默认了两个宿主的原生能力相同**，
结果做出一堆重复造轮子的层。v4.2 才补上"先探测宿主有什么"这一步。

换宿主（WorkBuddy → 别的 IDE）或宿主大版本升级后，跑这个脚本重新校准，
把输出贴给主 Agent，就能重新判定「哪些能力该下沉到原生、哪些必须自建」。

## 用法

    python tools/probe-host.py              # 交互式看结论
    python tools/probe-host.py --json       # 机器可读，便于 diff 两次升级的差异

## 看什么

  1. 原生库与表结构 → 决定「存活判据 / 用量账本」能不能读原生
  2. 原生台账目录   → 决定「变更 / 产物 / 审计」要不要自建
  3. 本会话定位     → `session id`、`cwd`、`status`、`model` 是否可得
  4. agent 注入机制 → 宿主会不会把角色定义注入子 agent 的系统提示（本机实测：不会）
"""

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

HOME = Path(os.path.expanduser("~"))


def _try(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def probe_db(path):
    """列出库的库表与行数（只读连接，绝不写）。"""
    p = Path(os.path.expanduser(str(path)))
    if not p.is_file():
        return {"path": str(p), "exists": False}
    out = {"path": str(p), "exists": True, "size": p.stat().st_size, "tables": {}}
    con = None
    try:
        con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True, timeout=3.0)
        c = con.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        for (t,) in c.fetchall():
            try:
                c.execute(f"SELECT COUNT(*) FROM {t}")
                n = c.fetchone()[0]
                c.execute(f"PRAGMA table_info({t})")
                cols = [r[1] for r in c.fetchall()]
                out["tables"][t] = {"rows": n, "columns": cols}
            except Exception as e:
                out["tables"][t] = {"error": str(e)[:80]}
    finally:
        if con is not None:
            con.close()
    return out


def probe_dir(path, sample=6):
    p = Path(os.path.expanduser(str(path)))
    if not p.exists():
        return {"path": str(p), "exists": False}
    try:
        kids = sorted(p.iterdir(), key=lambda x: -x.stat().st_mtime)
    except Exception:
        return {"path": str(p), "exists": True, "error": "unreadable"}
    return {
        "path": str(p),
        "exists": True,
        "entries": len(kids),
        "newest": [
            {"name": k.name, "is_dir": k.is_dir(),
             "size": (k.stat().st_size if k.is_file() else None),
             "age_s": int(time.time() - k.stat().st_mtime)}
            for k in kids[:sample]
        ],
    }


def probe_current_session(db_path, cwd=None):
    """能不能定位到「当前这条会话」—— 决定原生判据可用性。"""
    p = Path(os.path.expanduser(str(db_path)))
    if not p.is_file():
        return None
    want = str(cwd or os.getcwd()).replace("/", "\\").rstrip("\\").lower()
    con = None
    try:
        con = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True, timeout=3.0)
        con.row_factory = sqlite3.Row
        c = con.cursor()
        c.execute("""SELECT id, cwd, status, model, last_activity_at, updated_at
                     FROM sessions WHERE COALESCE(deleted_at,0)=0
                     ORDER BY COALESCE(last_activity_at, updated_at) DESC LIMIT 40""")
        rows = [dict(r) for r in c.fetchall()]
        hit = next((r for r in rows
                    if str(r.get("cwd", "")).replace("/", "\\").rstrip("\\").lower() == want), None)
        s = hit or (rows[0] if rows else None)
        if not s:
            return None
        now = time.time() * 1000
        return {
            "matched_by": "cwd" if hit else "latest",
            "session_id": s.get("id"),
            "status": s.get("status"),
            "model": s.get("model"),
            "cwd": s.get("cwd"),
            "last_activity_s": (int((now - s["last_activity_at"]) / 1000)
                                if s.get("last_activity_at") else None),
        }
    except Exception:
        return None
    finally:
        if con is not None:
            con.close()


def build_report(home=None, cwd=None):
    h = Path(home) if home else HOME / ".workbuddy"
    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cwd": str(cwd or os.getcwd()),
        "dbs": {
            "workbuddy": probe_db(h / "workbuddy.db"),
            "zcode": probe_db(HOME / ".zcode" / "cli" / "db" / "db.sqlite"),
        },
        "ledger_dirs": {
            "changes-index": probe_dir(h / "changes-index"),
            "artifact-index": probe_dir(h / "artifact-index"),
            "audit-log": probe_dir(h / "audit-log"),
            "traces": probe_dir(h / "traces"),
            "tasks": probe_dir(h / "tasks"),
            "teams": probe_dir(h / "teams"),
        },
        "current_session": probe_current_session(h / "workbuddy.db", cwd),
        "agent_registry_dirs": {
            "workspace .workbuddy/agents": probe_dir(Path(cwd or os.getcwd()) / ".workbuddy" / "agents"),
            "builtin plugin agents": probe_dir(
                Path(os.environ.get("WORKBUDDY_APP", r"F:\WorkBuddy\resources\app.asar.unpacked"))
                / "resources" / "plugins" / "workbuddy-builtin" / "builtin-plugins"),
        },
    }


CAPABILITY_VERDICTS = [
    ("存活判据（会话级）", "dbs.workbuddy", "sessions 表存在 → 可读 status/last_activity_at"),
    ("存活判据（per-agent）", "dbs.zcode", "turn_usage 表存在 → 可读回合级状态"),
    ("真实 token 用量", "dbs.workbuddy", "session_usage 表存在 → 可读 used/size"),
    ("变更台账", "ledger_dirs.changes-index", "存在 → 不必自建"),
    ("产物台账", "ledger_dirs.artifact-index", "存在 → 不必自建"),
    ("审计流水", "ledger_dirs.audit-log", "存在 → 不必自建"),
    ("原生任务表", "ledger_dirs.tasks", "存在 → 可双写"),
    ("团队消息", "ledger_dirs.teams", "存在 → 可用原生协作"),
]


def main():
    ap = argparse.ArgumentParser(description="宿主机能力探测（WorkBuddy）")
    ap.add_argument("--json", action="store_true", help="输出 JSON（便于 diff 两次升级）")
    ap.add_argument("--home", default=None, help="覆盖 ~/.workbuddy 位置")
    ap.add_argument("--cwd", default=None, help="按此工作区匹配当前会话")
    a = ap.parse_args()

    rep = build_report(home=a.home, cwd=a.cwd)

    if a.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
        return 0

    print(f"宿主机能力探测 · {rep['generated_at']}")
    print(f"工作区：{rep['cwd']}")
    print("=" * 66)

    print("\n【原生库】")
    for name, d in rep["dbs"].items():
        if not d.get("exists"):
            print(f"  [--] {name:<10} 不存在：{d['path']}")
            continue
        print(f"  [ok] {name:<10} {d['size']} bytes · {len(d['tables'])} 张表")
        for t, info in d["tables"].items():
            if "error" in info:
                print(f"        · {t:<26} 读取失败")
            else:
                print(f"        · {t:<26} rows={info['rows']:<6} cols={len(info['columns'])}")

    print("\n【原生台账目录】")
    for name, d in rep["ledger_dirs"].items():
        if not d.get("exists"):
            print(f"  [--] {name:<16} 不存在")
            continue
        print(f"  [ok] {name:<16} {d['entries']} 项，最新：")
        for e in d["newest"][:2]:
            age = f"{e['age_s']}s 前" if e["age_s"] is not None else ""
            print(f"        · {e['name']:<34} {age}")

    cs = rep["current_session"]
    print("\n【当前会话定位】")
    if cs:
        print(f"  [ok] 命中方式={cs['matched_by']}  id={str(cs['session_id'])[:8]}…")
        print(f"       status={cs['status']}  model={cs['model']}")
        print(f"       最后活动 {cs['last_activity_s']}s 前")
    else:
        print("  [--] 无法定位当前会话（原生判据不可用）")

    print("\n【能力判定】")

    def dig(path):
        cur = rep
        for k in path.split("."):
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur

    for label, path, note in CAPABILITY_VERDICTS:
        node = dig(path)
        ok = bool(node and node.get("exists"))
        if ok and "tables" in node:
            ok = bool(node["tables"])
        print(f"  [{'可用' if ok else '不可用'}] {label:<20} {note}")

    print("\n【agent 注入机制】")
    wa = rep["agent_registry_dirs"]["workspace .workbuddy/agents"]
    print(f"  工作区 .workbuddy/agents：{'存在' if wa.get('exists') else '不存在'}")
    print("  ⚠ 本机实测（2026-09-12）：该目录**不是**应用启动时注册的 agent 来源，")
    print("    会话内写入后立即派发会返回 `not available`。")
    print("    → 角色契约**必须由主 Agent 内联进派发 prompt**，不要指望宿主注入。")
    print("    （若换宿主后此项变化，请重新做一次探针实验：写入 probe-agent.md 后派发它。）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
