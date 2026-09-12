"""多 Agent 运行时数据层（多项目版）。

设计要点：
- 项目之间**完全隔离**：每个项目有自己的 state / bus / tasks / agent 私有记忆
- agent 角色模板在 runtime/registry.json，建项目时复制一份到项目内，
  因此每个项目可以单独覆盖 agent 的模型档位，互不影响
- 消息总线是 append-only jsonl，天然可回放、可审计
- 所有写操作走跨进程文件锁：子 agent 是不同 OS 进程，threading.Lock 管不住
"""
import contextlib
import json
import os
import shutil
import threading
import time
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

try:
    import ctypes
except ImportError:
    ctypes = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

ROOT = Path(__file__).resolve().parent.parent          # runtime/
WS = ROOT.parent                                        # 工作区根
PROJECTS = ROOT / "projects"
TEMPLATE = ROOT / "registry.json"                       # agent 角色模板
INDEX = ROOT / "projects.json"

# ---------- 中断检测参数 ----------
# agent 声称 working，但多久没有任何上报算"静默"（秒）。看板黄色预警。
SILENCE_WARN = 90
# 静默超过这个时长、且**无法确认进程活着** → 判定"中断"。看板红色。
SILENCE_INTERRUPT = 240
#
# ⚠ 为什么不能只用 PID 判死活：子 agent 常见用 `$$` 上报进程号，而 Git Bash 的 `$$`
#   是 MSYS 自己的 PID，并不是 Windows PID（实测 524 / 816 / 569 在进程表里都不存在）。
#   若拿它去 OpenProcess，结果永远是"已死" → 会把活着的 agent 全判成中断。
#   所以规则是：**静默是证据，PID 只用来排除误判**（确认活着就永不判中断）。
#   子 agent 若想被精确识别，应上报真实 OS PID（`python -c "import os;print(os.getpid())"`），
#   并在长命令（>90s）前发一次 heartbeat。

_local = threading.local()
_LOCK_FILE = ROOT / ".lock"

# 本进程（= 看板服务）的启动时刻。
# ★ 为什么需要：服务自己宕机期间，所有 agent 的心跳都打不进来，静默被白白累积。
#   不设宽限的话，服务一重启就会把"其实一直在干活"的 agent 集体误判成中断（实测踩过）。
#   规则：服务刚起来的 SERVER_GRACE 秒内**不做任何中断判定**，等 agent 把心跳补上。
SERVER_START = time.time()
SERVER_GRACE = SILENCE_INTERRUPT


@contextlib.contextmanager
def global_lock():
    """跨进程互斥锁，可重入（update_agent 内部会调 ensure_init）。"""
    depth = getattr(_local, "depth", 0)
    if depth > 0:
        _local.depth = depth + 1
        try:
            yield
        finally:
            _local.depth -= 1
        return

    fd = os.open(str(_LOCK_FILE), os.O_CREAT | os.O_RDWR)
    try:
        if msvcrt:
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX)
        _local.depth = 1
        try:
            yield
        finally:
            _local.depth = 0
    finally:
        try:
            if msvcrt:
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_UN)
        except Exception:
            pass
        os.close(fd)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ts():
    return time.time()


# ---------- 基础读写 ----------

def load_json(path, default=None):
    p = Path(path)
    if not p.exists():
        return default if default is not None else {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}


def save_json(path, data):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)


