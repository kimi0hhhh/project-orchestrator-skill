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
import sqlite3
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
    txt = json.dumps(data, ensure_ascii=False, indent=2)
    tmp = p.with_suffix(p.suffix + ".tmp")
    last_err = None
    # 首选原子替换；Windows 下目标被并发读者（1.2s 轮询的 UI、另一会话）占用时
    # os.replace 抛 WinError 5，退避重试后仍失败则**回退原地写入**——
    # Python 读方以共享模式打开，开写句柄不被阻塞，故原地写总能落地。
    try:
        tmp.write_text(txt, encoding="utf-8")
        for i in range(3):
            try:
                os.replace(tmp, p)
                return
            except PermissionError as e:
                last_err = e
                import time as _t
                _t.sleep(0.15 * (i + 1))
        try:
            tmp.unlink()
        except Exception:
            pass
    except Exception:
        pass
    for i in range(3):
        try:
            with p.open("w", encoding="utf-8") as f:
                f.write(txt)
                f.flush()
                os.fsync(f.fileno())
            return
        except PermissionError as e:
            last_err = e
            import time as _t
            _t.sleep(0.2 * (i + 1))
    if last_err:
        raise last_err


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
        nev = sum(1 for _ in (bus_dir(p["id"]) / "events.jsonl").open("r", encoding="utf-8")) \
            if (bus_dir(p["id"]) / "events.jsonl").exists() else 0
        active = sum(1 for a in (st.get("agents") or {}).values() if a.get("status") == "working")
        out.append({**p, "phase": st.get("phase", "S0"), "messages": nmsg,
                    "events": nev, "active": active})
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

        # 规划表初始布点：按 registry phases 建满整条流水线（全部 pending，等权 10）。
        # 不这么做的话，plan.json 的 stages 起初为空 → 作战地图一片空白，
        # 且 `cli.py plan --stage S1` 会报「未知阶段」，主 Agent 无从推进规划。
        stages = [{"id": ph["id"], "name": ph.get("name", ph["id"]), "status": "pending",
                   "progress": 0, "weight": 10, "owner": "", "note": "",
                   "deliverable": ""} for ph in reg.get("phases", [])]
        save_json(d / "plan.json", {"title": name, "goal": "", "blockers": "", "next": "",
                                    "stages": stages, "milestones": [],
                                    "updated": now()})

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
            # v3.7：显式选档位 = 放弃模型名覆盖（否则 model_id 优先，档位设了也不生效）
            if model_id is None:
                hit["model_id"] = ""
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

_TPL_FALLBACK_CACHE = {"mtime": None, "fb": {}}

# v3.16：模型名归一。换供应商（→ OpenCodeGo）后，老项目 registry / 账本里会留着
# 已不存在的模型名（如 Deepseek-V4-Pro）。读时映射到当前供应商的等价模型，
# **只做读时归一、不改用户文件**；价格表与看板「下轮模型」因此能对上号。
_MODEL_ALIAS = {
    "deepseek-v4-pro": "kimi-k3",              # 原 reasoning 档位已下线 → 最强可用
    "deepseek-v4.1-flash": "deepseek-v4.1-flash",
    "deepseek v4 flash": "deepseek-v4.1-flash",
    "kimi-k3": "kimi-k3",
    "hy4 preview": "hy4-preview",
    "hy4-preview": "hy4-preview",
    "glm-5.3-flash": "GLM-5.3-Flash",
}


def normalize_model(name):
    """历史/大小写不一致的模型名 → 当前供应商规范名；未知名字原样返回。"""
    if not isinstance(name, str):
        return name
    return _MODEL_ALIAS.get(name.strip().lower(), name)


def _template_fallbacks():
    """全局模板里各角色的 fallback 降级链（带 mtime 缓存，避免每次轮询都读盘）。"""
    try:
        mt = TEMPLATE.stat().st_mtime
    except OSError:
        return {}
    if _TPL_FALLBACK_CACHE["mtime"] != mt:
        tpl = load_json(TEMPLATE, {})
        _TPL_FALLBACK_CACHE["fb"] = {a.get("id"): a.get("fallback")
                                     for a in tpl.get("agents", [])
                                     if a.get("id") and a.get("fallback")}
        _TPL_FALLBACK_CACHE["mtime"] = mt
    return _TPL_FALLBACK_CACHE["fb"]


