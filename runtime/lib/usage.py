"""真实用量适配层：把「客户端记录的真实 token / 成本」抽象成一个可切换的后端。

## 为什么要这层
原实现把「真实计量」直接写死成读 ZCode 的 `db.sqlite`。换到 OpenCode 后那条路
不存在，会静默返回 None，看板就退回**按上报文本字节估算**的口径 —— 而那个口径实测
差 5 个数量级（1,494 vs 249,529,354），等于没有。

本模块把两个客户端统一成同一份返回结构，上层（store.token_summary）不再关心用哪个。

## 后端
- `zcode`    ：`~/.zcode/cli/db/db.sqlite` 的 `turn_usage`（按回合）
- `opencode` ：`~/.local/share/opencode/opencode.db` 的 `session`（按会话，自带 cost）
- `none`     ：都不在 → 上层只给估算值并明确标注不可信

## 选择顺序
`ORCH_USAGE_BACKEND` 环境变量强制指定（`auto`/`zcode`/`opencode`/`none`），
缺省 auto：两个库都在时**优先读会话里已登记的那个**，都没登记才按 zcode → opencode 顺序。

## 返回结构（两个后端一致，看板直接消费）
    {
      "session_id": str,        # 去重键
      "backend": "zcode|opencode",
      "turns", "requests", "tool_calls", "duration_ms": int,
      "input", "output", "reasoning", "cache_read", "cache_write": int,
      "total": int,             # input + output
      "model": str,
      "cost_usd": float | None, # 客户端自带成本（OpenCode 有，ZCode 无）
      "last_turn": dict | None,
    }
"""
import json
import os
import sqlite3
from pathlib import Path

ZC_DB = Path(os.path.expanduser(os.environ.get("ZCODE_DB", "~/.zcode/cli/db/db.sqlite")))
OC_DB = Path(os.path.expanduser(
    os.environ.get("OPENCODE_DB", "~/.local/share/opencode/opencode.db")))
# OpenCode 的数据目录在 Windows 上也可能落在 XDG 位置；都给上，取第一个存在的。
OC_DB_FALLBACKS = [
    Path(os.path.expanduser("~/.local/share/opencode/opencode.db")),
    Path(os.path.expanduser("~/AppData/Local/opencode/opencode.db")),
    Path(os.path.expanduser("~/.cache/opencode/opencode.db")),
]


def _norm(p):
    """路径归一：大小写、斜杠方向、尾斜杠都抹平，便于与客户端存的 directory 比较。"""
    try:
        return os.path.normcase(os.path.normpath(str(p))).replace("\\", "/").rstrip("/")
    except Exception:
        return str(p or "").replace("\\", "/").rstrip("/")


def _oc_db_path():
    env = os.environ.get("OPENCODE_DB")
    if env:
        return Path(os.path.expanduser(env))
    for p in [OC_DB] + OC_DB_FALLBACKS:
        if p.exists():
            return p
    return OC_DB


def _ro_con(path):
    """只读打开。文件不存在/被锁/结构不符 → None（调用方回退，绝不抛）。"""
    try:
        if not path or not Path(path).exists():
            return None
        return sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True, timeout=2)
    except Exception:
        return None


def backend(force=None):
    """当前用哪个后端。"""
    b = (force or os.environ.get("ORCH_USAGE_BACKEND") or "auto").strip().lower()
    if b in ("zcode", "opencode", "none"):
        return b
    if ZC_DB.exists():                       # auto
        return "zcode"
    if _oc_db_path().exists():
        return "opencode"
    return "none"


def available(force=None):
    b = backend(force)
    if b == "zcode":
        return ZC_DB.exists()
    if b == "opencode":
        return _oc_db_path().exists()
    return False


# ---------------- ZCode：turn_usage（按回合） ----------------

_ZC_FIELDS = ("input_tokens", "output_tokens", "reasoning_tokens",
              "cache_read_input_tokens", "cache_creation_input_tokens")


def _zcode_sessions(session_ids):
    con = _ro_con(ZC_DB)
    if con is None:
        return []
    out = []
    try:
        c = con.cursor()
        for sid in session_ids:
            sid = f"sess_subagent_{sid}" if str(sid).startswith("agent_") else sid
            r = c.execute(
                f"""SELECT COUNT(*), SUM(model_request_count), SUM(tool_call_count), SUM(duration_ms),
                           {', '.join('SUM(' + f + ')' for f in _ZC_FIELDS)}
                    FROM turn_usage WHERE session_id=?""", (sid,)).fetchone()
            if not r or not r[0]:
                continue
            v = [int(x or 0) for x in r[4:]]
            tk = {"session_id": sid, "backend": "zcode", "turns": int(r[0]),
                  "requests": int(r[1] or 0), "tool_calls": int(r[2] or 0),
                  "duration_ms": int(r[3] or 0), "input": v[0], "output": v[1],
                  "reasoning": v[2], "cache_read": v[3], "cache_write": v[4],
                  "cost_usd": None, "last_turn": None, "model": ""}
            tk["total"] = tk["input"] + tk["output"]
            r2 = c.execute(
                f"""SELECT model_request_count, tool_call_count, duration_ms,
                           {', '.join(_ZC_FIELDS)}
                    FROM turn_usage WHERE session_id=? ORDER BY started_at DESC LIMIT 1""",
                (sid,)).fetchone()
            if r2:
                w = [int(x or 0) for x in r2[3:]]
                tk["last_turn"] = {"requests": int(r2[0] or 0), "tool_calls": int(r2[1] or 0),
                                   "duration_ms": int(r2[2] or 0), "input": w[0], "output": w[1],
                                   "reasoning": w[2], "cache_read": w[3], "cache_write": w[4],
                                   "total": w[0] + w[1]}
            r3 = c.execute("""SELECT model_id FROM model_usage WHERE session_id=?
                              GROUP BY model_id ORDER BY COUNT(*) DESC LIMIT 1""",
                           (sid,)).fetchone()
            tk["model"] = r3[0] if r3 else ""
            out.append(tk)
    except Exception:
        return []
    finally:
        try:
            con.close()
        except Exception:
            pass
    return out