def append_jsonl(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def read_jsonl(path, limit=None):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out[-limit:] if limit else out


def _next_id(path):
    p = Path(path)
    if not p.exists():
        return 1
    return sum(1 for _ in p.open("r", encoding="utf-8")) + 1


# ---------- 项目 ----------

def projects():
    return load_json(INDEX, {"current": None, "list": []})


def _save_projects(ix):
    save_json(INDEX, ix)


def current_project():
    ix = projects()
    return ix.get("current")


def set_current(pid):
    with global_lock():
        ix = projects()
        if not any(p["id"] == pid for p in ix["list"]):
            return None
        ix["current"] = pid
        _save_projects(ix)
        return pid


def proj_dir(pid=None):
    return PROJECTS / (pid or current_project() or "default")


def bus_dir(pid=None):
    return proj_dir(pid) / "bus"


def agents_dir(pid=None):
    return proj_dir(pid) / "agents"


def list_projects():
    ix = projects()
    out = []
    for p in ix["list"]:
        d = proj_dir(p["id"])
        st = load_json(d / "state.json", {})
        nmsg = sum(1 for _ in (bus_dir(p["id"]) / "messages.jsonl").open("r", encoding="utf-8")) \
            if (bus_dir(p["id"]) / "messages.jsonl").exists() else 0
        active = sum(1 for a in (st.get("agents") or {}).values() if a.get("status") == "working")
        out.append({**p, "phase": st.get("phase", "S0"), "messages": nmsg, "active": active})
    return {"current": ix.get("current"), "list": out}


def create_project(pid, name, brief="", model_overrides=None):
    """新建项目：复制 agent 角色模板，初始化各 agent 的私有记忆。"""
    with global_lock():
        ix = projects()
        if any(p["id"] == pid for p in ix["list"]):
            return {"error": "项目已存在"}
        d = proj_dir(pid)
        (d / "bus").mkdir(parents=True, exist_ok=True)
        (d / "agents").mkdir(parents=True, exist_ok=True)

        reg = load_json(TEMPLATE, {"agents": [], "phases": []})
        reg = json.loads(json.dumps(reg))
        if model_overrides:
            for a in reg.get("agents", []):
                if a["id"] in model_overrides:
                    a["model"] = model_overrides[a["id"]]
        save_json(d / "registry.json", reg)

        st = {"phase": "S0", "updated": now(), "agents": {}}
        for a in reg.get("agents", []):
            st["agents"][a["id"]] = {
                "status": "idle", "pid": None, "model": a["model"],
                "task_id": None, "task_title": "", "step": "", "progress": 0,
                "context_messages": 0, "spawned_at": None, "last_seen": None, "rounds": 0,
            }
            mem = agents_dir(pid) / a["id"] / "memory.md"
            mem.parent.mkdir(parents=True, exist_ok=True)
            mem.write_text(
                f"# {a['name']} · 私有记忆（项目：{name}）\n\n"
                f"> 本文件只有本项目下的 {a['id']} 可读写，其他 agent 与其他项目均不可见。\n"
                f"> 跨任务累积，每次被唤醒时先读这里。\n\n## 长期经验\n\n（尚无）\n\n## 待办与承诺\n\n（尚无）\n",
                encoding="utf-8")
        save_json(d / "state.json", st)
        save_json(d / "tasks.json", {})

        ix["list"].append({"id": pid, "name": name, "brief": brief, "created": now()})
        ix["current"] = pid
        _save_projects(ix)
        return {"id": pid, "name": name}


def delete_project(pid):
    with global_lock():
        ix = projects()
        rest = [p for p in ix["list"] if p["id"] != pid]
        if len(rest) == len(ix["list"]):
            return {"error": "项目不存在"}
        ix["list"] = rest
        if ix.get("current") == pid:
            ix["current"] = rest[0]["id"] if rest else None
        _save_projects(ix)
        d = proj_dir(pid)
        if d.exists():
            shutil.rmtree(d, ignore_errors=True)
        return {"ok": True, "current": ix.get("current")}


def set_agent_model(agent_id, model=None, pid=None, provider=None,
                    model_id=None, params=None):
    """配置某个项目下某个 agent 的模型。

    model      档位（reasoning/default/lite）——当前唯一真正生效的项
    provider   供应商标识，跨 provider 接入后生效
    model_id   具体模型名，如 gpt-4o / claude-sonnet-4-5
    params     temperature / max_tokens 等，预留
    """
    with global_lock():
        pid = pid or current_project()
        rp = proj_dir(pid) / "registry.json"
        reg = load_json(rp, {"agents": []})
        hit = None
        for a in reg.get("agents", []):
            if a["id"] == agent_id:
                hit = a
                break
        if hit is None:
            return {"error": "未知 agent"}
        if model:
            hit["model"] = model
        if provider is not None:
            hit["provider"] = provider
        if model_id is not None:
            hit["model_id"] = model_id
        if params is not None:
            p = dict(hit.get("params") or {})
            p.update(params)
            hit["params"] = p
        save_json(rp, reg)

        sp = proj_dir(pid) / "state.json"
        st = load_json(sp, {"agents": {}})
        ag = st.setdefault("agents", {}).setdefault(agent_id, {})
        applied = False
        if model and ag.get("status") in (None, "idle", "done"):
            ag["model"] = model
            applied = True
        save_json(sp, st)
        return {"ok": True, "agent": agent_id, "model": hit["model"],
                "provider": hit.get("provider"), "model_id": hit.get("model_id"),
                "applied": applied}


# ---------- 项目内数据 ----------

def registry(pid=None):
    return load_json(proj_dir(pid) / "registry.json", load_json(TEMPLATE, {"agents": [], "phases": []}))


def registry_agent_model(agent_id, pid=None):
    for a in registry(pid).get("agents", []):
        if a["id"] == agent_id:
            return a.get("model", "default")
    return "default"


def state(pid=None):
    return load_json(proj_dir(pid) / "state.json", {"phase": "S0", "agents": {}})


def ensure_init(pid=None):
    pid = pid or current_project()
    if not pid:
        return {"phase": "S0", "agents": {}}
    d = proj_dir(pid)
    st = load_json(d / "state.json", None)
    if st and st.get("agents"):
        return st
    reg = registry(pid)
    st = {"phase": "S0", "updated": now(), "agents": {}}
    for a in reg.get("agents", []):
        st["agents"][a["id"]] = {
            "status": "idle", "pid": None, "model": a.get("model", "default"),
            "task_id": None, "task_title": "", "step": "", "progress": 0,
            "context_messages": 0, "spawned_at": None, "last_seen": None, "rounds": 0,
        }
        mem = agents_dir(pid) / a["id"] / "memory.md"
        mem.parent.mkdir(parents=True, exist_ok=True)
        if not mem.exists():
            mem.write_text(f"# {a['name']} · 私有记忆\n\n## 长期经验\n\n（尚无）\n", encoding="utf-8")
    save_json(d / "state.json", st)
    return st


def update_agent(agent_id, proj=None, **kwargs):
    """注意：项目参数叫 proj 而非 pid —— 因为 kwargs 里会有 agent 自己的
    OS 进程号字段 `pid`，同名会导致 Python 报重复参数。"""
    with global_lock():
        pid = proj or current_project()
        st = ensure_init(pid)
        a = st["agents"].setdefault(agent_id, {})
        a.update(kwargs)
        a["last_seen"] = now()
        st["updated"] = now()
        save_json(proj_dir(pid) / "state.json", st)
        return a


def set_phase(phase, pid=None):
    with global_lock():
        pid = pid or current_project()
        st = ensure_init(pid)
        st["phase"] = phase
        st["updated"] = now()
        save_json(proj_dir(pid) / "state.json", st)


def post_message(frm, to, body, msg_type="message", artifact=None, meta=None, pid=None):
    with global_lock():
        pid = pid or current_project()
        # 计量挂载（08 §3）：say 文本入账本。from=user 不计量（用户非 7 角色，01 §3 边界外）。
        # meter 内部全吞异常、无返回值，绝不影响消息主流程（F1④）。
        if frm != "user":
            try:
                meter(frm, body, "say", pid=pid, kind_text="say.body")
            except Exception:
                pass
        path = bus_dir(pid) / "messages.jsonl"
        rec = {"id": _next_id(path), "ts": now(), "epoch": ts(), "from": frm,
               "to": to, "type": msg_type, "body": body,
               "artifact": artifact, "meta": meta or {}}
        append_jsonl(path, rec)
    return rec


def emit(kind, agent_id, text, data=None, pid=None):
    with global_lock():
        pid = pid or current_project()
        path = bus_dir(pid) / "events.jsonl"
        rec = {"id": _next_id(path), "ts": now(), "epoch": ts(), "kind": kind,
               "agent": agent_id, "text": text, "data": data or {}}
        append_jsonl(path, rec)
    return rec


def inbox(agent_id, limit=50, pid=None):
    msgs = read_jsonl(bus_dir(pid) / "messages.jsonl")
    out = [m for m in msgs
           if str(m.get("to", "")) == "*"
           or agent_id in [t.strip() for t in str(m.get("to", "")).split(",")]]
    return out[-limit:]


def upsert_task(task_id, title, agent_id, phase, pid=None, **kwargs):
    with global_lock():
        pid = pid or current_project()
        tp = proj_dir(pid) / "tasks.json"
        tasks = load_json(tp, {})
        t = tasks.get(task_id, {"id": task_id, "title": title, "agent": agent_id,
                                "phase": phase, "status": "pending", "progress": 0,
                                "steps": [], "created": now()})
        t.update(kwargs)
        t["updated"] = now()
        tasks[task_id] = t
        save_json(tp, tasks)
        return t


def get_tasks(pid=None):
    return load_json(proj_dir(pid) / "tasks.json", {})


def memory_path(agent_id, pid=None):
    return agents_dir(pid) / agent_id / "memory.md"


def read_memory(agent_id, pid=None):
    p = memory_path(agent_id, pid)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def append_memory(agent_id, section, text, pid=None):
    # 计量挂载（08 §3）：remember 文本入账本。meter 全吞异常，不影响记忆写入主流程（F1④）。
    try:
        meter(agent_id, text, "remember", pid=pid, kind_text="remember.text")
    except Exception:
        pass
    p = memory_path(agent_id, pid)
    p.parent.mkdir(parents=True, exist_ok=True)
    cur = p.read_text(encoding="utf-8") if p.exists() else f"# {agent_id} 记忆\n"
    block = f"\n- [{now()}] {text}\n"
    if f"## {section}" in cur:
        head, rest = cur.split(f"## {section}", 1)
        idx = rest.find("\n## ")
        if idx == -1:
            cur = head + f"## {section}" + rest.rstrip() + block
        else:
            cur = head + f"## {section}" + rest[:idx].rstrip() + block + rest[idx:]
    else:
        cur = cur.rstrip() + f"\n\n## {section}\n{block}"
    p.write_text(cur, encoding="utf-8")
    return p


# ---------- 中断检测 / 恢复（运行时自愈） ----------
#
# 为什么需要这一层：子 agent 是独立 OS 进程，可能被系统杀掉或自身崩掉。
# 若不检测，看板会一直显示"工作中"，用户以为在跑实际早已死透。
# 检测到中断后，**恢复 = 同一个 agent id 带着它的私有记忆与收件箱续跑**，
# 而不是新开一个 agent 从零开始。

def pid_alive(p):
    """OS 进程是否存活。返回 True/False；拿不到进程号或无法判断时返回 None。"""
    if p in (None, "", 0):
        return None
    try:
        p = int(p)
    except (TypeError, ValueError):
        return None
    if os.name == "nt":
        if ctypes is None:
            return None
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        try:
            k32 = ctypes.windll.kernel32
            h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, p)
        except Exception:
            return None
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            if k32.GetExitCodeProcess(h, ctypes.byref(code)):
                return code.value == STILL_ACTIVE
            return None
        finally:
            try:
                k32.CloseHandle(h)
            except Exception:
                pass
    try:
        os.kill(p, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except Exception:
        return None


def age_seconds(last_seen, since_epoch=None):
    """距 last_seen 的秒数；传 since_epoch 时取二者的较晚者作起点。

    since_epoch 用于把"服务停摆期间"的静默排除掉 —— 那段时间心跳打不进来，不算 agent 的账。
    """
    if not last_seen:
        return None
    try:
        t = datetime.strptime(str(last_seen), "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None
    if since_epoch is not None:
        t = max(t, datetime.fromtimestamp(since_epoch))
    return max(0.0, (datetime.now() - t).total_seconds())


def watchdog(pid=None):
    """扫描 status=working 的 agent，把已死的标成 interrupted。返回本次新判定的列表。

    判定规则（**静默是证据，PID 只用来排除误判**）：
      · 进程确认活着（pid_alive is True）→ 永不判中断，长计算不算死
      · 静默 > SILENCE_INTERRUPT 秒 → 中断
          - 若 PID 明确查无此进程，理由写成"进程已消失且静默 N 秒"（更硬）
          - 若 PID 不可信/未登记，理由写成"静默 N 秒无任何上报"（疑似）
    """
    with global_lock():
        pid = pid or current_project()
        st = ensure_init(pid)
        newly = []
        for aid, a in (st.get("agents") or {}).items():
            if a.get("status") not in ("working", "resuming"):
                continue
            alive = pid_alive(a.get("pid"))
            if alive is True:
                continue                      # 进程还在，绝不打扰
            # ★ 静默只统计"服务确实在运行"的那段时间。
            # 服务停摆期间 agent 的心跳根本打不进来，那段静默是**服务的错，不是 agent 的错**。
            # 老实现只在启动后给 240s 宽限，宽限一过就把宕机期累积的旧静默一次性算总账
            # （实测：刚重启就把一个正在跑 daily.py、1 分钟前还在写文件的 agent 判成中断）。
            # 改成 max(last_seen, 服务启动时间)：重启后每个在跑的 agent 都拿到一个干净的全新窗口。
            age = age_seconds(a.get("last_seen"), since_epoch=SERVER_START)
            if age is None or age <= SILENCE_INTERRUPT:
                continue
            if alive is False and a.get("pid"):
                reason = f"进程 {a.get('pid')} 已消失，且静默 {int(age)} 秒"
            else:
                reason = f"静默 {int(age)} 秒无任何上报"
            a["status"] = "interrupted"
            a["interrupt_reason"] = reason
            a["interrupted_at"] = now()
            a["interrupt_step"] = a.get("step", "")
            a["pid_dead"] = True if alive is False else None
            newly.append({"agent": aid, "reason": reason,
                          "task_id": a.get("task_id"), "step": a.get("step", "")})
        if newly:
            st["updated"] = now()
            save_json(proj_dir(pid) / "state.json", st)
            for n in newly:
                emit("interrupt", n["agent"],
                     f"⚠ 中断：{n['reason']}　（任务 {n['task_id'] or '—'}，停在 {n['step'] or '—'}）",
                     {"reason": n["reason"], "step": n["step"], "task_id": n["task_id"]}, pid=pid)
        return newly


def clear_interrupt(agent_id, note="", by="orchestrator", pid=None):
    """撤销一次中断判定 —— 主 Agent 取证后确认"它其实活着"时使用。

    判据是启发式的，错了必须能改回来，而且**要留痕**：写一条事件说明撤销理由，
    否则看板状态会被人随手翻来翻去，失去可信度。
    """
    with global_lock():
        pid = pid or current_project()
        st = ensure_init(pid)
        a = (st.get("agents") or {}).get(agent_id)
        if not a:
            return {"error": f"未知 agent：{agent_id}"}
        was = a.get("status")
        a["status"] = "working"
        a["interrupt_reason"] = ""
        a["interrupted_at"] = None
        a["pid_dead"] = None
        a["last_seen"] = now()
        st["updated"] = now()
        save_json(proj_dir(pid) / "state.json", st)
        emit("resume", agent_id,
             f"主 Agent 撤销中断判定（原状态 {was}）{('：' + note) if note else ''}",
             {"cleared_by": by, "note": note, "was": was}, pid=pid)
        return {"ok": True, "agent": agent_id, "was": was}


def resume_path(pid=None):
    return bus_dir(pid) / "resume_requests.jsonl"


def request_resume(agent_id, note="", by="user", pid=None):
    """登记一条恢复请求。真正的重新派发由主 Agent 执行（只有它有派发子 agent 的能力）。"""
    with global_lock():
        pid = pid or current_project()
        st = ensure_init(pid)
        a = st["agents"].get(agent_id)
        if a is None:
            return {"error": f"未知 agent：{agent_id}"}
        if a.get("status") not in ("interrupted", "blocked", "failed", "idle", "done"):
            return {"error": f"当前状态 {a.get('status')} 无需恢复"}
        rec = {"id": _next_id(resume_path(pid)), "ts": now(), "epoch": ts(),
               "agent": agent_id, "note": note, "by": by,
               "task_id": a.get("task_id"), "task_title": a.get("task_title", ""),
               "step": a.get("step", ""), "progress": a.get("progress", 0),
               "interrupt_reason": a.get("interrupt_reason", ""),
               "status": "pending"}
        append_jsonl(resume_path(pid), rec)
        a["status"] = "pending_resume"
        a["resume_requested_at"] = now()
        st["updated"] = now()
        save_json(proj_dir(pid) / "state.json", st)
        emit("resume_request", agent_id,
             f"已登记恢复请求（上次停在 {rec['progress']}%：{rec['step'] or '—'}）",
             {"note": note, "by": by, "task_id": rec["task_id"]}, pid=pid)
        return rec


def pending_resumes(pid=None):
    """尚未处理的恢复请求（主 Agent 每次唤醒先看这里）。"""
    pid = pid or current_project()
    return [r for r in read_jsonl(resume_path(pid)) if r.get("status") == "pending"]


def clear_resume(agent_id, pid=None, resolution=""):
    """主 Agent 完成恢复后调用，把该 agent 的待办请求置为已处理。"""
    with global_lock():
        pid = pid or current_project()
        recs = read_jsonl(resume_path(pid))
        changed = False
        for r in recs:
            if r.get("agent") == agent_id and r.get("status") == "pending":
                r["status"] = "done"
                r["resolved_at"] = now()
                r["resolution"] = resolution
                changed = True
        if changed:
            p = resume_path(pid)
            tmp = p.with_suffix(".tmp")
            tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in recs),
                           encoding="utf-8")
            os.replace(tmp, p)
        return {"ok": changed}