def registry(pid=None):
    reg = load_json(proj_dir(pid) / "registry.json", None)
    tpl = load_json(TEMPLATE, {"agents": [], "phases": []})
    if not reg:
        reg = dict(tpl)
    elif not reg.get("agents"):
        # 注册表存在但角色为空（多为老世代项目）→ 缺什么用模板补什么。
        # 否则 snapshot 遍历不到任何 agent，看板的「子 agent 实例」与阶段流水线会全空。
        for k in ("agents", "phases", "model_tiers", "providers", "available_models"):
            if not reg.get(k) and tpl.get(k):
                reg[k] = tpl[k]
    fb = _template_fallbacks()
    for a in reg.get("agents", []):
        # ① 模型名归一（老项目里的旧供应商模型名 → 当前供应商规范名）
        if a.get("model"):
            a["model"] = normalize_model(a["model"])
        if a.get("model_id"):
            a["model_id"] = normalize_model(a["model_id"])
        if isinstance(a.get("fallback"), list):
            a["fallback"] = [normalize_model(x) for x in a["fallback"]]
        # ② 缺 fallback 的旧项目：回退全局模板同名角色的降级链
        if not a.get("fallback") and fb:
            aid = AGENT_ALIAS.get(a.get("id", ""), a.get("id", ""))
            if fb.get(aid):
                a["fallback"] = list(fb[aid])
    return reg


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
        # 标题/执行者/阶段可改：此前这三项只在**新建**时落盘，任务建完就再也改不动
        # （表现：作战地图找不到阶段 → owner 空；任务行没有标题）。空值不覆盖。
        if phase:
            t["phase"] = phase
        if title:
            t["title"] = title
        if agent_id:
            t["agent"] = agent_id
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
        refreshed = []          # v3.16.8：被存活证据续约的 agent（也必须落盘）
        autoclosed = []         # v3.17：ZCode 回合已结束但没收到 finish → 看门狗收口
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
            # ★ v3.17 精准判据（优先）：读 ZCode 客户端 DB 的回合/工具状态。
            #   进行中 → 活着；异常结束 → 立即告警（不等超时）；回合已完成 → 收口为 done。
            #   读不到（表结构变/会话未知）→ verdict=None，继续走下面的启发式兜底。
            _verdict, _reason, _facts = zcode_verdict(
                a.get("zcode_agent"), is_orchestrator=(aid == "orchestrator"))
            if _verdict == "alive":
                a["last_seen"] = now()
                a["lease_source"] = "zcode-db:inflight"
                a["liveness"] = _reason
                refreshed.append(aid)
                continue
            if _verdict == "abnormal":
                a["status"] = "interrupted"
                a["interrupt_kind"] = "abnormal"      # 精确：ZCode 回合异常结束
                a["interrupt_reason"] = _reason
                a["interrupted_at"] = now()
                a["interrupt_step"] = a.get("step", "")
                a["liveness"] = _reason
                a["pid_dead"] = None
                newly.append({"agent": aid, "reason": _reason,
                              "task_id": a.get("task_id"), "step": a.get("step", "")})
                continue
            if _verdict == "finished":
                # ★ 必须先确认：这个"已完成回合"发生在**本次派发之后**。
                #   刚派发（尤其是 resume）时，会话里最后一个回合还是上一轮的（早已完成），
                #   若据此收口，会把正在跑的新任务错标成 done（实测踩过：T106 刚派发就被收口）。
                _lt = (_facts or {}).get("last_turn") or {}
                _ct = _lt.get("completed_at") or 0
                _sp = None
                try:
                    _sp = time.mktime(time.strptime(str(a.get("spawned_at")),
                                                    "%Y-%m-%d %H:%M:%S")) * 1000
                except Exception:
                    _sp = None
                if (not _sp) or (not _ct) or _ct < _sp:
                    # 上一轮的完成记录 / 无本轮派发时间 → 只续约，等新回合出现，**不收口**
                    a["last_seen"] = now()
                    a["lease_source"] = "zcode-db:awaiting-new-turn"
                    refreshed.append(aid)
                    continue
                # 回合已完成超过宽限期仍未收到 finish：自动收口，别让它挂着 working 被误判。
                # 主会话的"回合完成"是常态（我在等用户输入），只续约不收口。
                a["liveness"] = _reason
                if aid == "orchestrator":
                    a["last_seen"] = now()
                    a["lease_source"] = "zcode-db:between-turns"
                    refreshed.append(aid)
                else:
                    a["status"] = "done"
                    a["progress"] = 100
                    a["lease_source"] = "zcode-db:turn-completed"
                    autoclosed.append(aid)
                continue
            # ★ v3.16.6 兜底：ZCode 会话日志有写入 = 在调模型（DB 读不到时的次优证据）
            if zcode_session_alive(a.get("zcode_agent")):
                a["last_seen"] = now()
                a["lease_source"] = "zcode-session-log"
                refreshed.append(aid)
                continue
            age = age_seconds(a.get("last_seen"), since_epoch=SERVER_START)
            if age is None or age <= SILENCE_INTERRUPT:
                continue
            # v3.19：措辞分级 —— 没拿到硬证据时只能说"疑似停滞"，不能断言"中断"
            #   dead   = 进程号确认消失（较硬）
            #   stalled= 仅静默超时、无 DB/日志证据（**疑似**，不是结论）
            if alive is False and a.get("pid"):
                kind, reason = "dead", f"进程 {a.get('pid')} 已消失，且静默 {int(age)} 秒"
            else:
                kind, reason = "stalled", f"疑似停滞：静默 {int(age)} 秒且无会话证据（非结论，可续跑）"
            a["status"] = "interrupted"
            a["interrupt_kind"] = kind
            a["interrupt_reason"] = reason
            a["interrupted_at"] = now()
            a["interrupt_step"] = a.get("step", "")
            a["pid_dead"] = True if alive is False else None
            newly.append({"agent": aid, "reason": reason,
                          "task_id": a.get("task_id"), "step": a.get("step", "")})
        # ★ 续约同样要落盘：此前只在判中断时 save_json，导致"自动续约"改了内存写不回磁盘
        #   （实测现象：last_seen 一直停在旧值，看板显示"静默 10 分钟"却是活的）。
        if newly or refreshed or autoclosed:
            st["updated"] = now()
            save_json(proj_dir(pid) / "state.json", st)
        for n in newly:
            emit("interrupt", n["agent"],
                 f"⚠ 中断：{n['reason']}　（任务 {n['task_id'] or '—'}，停在 {n['step'] or '—'}）",
                 {"reason": n["reason"], "step": n["step"], "task_id": n["task_id"]}, pid=pid)
        for aid in autoclosed:
            a = (st.get("agents") or {}).get(aid) or {}
            emit("auto_close", aid,
                 f"✓ 自动收口：{a.get('liveness', 'ZCode 回合已完成')}　（任务 {a.get('task_id') or '—'}）",
                 {"reason": a.get("liveness", ""), "task_id": a.get("task_id")}, pid=pid)
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
        a["interrupt_kind"] = ""
        a["interrupt_step"] = ""
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
    # v3.7 修复：ack 台账里的 id 可能是字符串（CLI 传参）、消息里的 id 是整数，
    # 直接 `in` 比较永远不相等 → 留言标了"已处理"仍留在队列。两侧统一转 str。
    acked = {str(x) for x in (load_json(ack_path(pid), {"ids": []}).get("ids") or [])}
    notes = [m for m in read_jsonl(bus_dir(pid) / "messages.jsonl")
             if m.get("from") == "user" and str(m.get("id")) not in acked]
    urg = [m for m in notes if (m.get("meta") or {}).get("priority") == "urgent"]
    nor = [m for m in notes if (m.get("meta") or {}).get("priority") != "urgent"]
    return urg + nor