# ---------------- OpenCode：session（按会话，自带 cost） ----------------

def _oc_model(raw):
    """model 列是 JSON 字符串：{"id":"glm-4.7","providerID":"z-ai","variant":"high"}。"""
    try:
        d = json.loads(raw) if isinstance(raw, str) else (raw or {})
        mid = d.get("id") or ""
        pid = d.get("providerID") or ""
        return f"{pid}/{mid}" if pid and mid else (mid or "")
    except Exception:
        return ""


def _opencode_sessions(agent_id=None, workspace=None, session_id=None):
    con = _ro_con(_oc_db_path())
    if con is None:
        return []
    rows = []
    try:
        c = con.cursor()
        sql = ("SELECT id, parent_id, agent, model, directory, cost, "
               "tokens_input, tokens_output, tokens_reasoning, "
               "tokens_cache_read, tokens_cache_write, time_created "
               "FROM session")
        where, args = [], []
        if session_id:
            where.append("id = ?"); args.append(session_id)
        if workspace:
            # directory 在库里可能是 Windows 或 MSYS 风格，SQL 里没法归一，取回来再比。
            pass
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY time_created"
        for r in c.execute(sql, args):
            (sid, parent, agent, model, directory, cost, ti, to, tr, tcr, tcw, tcr_ts) = r
            if workspace and _norm(directory) != _norm(workspace):
                continue
            # 角色匹配：优先 agent 列 == 角色 id；未指定角色则全收
            if agent_id and not session_id:
                if (agent or "") != agent_id and not (parent and agent_id in str(parent)):
                    continue
            ti, to = int(ti or 0), int(to or 0)
            rows.append({
                "session_id": sid, "backend": "opencode",
                "turns": 0, "requests": 0, "tool_calls": 0, "duration_ms": 0,
                "input": ti, "output": to,
                "reasoning": int(tr or 0),
                "cache_read": int(tcr or 0), "cache_write": int(tcw or 0),
                "total": ti + to,
                "model": _oc_model(model),
                "cost_usd": (float(cost) if cost not in (None, "") else None),
                "last_turn": None,
                "agent": agent or "", "directory": directory or "",
            })
    except Exception:
        return []
    finally:
        try:
            con.close()
        except Exception:
            pass
    return rows


# ---------------- 统一入口 ----------------

def sessions(agent_id=None, workspace=None, zcode_agent=None, force=None):
    """取某角色的真实用量会话列表（可能多条：一个角色跑过多次会话）。

    zcode_agent：会话内显式登记的会话 id（ZCode 是 `sess_subagent_xxx`/`agent_xxx`，
                 OpenCode 是 `ses_xxx`）——登记了就按它精确取，不再靠名字猜。

    ★ auto 模式按「谁真有数据」回退，而不是「哪个库存在」：
      本机可能同时装着两个客户端（实测就是），只看存在性会在 OpenCode 项目里
      错选 ZCode 源、拿到空数据，看板又退回那个差 5 个数量级的估算值。
    """
    explicit = (force or os.environ.get("ORCH_USAGE_BACKEND") or "auto").strip().lower()
    if explicit in ("zcode", "opencode", "none"):
        return [] if explicit == "none" else _sessions_one(explicit, agent_id, workspace, zcode_agent)
    order = ["zcode", "opencode"] if ZC_DB.exists() else ["opencode", "zcode"]
    for b in order:
        rows = _sessions_one(b, agent_id, workspace, zcode_agent)
        if rows:
            return rows
    return []


def _sessions_one(b, agent_id, workspace, zcode_agent):
    if b == "zcode":
        if not zcode_agent:
            return []
        return _zcode_sessions([zcode_agent])
    if b == "opencode":
        return _opencode_sessions(agent_id=agent_id, workspace=workspace,
                                  session_id=zcode_agent if zcode_agent else None)
    return []


def workspace_totals(workspace, force=None):
    """整个工作区的真实汇总（不区分角色）——看板兜底与自检用。"""
    b = backend(force)
    if b == "opencode":
        rows = _opencode_sessions(workspace=workspace, session_id=None)
    else:
        rows = _zcode_sessions([])          # zcode 无法按目录反查，故空
    tok = sum(int(r.get("total") or 0) for r in rows)
    cost = 0.0
    has_cost = False
    for r in rows:
        if r.get("cost_usd") is not None:
            cost += float(r["cost_usd"]); has_cost = True
    return {"backend": b, "sessions": len(rows), "tokens": tok,
            "cost_usd": cost if has_cost else None}


if __name__ == "__main__":                  # 自检：python runtime/lib/usage.py
    import sys
    ws = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[2])
    print("backend   =", backend())
    print("zcode db  =", ZC_DB, ZC_DB.exists())
    print("opencode  =", _oc_db_path(), _oc_db_path().exists())
    print("workspace =", ws)
    print("totals    =", workspace_totals(ws))