def begin_resume(agent_id, new_pid=None, model=None, project=None):
    """主 Agent 重新派发时调用：**同一个 agent id 续跑**，rounds / resume_count 各 +1。
    不新建 agent、不重建记忆、不清空收件箱 —— 这是与"新开一个"的本质区别。"""
    with global_lock():
        pid = project or current_project()
        st = ensure_init(pid)
        a = st["agents"].setdefault(agent_id, {})
        a["status"] = "working"
        a["pid"] = new_pid
        a["rounds"] = int(a.get("rounds") or 0) + 1
        a["resume_count"] = int(a.get("resume_count") or 0) + 1
        a["spawned_at"] = now()
        a["last_seen"] = now()
        a["interrupt_reason"] = ""
        a["pid_dead"] = None
        if model:
            a["model"] = model
        st["updated"] = now()
        save_json(proj_dir(pid) / "state.json", st)
        emit("resume", agent_id,
             f"已**续跑**（第 {a['rounds']} 轮，累计恢复 {a['resume_count']} 次）："
             f"沿用原私有记忆与收件箱，任务 {a.get('task_id') or '—'} 从 {a.get('progress', 0)}% 继续",
             {"rounds": a["rounds"], "resume_count": a["resume_count"]}, pid=pid)
        return a


def post_user_note(body, to="orchestrator", kind="directive", priority="normal", pid=None):
    """网页看板上的留言通道：用户 → 主 Agent（补充内容 / 修正方向），也可直接发给某个子 agent。

    priority='urgent' 表示加急：用户的沟通必须**优先于** agent 之间的机器播报被处理，
    加急留言会排进 pending_notes 队列最前，主 Agent 每次唤醒先读它。
    """
    return post_message("user", to, body, msg_type=kind, pid=pid,
                        meta={"priority": priority, "acked": False})