def ack_user_note(note_id, by="orchestrator", pid=None):
    """主 Agent 处理完一条用户指令后调用：从待处理队列摘掉。"""
    with global_lock():
        pid = pid or current_project()
        note_id = str(note_id)          # v3.7：统一字符串，避免与消息整型 id 比较失配
        data = load_json(ack_path(pid), {"ids": []})
        ids = [str(x) for x in (data.get("ids") or [])]
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


def _default_stage(stage_id, pid=None):
    """按 registry 的 phases 造一个默认阶段——作战地图在全新项目里的首次布点。

    没有这个，`cli.py plan --stage S1` 在刚建的项目上只会返回「未知阶段」，
    主 Agent 无法从零把规划表建起来（plan.json 的 stages 无处可生）。
    默认等权 10：不臆测需求优先级，需要时自行改 plan.json。
    """
    for ph in registry(pid).get("phases", []):
        if ph.get("id") == stage_id:
            return {"id": stage_id, "name": ph.get("name", stage_id),
                    "status": "pending", "progress": 0, "weight": 10,
                    "owner": "", "note": "", "deliverable": ""}
    return None


def set_plan_stage(stage_id, pid=None, **kw):
    """更新某个阶段的状态/进度/备注。主 Agent 在每个里程碑调用一次。
    阶段不存在时（全新项目）按 registry phases 自动建点，而不是报错。"""
    with global_lock():
        pid = pid or current_project()
        plan = get_plan(pid)
        hit = None
        for s in plan.get("stages", []):
            if s.get("id") == stage_id:
                hit = s
                break
        if hit is None:
            hit = _default_stage(stage_id, pid)
            if hit is None:
                return {"error": f"未知阶段：{stage_id}"}
            plan.setdefault("stages", []).append(hit)
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
    """整体进度 = Σ(权重 × 阶段进度) / Σ权重 × 100，四舍五入到整数。

    v3.18：`status='skipped'`（本任务不适用，如内部工具优化不做 S5~S7）
    的阶段**从分母里剔除** —— 否则它们会永远挂着 0%，整体进度假性卡死
    （实测：5/8 完成等权 → 永远 63%）。
    """
    _all = (plan or {}).get("stages") or []
    stages = [s for s in _all
              if str(s.get("status") or "").lower() not in ("skipped", "n/a")]
    tw = sum(float(s.get("weight") or 0) for s in stages)
    if tw <= 0:
        return 100 if _all else 0
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
AGENT_ALIAS = {"pm": "product-manager",
               # v3.8：派发方用简写 id 时，计量并入正式角色，避免看板出现重复零行
               "frontend": "frontend-dev", "backend": "backend-dev"}
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


def _usage_for(agent_id, st, ws=None):
    """取某角色的**真实用量**（ZCode 或 OpenCode，由 runtime/lib/usage.py 适配层决定）。

    返回结构与 usage.sessions() 一致；取不到返回 None。
    一个角色跑过多条会话时合并成一条（token 相加、成本相加、保留最近一次的 last_turn）。
    """
    try:
        import usage as _u
    except Exception:
        return None
    rec = (st.get("agents") or {}).get(agent_id) or {}
    try:
        rows = _u.sessions(agent_id=agent_id, workspace=str(ws or WS),
                           zcode_agent=rec.get("zcode_agent"))
    except Exception:
        return None
    if not rows:
        return None
    if len(rows) == 1:
        return rows[0]
    base = dict(rows[-1])
    for k in ("input", "output", "reasoning", "cache_read", "cache_write",
              "turns", "requests", "tool_calls", "duration_ms"):
        base[k] = sum(int(r.get(k) or 0) for r in rows)
    base["total"] = base["input"] + base["output"]
    costs = [r.get("cost_usd") for r in rows if r.get("cost_usd") is not None]
    base["cost_usd"] = sum(costs) if costs else None
    base["session_id"] = "+".join(str(r.get("session_id")) for r in rows)
    base["sessions"] = len(rows)
    return base


def usage_backend():
    """当前真实计量的数据源（zcode / opencode / none）。"""
    try:
        import usage as _u
        return _u.backend()
    except Exception:
        return "none"


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
    # ── v3.19：真实计量（ZCode DB turn_usage），与上面的"估算"并列返回 ──
    #   估算 = 按上报文本字节（旧账本）；真实 = 客户端记录的 input/output/cache 分项。
    #   实测差距可达 30 倍以上（且 99% 输入是缓存命中，混合价根本不适用）。
    actual, seen_sessions = {}, set()
    actual_total_tokens = 0
    actual_total_cost = Decimal("0")
    has_actual_unpriced = False
    for a in agents:
        tk = _usage_for(a, st)
        if not tk:
            continue
        # OpenCode 的 session 行自带 cost；ZCode 只有分项 token，需按单价算。
        c_ = tk.get("cost_usd")
        if c_ is None:
            c_ = actual_cost_usd(tk, tbl)
        if tk["session_id"] in seen_sessions:     # 同一会话被多角色引用时不重复计总
            actual[a] = {**tk, "cost_usd": c_, "counted_in_total": False}
            continue
        seen_sessions.add(tk["session_id"])
        if c_ is None:
            has_actual_unpriced = True
        else:
            actual_total_cost += Decimal(str(c_))
        actual_total_tokens += int(tk.get("total") or 0)
        actual[a] = {**tk, "cost_usd": c_, "counted_in_total": True}
    # 后端以**实际取到数据的那个**为准（auto 模式会两个源都试），而不是“哪个库存在”
    _ub = next((v.get("backend") for v in actual.values() if v.get("backend")),
               usage_backend())
    _src = {"zcode": "ZCode 客户端 DB（turn_usage）",
            "opencode": "OpenCode DB（session）",
            "none": "无可用数据源"}.get(_ub, _ub)
    return {"calibration": calibration, "price_version": tbl.get("version", ""),
            "total_tokens": total_tokens,
            "total_cost_usd": float(total_cost.quantize(Decimal("0.000001"),
                                                        rounding=ROUND_HALF_UP)),
            "has_unpriced": has_unpriced, "agents": agents,
            # 真实计量（推荐看板优先展示这一组）
            "actual": actual,
            "actual_total_tokens": actual_total_tokens,
            "actual_total_cost_usd": float(actual_total_cost.quantize(
                Decimal("0.000001"), rounding=ROUND_HALF_UP)),
            "has_actual_unpriced": has_actual_unpriced,
            "backend": _ub,
            "actual_note": f"真实值来自 {_src}；估算值来自上报文本字节，仅作兜底"
                           + ("" if _ub != "none" else "（当前两个客户端 DB 都读不到，"
                                                      "估算值不可信，勿据此决策）")}


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


def set_reported_model(agent_id, model, source="system-prompt", pid=None, task_id=None):
    """登记子 agent 回传信号里 [模型] 行的**实测自报**值（v3.16.4）。

    与另外两个口径严格分开：
      · registry 的 model                = 配置（账本，应当是什么）
      · state 的 model（spawn --model）  = 派发声明（谁派的谁写，未核实）
      · 本函数的 reported_model          = 子 agent 抄自己系统提示的**实测值**（可核实）
    """
    with global_lock():
        pid = pid or current_project()
        aid = AGENT_ALIAS.get(agent_id, agent_id)
        st = state(pid)
        rec = (st.get("agents") or {}).setdefault(aid, {})
        rec["reported_model"] = (model or "").strip()
        rec["reported_source"] = source or "unknown"
        rec["reported_at"] = now()
        if task_id:
            rec["reported_task"] = task_id
        st["updated"] = now()
        save_json(proj_dir(pid) / "state.json", st)
        emit("model_report", aid, f"实测自报模型：{model}",
             {"model": model, "source": source, "task_id": task_id}, pid=pid)
        return {"ok": True, "agent": aid, "reported_model": rec["reported_model"],
                "reported_at": rec["reported_at"]}