# ---------- 用户指令的"待处理"队列 ----------
#
# 用户的话不是聊天记录，是待办。发完就沉到消息流底部 = 等于没说。
# 所以留言单独维护一份 ack 台账：没被处理的一直置顶，直到主 Agent 摘掉。

def ack_path(pid=None):
    return proj_dir(pid) / "note_acks.json"


def pending_user_notes(pid=None):
    """未处理的用户留言：加急优先，其次按时间正序（先到的先办）。"""
    pid = pid or current_project()
    acked = set(load_json(ack_path(pid), {"ids": []}).get("ids") or [])
    notes = [m for m in read_jsonl(bus_dir(pid) / "messages.jsonl")
             if m.get("from") == "user" and m.get("id") not in acked]
    urg = [m for m in notes if (m.get("meta") or {}).get("priority") == "urgent"]
    nor = [m for m in notes if (m.get("meta") or {}).get("priority") != "urgent"]
    return urg + nor


def ack_user_note(note_id, by="orchestrator", pid=None):
    """主 Agent 处理完一条用户指令后调用：从待处理队列摘掉。"""
    with global_lock():
        pid = pid or current_project()
        data = load_json(ack_path(pid), {"ids": []})
        ids = data.get("ids") or []
        if note_id in ids:
            return {"ok": True, "already": True}
        ids.append(note_id)
        data["ids"] = ids[-2000:]
        data["updated"] = now()
        save_json(ack_path(pid), data)
        emit("note_ack", by, f"已处理用户指令 #{note_id}", {"note": note_id}, pid=pid)
        return {"ok": True, "id": note_id}