# ---------- ZCode 会话记录读取：实际使用的模型（v3.16.5） ----------
#
# 为什么需要它：registry 是"配置"、spawn --model 是"声明"、子 agent 的 [模型] 行是"自报"，
# 三者都可能与事实不符。ZCode 自己按会话逐请求记录了**实际**用的模型与思考档位：
#   ~/.zcode/cli/rollout/model-io-sess_subagent_<agentId>.jsonl （主会话则是 model-io-sess_<sessionId>.jsonl）
# 每行一次请求，含 model.modelId / response.modelId / request.body.model 与
# providerOptions.{anthropic.effort, anthropic.thinking.budgetTokens, openaiCompatible.reasoningEffort}。
# 文件巨大（可达数十 MB），故只读尾部若干 KB、从后往前取最近一条成功请求。

ZC_ROLLOUT = Path(os.path.expanduser("~/.zcode/cli/rollout"))


def zcode_session_actual(zcode_agent_id, tail_bytes=512 * 1024):
    """读 ZCode 会话日志，返回实际模型与思考档位。找不到返回 None。
    zcode_agent_id 可传 'agent_xxx'（子 agent）或 'sess_xxx'（主会话）。"""
    if not zcode_agent_id:
        return None
    aid = str(zcode_agent_id).strip()
    names = []
    if aid.startswith("agent_"):
        names = [f"model-io-sess_subagent_{aid}.jsonl"]
    else:
        names = [f"model-io-sess_{aid}.jsonl", f"model-io-{aid}.jsonl"]
    for name in names:
        p = ZC_ROLLOUT / name
        if not p.exists():
            continue
        try:
            size = p.stat().st_size
            with p.open("rb") as f:
                if size > tail_bytes:
                    f.seek(size - tail_bytes)
                    f.readline()          # 丢掉被截断的半行
                raw = f.read()
            lines = [l for l in raw.decode("utf-8", "replace").splitlines() if l.strip()]
            model_id = provider = effort = None
            for line in reversed(lines):
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                m = d.get("model") or {}
                model_id = m.get("modelId") or d.get("response", {}).get("modelId")
                if not model_id:
                    continue
                provider = m.get("providerId") or provider
                po = (d.get("request") or {}).get("providerOptions") or {}
                effort = ((po.get("anthropic") or {}).get("effort")
                          or (po.get("openaiCompatible") or {}).get("reasoningEffort"))
                budget = ((po.get("anthropic") or {}).get("thinking") or {}).get("budgetTokens")
                return {"model": model_id, "provider": provider, "effort": effort,
                        "thinking_budget": budget, "file": name, "at": now()}
        except Exception:
            continue
    return None


def zcode_session_alive(zcode_agent_id, within=None):
    """ZCode 会话日志最近是否有写入 —— 比"静默"硬得多的**存活证据**（v3.16.6）。

    看门狗原来只看 agent 有没有调 cli.py 上报，看不到它其实一直在调模型干活，
    于是长任务（写大文件、跑自测、连续编辑）超过 240s 不上报就被误判"中断"。
    现在：日志文件在最近 within 秒内被写过 → 判定活着，刷新 last_seen。
    """
    if not zcode_agent_id:
        return None
    win = within if within is not None else max(SILENCE_INTERRUPT * 2, 480)
    aid = str(zcode_agent_id).strip()
    # 两种会话 id 都要认（与 zcode_session_actual 同口径）：
    #   agent_xxx → 子 agent 会话文件；sess_xxx → 主会话文件
    names = ([f"model-io-sess_subagent_{aid}.jsonl"] if aid.startswith("agent_")
             else [f"model-io-sess_{aid}.jsonl", f"model-io-{aid}.jsonl"])
    for name in names:
        p = ZC_ROLLOUT / name
        if not p.exists():
            continue
        try:
            return (time.time() - p.stat().st_mtime) <= win
        except Exception:
            continue
    return None


def main_session_actual():
    """读**主会话**（非 subagent）最近活跃的会话日志 → 实际模型/档位。

    用途：派发前把这个值和 registry 里各角色的配置比对 —— 因为 Agent 工具没有 model
    参数，子 agent 要么按角色定义的 model（会话启动时加载）、要么继承主会话模型。
    两者不同就说明"按配置派发不会生效"，得切会话模型或新开会话。
    """
    try:
        files = [p for p in ZC_ROLLOUT.glob("model-io-sess_*.jsonl") if "subagent" not in p.name]
        if not files:
            return None
        newest = max(files, key=lambda p: p.stat().st_mtime)
        sid = newest.name[len("model-io-sess_"):-len(".jsonl")]
        return zcode_session_actual(sid)
    except Exception:
        return None


def zcode_session_tokens(zcode_agent_id):
    """读该会话在 ZCode DB 里的**真实 token 计量**（turn_usage 逐回合求和）。

    字段语义（已实测核对）：
      · input_tokens 含 cache_read（即 input = 新读 + 缓存命中）
      · output_tokens **已含 reasoning**（in+out == provider_total == computed_total）
      · cache_creation 为缓存写入（多数网关为 0）
    真实成本 = (input-cache_read)×输入价 + cache_read×缓存读价 + output×输出价
    （不能再用"文本字节估算 × 混合价"——实测差 30 倍以上）
    """
    aid = str(zcode_agent_id or "").strip()
    if not aid:
        return None
    sid = f"sess_subagent_{aid}" if aid.startswith("agent_") else aid
    con = _zc_con()
    if con is None:
        return None
    FIELDS = ("input_tokens", "output_tokens", "reasoning_tokens",
              "cache_read_input_tokens", "cache_creation_input_tokens")
    try:
        c = con.cursor()
        c.execute(f"""SELECT COUNT(*), SUM(model_request_count), SUM(tool_call_count), SUM(duration_ms),
                             {', '.join('SUM(' + f + ')' for f in FIELDS)}
                      FROM turn_usage WHERE session_id=?""", (sid,))
        r = c.fetchone()
        if not r or not r[0]:
            return None
        vals = [int(x or 0) for x in r[4:]]
        tk = {"session_id": sid, "turns": int(r[0]), "requests": int(r[1] or 0),
              "tool_calls": int(r[2] or 0), "duration_ms": int(r[3] or 0),
              "input": vals[0], "output": vals[1], "reasoning": vals[2],
              "cache_read": vals[3], "cache_write": vals[4]}
        tk["total"] = tk["input"] + tk["output"]
        # 最近一个回合（≈"本轮"）
        c.execute(f"""SELECT model_request_count, tool_call_count, duration_ms,
                             {', '.join(f for f in FIELDS)}
                      FROM turn_usage WHERE session_id=? ORDER BY started_at DESC LIMIT 1""", (sid,))
        r2 = c.fetchone()
        if r2:
            v2 = [int(x or 0) for x in r2[3:]]
            tk["last_turn"] = {"requests": int(r2[0] or 0), "tool_calls": int(r2[1] or 0),
                               "duration_ms": int(r2[2] or 0), "input": v2[0], "output": v2[1],
                               "reasoning": v2[2], "cache_read": v2[3], "cache_write": v2[4],
                               "total": v2[0] + v2[1]}
        # 主导模型（用于取价）
        c.execute("""SELECT model_id, COUNT(*) n FROM model_usage WHERE session_id=?
                     GROUP BY model_id ORDER BY n DESC LIMIT 1""", (sid,))
        r3 = c.fetchone()
        tk["model"] = r3[0] if r3 else ""
        return tk
    except Exception:
        return None
    finally:
        try:
            con.close()
        except Exception:
            pass


def actual_cost_usd(tk, tbl):
    """按真实单价算成本；缺该模型的单价 → None（调用方回退混合价/标未定价）。"""
    if not tk:
        return None
    raw = (tbl.get("raw_per_1m") or {}).get(tk.get("model") or "")
    if not raw:
        return None
    try:
        p_in = float(raw.get("input") or 0)
        p_out = float(raw.get("output") or 0)
        p_cr = float(raw.get("cache_read") if raw.get("cache_read") is not None else p_in)
        p_cw = float(raw.get("cache_write") or 0)
        fresh = max(0, int(tk.get("input") or 0) - int(tk.get("cache_read") or 0))
        cost = (Decimal(fresh) * Decimal(str(p_in))
                + Decimal(int(tk.get("cache_read") or 0)) * Decimal(str(p_cr))
                + Decimal(int(tk.get("output") or 0)) * Decimal(str(p_out))
                + Decimal(int(tk.get("cache_write") or 0)) * Decimal(str(p_cw))) / Decimal(1000000)
        return float(cost.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))
    except Exception:
        return None