# ---------- 项目整体规划（主 Agent 的"作战地图"） ----------
#
# 主 Agent 是项目负责人，必须能回答"整个项目到哪一步了"。
# 规划落成 plan.json：每个阶段带**权重**与状态，整体进度 = Σ(权重 × 阶段进度) / Σ权重。
# 用权重而不是"完成了几个阶段"，才能反映真实的工程量分布。

def plan_path(pid=None):
    return proj_dir(pid) / "plan.json"


def get_plan(pid=None):
    return load_json(plan_path(pid), {"stages": [], "milestones": []})


def set_plan_stage(stage_id, pid=None, **kw):
    """更新某个阶段的状态/进度/备注。主 Agent 在每个里程碑调用一次。"""
    with global_lock():
        pid = pid or current_project()
        plan = get_plan(pid)
        hit = None
        for s in plan.get("stages", []):
            if s.get("id") == stage_id:
                hit = s
                break
        if hit is None:
            return {"error": f"未知阶段：{stage_id}"}
        hit.update({k: v for k, v in kw.items() if v is not None})
        plan["updated"] = now()
        save_json(plan_path(pid), plan)
        emit("plan", "orchestrator",
             f"规划更新：{stage_id} {hit.get('name','')} → {hit.get('status')} "
             f"{hit.get('progress', 0)}%",
             {"stage": stage_id, "status": hit.get("status"),
              "progress": hit.get("progress"), "overall": overall_progress(plan)}, pid=pid)
        return hit