def set_actual_model(agent_id, zcode_agent=None, pid=None):
    """把 ZCode 会话记录里的**实际模型**写进 state（看板「实际」显示这个）。"""
    with global_lock():
        pid = pid or current_project()
        aid = AGENT_ALIAS.get(agent_id, agent_id)
        st = state(pid)
        rec = (st.get("agents") or {}).setdefault(aid, {})
        zid = zcode_agent or rec.get("zcode_agent")
        if zcode_agent:
            rec["zcode_agent"] = zcode_agent
        # 优先读客户端 DB 的 model_usage（结构化：实际模型 + 思考档 + 调用次数），
        # 读不到再回退解析 rollout 日志文件。
        hit = None
        try:
            _f = zcode_session_facts(zid) or {}
            _ms = _f.get("models") or []
            if _ms:
                m = _ms[0]
                hit = {"model": m.get("model_id"), "provider": "", "effort": m.get("variant"),
                       "calls": m.get("n"),
                       "file": f"db:model_usage({_f.get('session_id')})", "at": now()}
        except Exception:
            hit = None
        if not hit:
            hit = zcode_session_actual(zid)
        if not hit:
            rec["actual_error"] = f"未找到会话日志（zcode_agent={zid or '未登记'}）"
            st["updated"] = now()
            save_json(proj_dir(pid) / "state.json", st)
            return {"ok": False, "agent": aid, "zcode_agent": zid,
                    "error": rec["actual_error"]}
        rec["actual_model"] = hit["model"]
        rec["actual_provider"] = hit.get("provider") or ""
        rec["actual_effort"] = hit.get("effort") or ""
        if hit.get("calls"):
            rec["actual_calls"] = hit["calls"]
        _f = str(hit.get("file") or "")
        rec["actual_source"] = (f"zcode-{_f}" if _f.startswith("db:")
                                else f"zcode-rollout:{_f}")
        rec["actual_at"] = hit["at"]
        rec.pop("actual_error", None)
        st["updated"] = now()
        save_json(proj_dir(pid) / "state.json", st)
        emit("model_actual", aid,
             f"实际模型：{hit['model']}" + (f"（思考档：{hit['effort']}）" if hit.get("effort") else ""),
             {"model": hit["model"], "effort": hit.get("effort"), "file": hit["file"]}, pid=pid)
        return {"ok": True, "agent": aid, "actual_model": hit["model"],
                "actual_effort": hit.get("effort"), "source": rec["actual_source"]}


# ---------- ZCode 客户端 DB：精准状态判读（v3.17，只读 + 防御式） ----------
#
# 为什么用它：看门狗原来的判据是"静默超时"（启发式），而 ZCode 客户端自己把**精确**状态
# 记在 ~/.zcode/cli/db/db.sqlite：
#   · turn_usage   —— 回合生命周期：completed_at 为空=进行中；status=cancelled/failed=异常结束；
#                     还带 model_request_count / tool_call_count / tool_error_count / token 计量
#   · tool_usage   —— 每个工具调用的 status（running/completed/error）+ 起止时间
#   · model_usage  —— 每次模型请求实际的 model_id + variant（思考档）+ agent 类型
# 这些把"活着/结束/异常"从"猜"变成"读"。**但它是客户端内部接口（未公开）**，故：
#   · 只读打开（mode=ro），绝不写入；
#   · 任何异常/字段缺失一律返回 None → 调用方回退到原有的启发式判据；
#   · 表结构变了也只是"精准判据失效"，不会让看门狗崩掉。
ZC_DB = Path(os.path.expanduser("~/.zcode/cli/db/db.sqlite"))
ZC_INFLIGHT_FRESH_MS = 30 * 60 * 1000      # 进行中回合/工具的新鲜度上限（超过则不算"活着"）
ZC_DONE_GRACE_S = 60                        # 回合已完成到这个秒数后才由看门狗收口


def _zc_con():
    if sqlite3 is None or not ZC_DB.exists():
        return None
    try:
        con = sqlite3.connect(f"file:{ZC_DB.as_posix()}?mode=ro", uri=True, timeout=2.0)
        con.row_factory = sqlite3.Row
        return con
    except Exception:
        return None


def zcode_session_facts(zcode_agent_id):
    """读某会话的精准状态；查不到返回 None（调用方回退启发式）。"""
    aid = str(zcode_agent_id or "").strip()
    if not aid:
        return None
    sid = f"sess_subagent_{aid}" if aid.startswith("agent_") else aid
    con = _zc_con()
    if con is None:
        return None
    try:
        c = con.cursor()
        out = {"session_id": sid}
        c.execute("""SELECT status, started_at, completed_at, model_request_count,
                            tool_call_count, tool_error_count, cancelled_by_user,
                            error_type, error_code
                     FROM turn_usage WHERE session_id=? ORDER BY started_at DESC LIMIT 1""", (sid,))
        r = c.fetchone()
        out["last_turn"] = dict(r) if r else None
        c.execute("""SELECT started_at, model_request_count, tool_call_count
                     FROM turn_usage
                     WHERE session_id=? AND (completed_at IS NULL OR completed_at=0)
                     ORDER BY started_at DESC LIMIT 1""", (sid,))
        r = c.fetchone()
        out["inflight_turn"] = dict(r) if r else None
        c.execute("""SELECT tool_name, started_at FROM tool_usage
                     WHERE session_id=? AND status='running' ORDER BY started_at DESC LIMIT 5""", (sid,))
        out["running_tools"] = [dict(x) for x in c.fetchall()]
        c.execute("""SELECT model_id, variant, COUNT(*) AS n FROM model_usage
                     WHERE session_id=? GROUP BY model_id, variant ORDER BY n DESC LIMIT 5""", (sid,))
        out["models"] = [dict(x) for x in c.fetchall()]
        return out
    except Exception:
        return None
    finally:
        try:
            con.close()
        except Exception:
            pass


def zcode_fresh_ms(ms, limit_ms):
    try:
        return ms is not None and (time.time() * 1000 - float(ms)) <= limit_ms
    except Exception:
        return False


def zcode_verdict(zcode_agent_id, is_orchestrator=False):
    """把 DB 事实翻译成一个判定：alive / abnormal / finished / None(无据)。
    返回 (verdict, reason, facts)。无据时 verdict=None，调用方回退启发式。"""
    f = zcode_session_facts(zcode_agent_id)
    if not f:
        return None, "", None
    it = f.get("inflight_turn") or {}
    if it and zcode_fresh_ms(it.get("started_at"), ZC_INFLIGHT_FRESH_MS):
        n = it.get("model_request_count")
        return "alive", f"ZCode 回合进行中（已 {n} 次模型请求）", f
    rt = [t for t in (f.get("running_tools") or [])
          if zcode_fresh_ms(t.get("started_at"), ZC_INFLIGHT_FRESH_MS)]
    if rt:
        return "alive", f"ZCode 工具执行中（{rt[0].get('tool_name')}）", f
    lt = f.get("last_turn") or {}
    st = str(lt.get("status") or "").lower()
    if st in ("cancelled", "failed", "aborted", "error") and not is_orchestrator:
        # 主会话的 cancelled 常常是"用户按了停止"（正常交互），故只对子 agent 生效
        extra = []
        if lt.get("error_type"):
            extra.append(f"error_type={lt['error_type']}")
        if lt.get("error_code"):
            extra.append(f"error_code={lt['error_code']}")
        if lt.get("cancelled_by_user"):
            extra.append("cancelled_by_user")
        return "abnormal", f"ZCode 回合异常结束（{st}{'，' + '，'.join(extra) if extra else ''}）", f
    if st == "completed":
        age = None
        try:
            age = (time.time() * 1000 - float(lt.get("completed_at") or 0)) / 1000
        except Exception:
            pass
        if age is not None and age > ZC_DONE_GRACE_S:
            return "finished", (f"ZCode 回合已完成 {int(age)} 秒（未收到 finish，"
                                f"模型请求 {lt.get('model_request_count')} 次）"), f
    return None, "", f

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
            "provider": a.get("provider", "zcode"),
            "model_id": a.get("model_id", ""),
            "params": a.get("params") or {},
            "status": rt.get("status", "idle"),
            "pid": rt.get("pid"),
            "pid_alive": alive,
            # 三个口径分开（v3.16.4）：runtime/dispatched = 派发声明；reported = 实测自报
            "runtime_model": rt.get("model", a.get("model", "default")),
            "dispatched_model": rt.get("model", a.get("model", "default")),
            "reported_model": rt.get("reported_model") or "",
            "reported_at": rt.get("reported_at"),
            # 实际值（ZCode 会话记录，硬证据）
            "zcode_agent": rt.get("zcode_agent") or "",
            "actual_model": rt.get("actual_model") or "",
            "actual_effort": rt.get("actual_effort") or "",
            "actual_provider": rt.get("actual_provider") or "",
            "actual_source": rt.get("actual_source") or "",
            "actual_at": rt.get("actual_at"),
            "actual_error": rt.get("actual_error") or "",
            "actual_calls": rt.get("actual_calls"),
            # v3.7：区分「本轮实际用的」与「下轮将用的」——
            # 下轮生效值来自项目配置 registry（model_id 优先于 model），
            # 本轮值来自派发时在 ZCode 客户端实际选用的模型（spawn --model 登记）。
            "next_model": ((a.get("model_id") or "").strip()
                           or (a.get("model") or "").strip() or "default"),
            "next_model_source": ("model_id" if (a.get("model_id") or "").strip()
                                  else ("model" if (a.get("model") or "").strip() else "default")),
            "task_id": rt.get("task_id"),
            "task_title": rt.get("task_title", ""),
            "step": rt.get("step", ""),
            "progress": rt.get("progress", 0),
            "context_messages": rt.get("context_messages", 0),
            "spawned_at": rt.get("spawned_at"),
            "last_seen": rt.get("last_seen"),
            "silence_seconds": int(silence) if silence is not None else None,
            "interrupt_reason": rt.get("interrupt_reason", ""),
            "interrupt_kind": rt.get("interrupt_kind", ""),
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
    # v3.9：已摘牌的用户指令 id（字符串数组，与 pending_notes 同源于 note_acks.json 台账）。
    # 消息流是历史记录，ack 后条目仍留在流里——前端据此给这些条目打「已处理」标记，
    # 否则用户点了「标记已处理」看不出任何变化。只增字段，不改既有语义。
    acked_notes = [str(x) for x in (load_json(ack_path(pid), {"ids": []}).get("ids") or [])]

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
        # 已摘牌的用户指令 id（v3.9 新增，消息流「已处理」标记用）
        "acked_notes": acked_notes,
        "pending_urgent": len([m for m in pend_notes
                               if (m.get("meta") or {}).get("priority") == "urgent"]),
    }