def set_plan_meta(pid=None, **kw):
    """更新规划的表头：目标 / 阻塞项 / 下一步。整体规划是活的，主 Agent 得能改它。"""
    with global_lock():
        pid = pid or current_project()
        plan = get_plan(pid)
        allowed = ("title", "goal", "blockers", "next", "owner")
        for k in allowed:
            if k in kw and kw[k] is not None:
                plan[k] = kw[k]
        plan["updated"] = now()
        save_json(plan_path(pid), plan)
        emit("plan", "orchestrator", "项目整体规划已更新",
             {"meta": True, "overall": overall_progress(plan)}, pid=pid)
        return plan


def overall_progress(plan):
    """整体进度 = Σ(权重 × 阶段进度) / Σ权重 × 100，四舍五入到整数。"""
    stages = (plan or {}).get("stages") or []
    tw = sum(float(s.get("weight") or 0) for s in stages)
    if tw <= 0:
        return 0
    done = sum(float(s.get("weight") or 0) * float(s.get("progress") or 0) / 100.0
               for s in stages)
    return int(round(done / tw * 100))


# ---------- Token 计量层（09-api-contract v2 §2/§4/§7，08-backend-arch v2 §2~§4） ----------
#
# 公式口径（01 §3 方案 C）：tokens = ceil(ascii_bytes/4 + non_ascii_utf8_bytes/6)
# cost 口径（09 §4）：cost_usd = tokens × calibration × price[model] ÷ 1e6，6 位小数
# F1④：meter 无返回值、内部全吞异常（含留痕也包 try），记账失败只落 meter_error，
#       绝不影响原命令返回 {"ok": true}。允许少记，不允许重复记（append 单次 fsync）。

# 计量对象 7 角色（09 §8 枚举穷举；V-1 修复：剔除历史简称 pm，以契约主键
# product-manager 为准，orchestrator 占位补齐——否则条形图出现恒 0 的 pm 死行）
METER_AGENT_IDS = ("orchestrator", "product-manager", "architect",
                   "frontend-dev", "backend-dev", "dev-lead", "qa")
# V-1 别名归一（19-pm-acceptance）：01 §2 用词 "pm" 与账本主键 "product-manager" 不一致，
# 两条 id 并存会把同一角色的记账分裂成两行。读写双侧统一归一，历史 pm 记账自动并入。
AGENT_ALIAS = {"pm": "product-manager"}
# 单价表缺省值（USD / 1e6 tokens）。表不存在时以此自动创建，版本号入账（09 §4）。
DEFAULT_PRICES = {"default": 3.0, "lite": 1.0, "reasoning": 15.0}
PRICE_TABLE_VERSION = "v1"


def price_table_path():
    return PROJECTS / "price-table.json"


def _price_table():
    """读单价表；不存在或损坏则以默认表创建（只兜底创建，不做人工修正通道）。"""
    p = price_table_path()
    t = load_json(p, None)
    if isinstance(t, dict) and t.get("version") and isinstance(t.get("prices"), dict):
        return t
    t = {"version": PRICE_TABLE_VERSION, "calibration": 1.0,
         "prices": dict(DEFAULT_PRICES), "created": now()}
    try:
        save_json(p, t)
    except Exception:
        pass
    return t


def ledger_path(pid=None):
    return proj_dir(pid) / "ledger.jsonl"


def append_ledger(rec, pid=None):
    """追加一行账本。seq 项目内自增；global_lock 可重入，post 层内调用安全。"""
    with global_lock():
        p = ledger_path(pid)
        out = {"seq": _next_id(p)}
        out.update(rec)
        append_jsonl(p, out)
    return out


def _calc_tokens(ascii_bytes, non_ascii_bytes):
    """ceil(ascii/4 + non_ascii/6)，纯整数运算避免浮点误差。
    通分到 12：3a/12 + 2n/12 → ceil((3a+2n)/12) = (3a+2n+11)//12。"""
    return (ascii_bytes * 3 + non_ascii_bytes * 2 + 11) // 12


def _calc_cost(tokens, calibration, price):
    """tokens × calibration × price ÷ 1e6，Decimal 计算后 6 位小数（金额不用裸浮点）。"""
    c = (Decimal(int(tokens)) * Decimal(str(calibration)) * Decimal(str(price))
         / Decimal(1000000))
    return float(c.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def meter(agent_id, text, kind, pid=None, kind_text=None):
    """计量入口（08 §4 伪代码的实现规范）。无返回值、永无异常上抛。

    kind 枚举（09 §4，7 值穷举）：say progress remember finish spawn_title
    resume_title meter_error。text 为空仍落 tokens=0 的行（边界/轮次起点语义）。
    """
    try:
        text = "" if text is None else str(text)
        agent_id = AGENT_ALIAS.get(agent_id, agent_id)   # V-1：别名归一防记账分裂
        if kind_text is None:
            kind_text = kind
        raw = text.encode("utf-8")
        ascii_bytes = sum(1 for b in raw if b < 0x80)
        non_ascii_bytes = len(raw) - ascii_bytes
        tokens = _calc_tokens(ascii_bytes, non_ascii_bytes)
        st = state(pid)
        model = ((st.get("agents") or {}).get(agent_id) or {}).get("model", "default")
        tbl = _price_table()
        calibration = float(tbl.get("calibration", 1.0) or 1.0)
        price = (tbl.get("prices") or {}).get(model)
        unpriced = price is None
        cost = 0.0 if unpriced else _calc_cost(tokens, calibration, price)
        append_ledger({"ts": now(), "epoch": ts(), "agent": agent_id, "kind": kind,
                       "kind_text": kind_text, "ascii_bytes": ascii_bytes,
                       "non_ascii_bytes": non_ascii_bytes, "tokens": tokens,
                       "model": model, "price_version": tbl.get("version", ""),
                       "calibration": calibration, "cost_usd": cost,
                       "unpriced": unpriced}, pid=pid)
    except Exception as e:                     # F1④：留痕也包 try，绝不外抛
        try:
            append_ledger({"ts": now(), "epoch": ts(), "agent": agent_id,
                           "kind": "meter_error", "kind_text": f"计量失败：{e}",
                           "ascii_bytes": 0, "non_ascii_bytes": 0, "tokens": 0,
                           "model": "default", "price_version": "", "calibration": 1.0,
                           "cost_usd": 0.0, "unpriced": False}, pid=pid)
        except Exception:
            try:
                emit("meter_error", agent_id, f"计量失败：{e}", pid=pid)
            except Exception:
                pass                            # 静默放弃，绝不影响主流程


def _read_ledger(pid=None):
    """读全部账本行。文件缺失 → []；读失败向上抛（供 tokens_error 区分零记账与故障）。"""
    p = ledger_path(pid)
    if not p.exists():
        return []
    rows = []
    for ln in p.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            rows.append(json.loads(ln))
        except Exception:
            continue
    return rows


def token_summary(pid=None):
    """快照 tokens 汇总（09 §2 口径 v2）。

    账本为空/不存在 → None（零记账空态，区别于读取失败）；
    读取失败向上抛异常，由调用方转 tokens_error。
    round 边界 = 该 agent 最近一条 spawn_title 或 resume_title 之后之和（R-2）。
    """
    with global_lock():
        rows = _read_ledger(pid)
    if not rows:
        return None
    tbl = _price_table()
    calibration = float(tbl.get("calibration", 1.0) or 1.0)
    st = state(pid)
    # 7 角色先占位（穷举），账本里出现的其他 id 动态补入，避免丢数据
    agents = {a: {"round_tokens": 0, "total_tokens": 0, "cost_usd": 0.0,
                  "unpriced": False} for a in METER_AGENT_IDS}
    # 两遍法：先扫出每个 agent 最后一条轮次边界（spawn_title/resume_title）的位置，
    # 再累加 —— 单遍累加无法撤销更早轮次已计入的部分（R-2）
    round_start = {}
    for i, r in enumerate(rows):
        if r.get("kind") in ("spawn_title", "resume_title"):
            round_start[r.get("agent")] = i + 1
    for i, r in enumerate(rows):
        a = AGENT_ALIAS.get(r.get("agent"), r.get("agent"))   # V-1：历史 pm 行并入 product-manager
        g = agents.setdefault(a, {"round_tokens": 0, "total_tokens": 0,
                                  "cost_usd": 0.0, "unpriced": False})
        g["total_tokens"] += int(r.get("tokens") or 0)
        if i >= round_start.get(a, 0):
            g["round_tokens"] += int(r.get("tokens") or 0)
    total_tokens = 0
    total_cost = Decimal("0")
    has_unpriced = False
    for a, g in agents.items():
        total_tokens += g["total_tokens"]
        model = ((st.get("agents") or {}).get(a) or {}).get("model", "default")
        price = (tbl.get("prices") or {}).get(model)
        g["unpriced"] = price is None
        if g["unpriced"]:
            has_unpriced = True
            g["cost_usd"] = 0.0
        else:
            g["cost_usd"] = _calc_cost(g["total_tokens"], calibration, price)
            total_cost += Decimal(str(g["cost_usd"]))
    return {"calibration": calibration, "price_version": tbl.get("version", ""),
            "total_tokens": total_tokens,
            "total_cost_usd": float(total_cost.quantize(Decimal("0.000001"),
                                                        rounding=ROUND_HALF_UP)),
            "has_unpriced": has_unpriced, "agents": agents}


def export_tokens(path=None, pid=None):
    """导出账本（09 §7）。只读动作：任何失败不得改动 ledger.jsonl。"""
    try:
        with global_lock():
            pid = pid or current_project()
            tbl = _price_table()
            meta = {"price_version": tbl.get("version", ""),
                    "calibration": float(tbl.get("calibration", 1.0) or 1.0),
                    "exported_at": now()}
            rows = _read_ledger(pid)
            summ = token_summary(pid)
        summary = []
        if summ:
            for a, g in summ["agents"].items():
                summary.append({"agent": a, "round_tokens": g["round_tokens"],
                                "total_tokens": g["total_tokens"],
                                "cost_usd": g["cost_usd"], "unpriced": g["unpriced"]})
        data = {"meta": meta, "summary": summary, "details": rows}
        target = Path(path) if path else (proj_dir(pid) / "token-export.json")
        if not target.is_absolute():
            target = WS / target
        rp = target.resolve()
        if not str(rp).startswith(str(WS)):     # 越界拒绝写
            return {"error": "target not writable"}
        rp.parent.mkdir(parents=True, exist_ok=True)
        tmp = rp.with_suffix(rp.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, rp)
        rel = str(rp.relative_to(WS)).replace("\\", "/")
        return {"ok": True, "path": rel, "records": len(rows)}
    except Exception:
        return {"error": "target not writable"}


def append_artifact(agent_id, path, summary, pid=None):
    """finish 工件登记（09 §6）：有 task_id 时追加进 tasks[task_id].artifacts。

    无 task_id / 任务不存在 → 返回 None（消息流兜底展示位由调用方 post_message 承担）。
    """
    with global_lock():
        pid = pid or current_project()
        st = ensure_init(pid)
        task_id = ((st.get("agents") or {}).get(agent_id) or {}).get("task_id")
        if not task_id:
            return None
        tp = proj_dir(pid) / "tasks.json"
        tasks = load_json(tp, {})
        t = tasks.get(task_id)
        if t is None:
            return None
        t.setdefault("artifacts", []).append(
            {"path": str(path).replace("\\", "/"), "summary": summary or "",
             "ts": now()})
        t["updated"] = now()
        save_json(tp, tasks)
        return task_id


# ---------- 聚合视图 ----------

def snapshot(pid=None, msg_limit=200, event_limit=120):
    pid = pid or current_project()
    # 每次拉快照前先体检：把已死的 agent 标成"中断"，看板才不会一直假显示"工作中"
    try:
        watchdog(pid)
    except Exception:
        pass
    reg = registry(pid)
    st = ensure_init(pid)
    agents = []
    for a in reg.get("agents", []):
        rt = st["agents"].get(a["id"], {})
        mem_txt = read_memory(a["id"], pid)
        silence = age_seconds(rt.get("last_seen"))
        alive = pid_alive(rt.get("pid")) if rt.get("pid") else None
        agents.append({
            **a,
            "provider": a.get("provider", "workbuddy"),
            "model_id": a.get("model_id", ""),
            "params": a.get("params") or {},
            "status": rt.get("status", "idle"),
            "pid": rt.get("pid"),
            "pid_alive": alive,
            "runtime_model": rt.get("model", a.get("model", "default")),
            "task_id": rt.get("task_id"),
            "task_title": rt.get("task_title", ""),
            "step": rt.get("step", ""),
            "progress": rt.get("progress", 0),
            "context_messages": rt.get("context_messages", 0),
            "spawned_at": rt.get("spawned_at"),
            "last_seen": rt.get("last_seen"),
            "silence_seconds": int(silence) if silence is not None else None,
            "interrupt_reason": rt.get("interrupt_reason", ""),
            "interrupted_at": rt.get("interrupted_at"),
            "resume_count": rt.get("resume_count", 0),
            "resume_requested_at": rt.get("resume_requested_at"),
            "rounds": rt.get("rounds", 0),
            "memory_bytes": len(mem_txt.encode("utf-8")),
            "memory_path": str(memory_path(a["id"], pid).relative_to(WS)).replace("\\", "/"),
        })
    # 当前任务：进行中的优先，否则取最近更新的那条 —— 主 Agent 卡片要能回答"现在在跑什么"
    _tasks = get_tasks(pid)
    _working = [t for t in _tasks.values() if t.get("status") == "working"]
    _pool = _working or list(_tasks.values())
    current_task = max(_pool, key=lambda t: t.get("updated") or "") if _pool else None
    pend_notes = pending_user_notes(pid)

    return {
        "project": pid,
        "phase": st.get("phase", "S0"),
        "updated": st.get("updated"),
        "server_time": now(),
        "phases": reg.get("phases", []),
        "model_tiers": reg.get("model_tiers", {}),
        # 老项目的 registry 复制自旧模板，可能没有这些字段，回退到全局模板
        "providers": reg.get("providers") or load_json(TEMPLATE, {}).get("providers", {}),
        "available_models": (reg.get("available_models")
                             or load_json(TEMPLATE, {}).get("available_models", [])),
        "agents": agents,
        "messages": read_jsonl(bus_dir(pid) / "messages.jsonl", limit=msg_limit),
        "events": read_jsonl(bus_dir(pid) / "events.jsonl", limit=event_limit),
        "tasks": get_tasks(pid),
        "projects": list_projects(),
        "silence_warn": SILENCE_WARN,
        "silence_interrupt": SILENCE_INTERRUPT,
        "resume_requests": pending_resumes(pid),
        "plan": {**get_plan(pid), "overall": overall_progress(get_plan(pid))},
        "current_task": current_task,
        "orchestrator_inbox": inbox("orchestrator", 30, pid),
        "user_notes": [m for m in read_jsonl(bus_dir(pid) / "messages.jsonl")
                       if m.get("from") == "user"][-30:],
        # 待处理的用户指令：加急在前。主 Agent 唤醒第一件事就是清这个队列。
        "pending_notes": pend_notes,
        "pending_urgent": len([m for m in pend_notes
                               if (m.get("meta") or {}).get("priority") == "urgent"]),
    }
