"""多 Agent 运行时可视化服务（多项目版）。

启动：python runtime/server.py [port]

子 agent 通过 /api/* 上报自己的状态、发消息、写记忆，
因此每个 agent 只需知道自己的 id 与所属项目，无需感知其他 agent 的存在。
"""
import json
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))
import store  # noqa: E402

ROOT = Path(__file__).resolve().parent
UI_DIR = ROOT / "ui"
WS = ROOT.parent

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def free_port(preferred):
    for p in [preferred] + list(range(preferred + 1, preferred + 30)):
        with socket.socket() as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    raise RuntimeError("no free port")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.end_headers()
        self.wfile.write(b)

    def _json_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def do_OPTIONS(self):
        self._send(204, "")

    # ---------------- GET ----------------
    def do_GET(self):
        u = urlparse(self.path)
        p, q = u.path, parse_qs(u.query)
        pid = (q.get("project") or [None])[0]

        if p in ("/", "/ui", "/ui/"):
            return self._file(UI_DIR / "index.html", "text/html; charset=utf-8")

        if p.startswith("/api/state"):
            limit = int(q.get("limit", ["300"])[0])
            snap = store.snapshot(pid=pid, msg_limit=limit)
            # 09 §2：快照新增 tokens 汇总（只增字段）。null=零记账空态；
            # 读取失败 → tokens=null + tokens_error，区别于空态。
            try:
                snap["tokens"] = store.token_summary(pid)
            except Exception as e:
                snap["tokens"] = None
                snap["tokens_error"] = f"ledger read failed: {e}"
            return self._send(200, snap)

        if p.startswith("/api/projects"):
            return self._send(200, store.list_projects())

        if p.startswith("/api/model/main"):
            # v4.1 移植：派发前预检用 —— 本会话（主会话日志）实际模型
            return self._send(200, store.main_session_actual() or {})

        if p.startswith("/api/registry"):
            return self._send(200, {"project": pid or store.current_project(),
                                    "registry": store.registry(pid)})

        if p.startswith("/api/memory"):
            aid = q.get("agent", [""])[0]
            return self._send(200, {"agent": aid, "content": store.read_memory(aid, pid)})

        if p.startswith("/api/inbox"):
            aid = q.get("agent", [""])[0]
            lim = int(q.get("limit", ["50"])[0])
            return self._send(200, {"agent": aid, "messages": store.inbox(aid, lim, pid)})

        if p.startswith("/api/resume"):
            return self._send(200, {"resume_requests": store.pending_resumes(pid)})

        if p.startswith("/api/watchdog"):
            # 供外部定时器调用：主动体检一遍，返回本次新判定为"中断"的 agent
            return self._send(200, {"interrupted": store.watchdog(pid)})

        if p.startswith("/api/plan"):
            plan = store.get_plan(pid)
            return self._send(200, {**plan, "overall": store.overall_progress(plan)})

        if p.startswith("/api/artifacts"):
            arts = []
            for f in sorted((WS / "docs").rglob("*")):
                if f.is_file():
                    arts.append({"path": str(f.relative_to(WS)).replace("\\", "/"),
                                 "name": f.name, "bytes": f.stat().st_size,
                                 "mtime": int(f.stat().st_mtime)})
            return self._send(200, {"artifacts": arts})

        if p.startswith("/api/artifact"):
            rel = q.get("path", [""])[0]
            fp = (WS / rel).resolve()
            if not str(fp).startswith(str(WS)) or not fp.exists():
                return self._send(404, {"error": "not found"})
            text = fp.read_text(encoding="utf-8", errors="replace")
            # 09 §5：新增可选 head 参数（不传=全文返回，老行为逐字节不变）
            head = q.get("head", [None])[0]
            if head is None:
                return self._send(200, {"path": rel, "content": text})
            n = max(0, int(head))
            lines = text.split("\n")
            if lines and lines[-1] == "":        # 尾换行归一化
                lines = lines[:-1]
            total = len(lines)
            return self._send(200, {"path": rel, "content": "\n".join(lines[:n]),
                                    "total_lines": total, "truncated": n < total,
                                    "bytes": len(text.encode("utf-8"))})

        return self._send(404, {"error": "not found"})

    # ---------------- POST ----------------
    def do_POST(self):
        # 兜底：任何业务异常都不得吞掉 HTTP 响应。此前 store 写文件抛 PermissionError
        # 时异常直接炸掉连接（前端 fetch 报 UND_ERR_SOCKET，静默无提示），用户只会觉得
        # 「发送失效了」。包一层后前端能拿到 500 + error 文本，至少能看到失败原因。
        try:
            self._do_post()
        except Exception as e:
            import traceback
            traceback.print_exc()
            try:
                self._send(500, {"error": f"看板服务内部错误: {e}"})
            except Exception:
                pass

    def _do_post(self):
        p = urlparse(self.path).path
        d = self._json_body()
        P = d.get("project")          # None 表示当前项目

        if p == "/api/message":
            rec = store.post_message(
                d.get("from", "?"), d.get("to", "*"), d.get("body", ""),
                d.get("type", "message"), d.get("artifact"), d.get("meta"), pid=P)
            return self._send(200, {"ok": True, "id": rec["id"]})

        if p == "/api/progress":
            aid = d.get("agent")
            pct = max(0, min(100, int(d.get("pct", 0))))
            # 上报 100% 就是干完了；不显式传 status 时不要硬写成 working，
            # 否则已完成的 agent 会在看板上永远显示"工作中"，被看门狗误判成中断。
            store.meter(aid, d.get("step"), "progress", P, kind_text="progress.step")
            status = d.get("status") or ("done" if pct >= 100 else "working")
            if d.get("pid"):
                # v3.15.1：重派/续跑后的新进程自报 pid。此前 agents.json 里一直是
                # 死进程的旧 pid，看门狗消息永远显示"进程 xxxx 已消失"（误导排查）。
                store.update_agent(aid, P, pid=d.get("pid"))
            store.update_agent(aid, P,progress=pct, step=d.get("step", ""),
                               status=status)
            if status in ("done", "idle"):
                # 干完了就把中断痕迹清掉，避免"已完成"的卡片还挂着上次的中断原因
                store.update_agent(aid, P, interrupt_reason="", pid_dead=None)
            if d.get("context_messages") is not None:
                store.update_agent(aid, P,context_messages=int(d["context_messages"]))
            if d.get("task_id"):
                store.upsert_task(d["task_id"], d.get("task_title", ""), aid,
                                  d.get("phase", ""), pid=P, progress=pct,
                                  status="working" if pct < 100 else "done")
            store.emit("progress", aid, f"{pct}% {d.get('step', '')}", {"pct": pct}, pid=P)
            return self._send(200, {"ok": True})

        if p == "/api/task":
            t = store.upsert_task(
                d.get("id"), d.get("title", ""), d.get("agent"), d.get("phase", ""),
                pid=P, status=d.get("status", "pending"),
                progress=d.get("progress", 0), steps=d.get("steps"))
            store.update_agent(d.get("agent"), P, task_id=t["id"],
                               task_title=t["title"], status=d.get("status", "working"))
            store.emit("task", d.get("agent"), f"{d.get('status')} · {t['title']}", pid=P)
            return self._send(200, {"ok": True, "task": t})

        if p == "/api/memory":
            store.append_memory(d.get("agent"), d.get("section", "长期经验"),
                                d.get("text", ""), pid=P)
            return self._send(200, {"ok": True})

        if p == "/api/spawn":
            aid = d.get("agent")
            if d.get("resume"):
                # ★ 续跑：同一个 agent id，保留私有记忆/收件箱/进度，只换进程
                a = store.begin_resume(aid, new_pid=d.get("pid"),
                                       model=d.get("model") or store.registry_agent_model(aid, P),
                                       project=P)
                if d.get("task_id"):
                    store.update_agent(aid, P, task_id=d.get("task_id"),
                                       task_title=d.get("task_title", ""))
                if d.get("zcode_agent"):
                    # v4.1 移植：续跑同样要登记新会话 id，否则看门狗读的是上一轮的死会话
                    store.update_agent(aid, P, zcode_agent=d.get("zcode_agent"))
                store.clear_resume(aid, P, resolution="已续跑")
                # R-2：resume 与 spawn 同权重落轮次起点记录；title 缺省落 tokens=0 边界行
                store.meter(aid, d.get("task_title") or "", "resume_title", P,
                            kind_text="resume.task_title")
                return self._send(200, {"ok": True, "resumed": True,
                                        "rounds": a.get("rounds"),
                                        "progress": a.get("progress", 0)})
            store.update_agent(
                aid, P, status="working", pid=d.get("pid"),
                model=d.get("model") or store.registry_agent_model(aid, P),
                task_id=d.get("task_id"), task_title=d.get("task_title", ""),
                spawned_at=store.now(), progress=0, step="已启动，读取私有记忆")
            if d.get("zcode_agent"):
                # v4.1 移植：登记会话 id —— 看门狗据此读客户端 DB 精准判存活。
                # （上游 v4.1 的 cli.py 会发这个字段但 server 未接收，本版补全。）
                store.update_agent(aid, P, zcode_agent=d.get("zcode_agent"))
            store.meter(aid, d.get("task_title") or "", "spawn_title", P,
                        kind_text="spawn.task_title")
            store.emit("spawn", aid, f"独立进程启动 pid={d.get('pid')} model={d.get('model')}", pid=P)
            return self._send(200, {"ok": True})

        # ---- 中断后的恢复 ----
        if p == "/api/agent/resume":
            return self._send(200, store.request_resume(
                d.get("agent"), d.get("note", ""), d.get("by", "user"), pid=P))

        # ---- 撤销误判：主 Agent 取证确认 agent 其实还活着 ----
        if p == "/api/interrupt/clear":
            return self._send(200, store.clear_interrupt(
                d.get("agent"), d.get("note", ""), d.get("by", "orchestrator"), pid=P))

        if p == "/api/resume/clear":
            return self._send(200, store.clear_resume(
                d.get("agent"), P, resolution=d.get("resolution", "")))

        # ---- 用户 → agent 留言通道（补充内容 / 修正方向）----
        if p == "/api/note":
            rec = store.post_user_note(d.get("body", ""), d.get("to", "orchestrator"),
                                       d.get("type", "directive"),
                                       priority=d.get("priority", "normal"), pid=P)
            return self._send(200, {"ok": True, "id": rec["id"]})

        # ---- 主 Agent 处理完一条用户指令后摘牌 ----
        if p == "/api/note/ack":
            return self._send(200, store.ack_user_note(
                d.get("id"), d.get("by", "orchestrator"), pid=P))

        # ---- 整体规划：主 Agent 在每个里程碑更新阶段状态 ----
        if p == "/api/plan":
            if d.get("meta"):
                return self._send(200, store.set_plan_meta(
                    P, title=d.get("title"), goal=d.get("goal"),
                    blockers=d.get("blockers"), next=d.get("next")))
            return self._send(200, store.set_plan_stage(
                d.get("stage"), P, status=d.get("status"),
                progress=d.get("progress"), note=d.get("note"),
                deliverable=d.get("deliverable")))

        # ---- 子 agent 主动上报"我还活着"（长命令期间用）----
        if p == "/api/heartbeat":
            store.update_agent(d.get("agent"), P,
                               step=d.get("step", "") or None,
                               status="working")
            store.emit("heartbeat", d.get("agent"), d.get("step", "仍在运行"), pid=P)
            return self._send(200, {"ok": True})

        if p == "/api/finish":
            aid = d.get("agent")
            store.meter(aid, d.get("step"), "finish", P, kind_text="finish.step")
            store.update_agent(aid, P,status="done", progress=100,
                               step=d.get("step", "已完成"))
            # 09 §6：新增可选工件登记。缺省（无 artifact）= 老行为逐字节不变。
            art = d.get("artifact")
            if art:
                rel = str(art).replace("\\", "/")
                fp = (WS / rel).resolve()
                if str(fp).startswith(str(WS)):   # 工件路径越界（不在工作区内）拒绝登记
                    summary = str(d.get("artifact_summary") or "")[:100]
                    store.append_artifact(aid, rel, summary, pid=P)
                    # 无论有无 task_id 都进消息流（无主工件兜底展示位，R-3）
                    store.post_message(aid, "*", summary, msg_type="artifact",
                                       artifact=rel, pid=P)
            store.emit("finish", aid, d.get("step", "已完成"), pid=P)
            return self._send(200, {"ok": True})

        if p == "/api/blocked":
            aid = d.get("agent")
            store.update_agent(aid, P,status="blocked", step=d.get("step", "等待中"))
            store.emit("blocked", aid, d.get("step", "等待中"), pid=P)
            return self._send(200, {"ok": True})

        if p == "/api/phase":
            store.set_phase(d.get("phase", "S0"), P)
            store.emit("phase", "orchestrator", f"阶段 → {d.get('phase')}", pid=P)
            return self._send(200, {"ok": True})

        # ---- 项目与设置 ----
        if p == "/api/projects":
            if d.get("action") == "delete":
                return self._send(200, store.delete_project(d.get("id")))
            return self._send(200, store.create_project(
                d.get("id"), d.get("name") or d.get("id"),
                d.get("brief", ""), d.get("models")))

        if p == "/api/projects/switch":
            return self._send(200, {"current": store.set_current(d.get("id"))})

        if p == "/api/settings/model":
            return self._send(200, store.set_agent_model(
                d.get("agent"), d.get("model"), d.get("project") or P,
                provider=d.get("provider"), model_id=d.get("model_id"),
                params=d.get("params")))

        # ---- Token 账本导出（09 §7，REQ-6）。只读动作，失败不改 ledger ----
        if p == "/api/token-export":
            return self._send(200, store.export_tokens(d.get("path"), pid=P))

        # ---- v4.1 移植：模型三口径登记（自报 / 实际）----
        if p == "/api/model/report":
            # 子 agent 回传 [模型] 行后，主 Agent 用 cli.py model-report 登记实测值
            return self._send(200, store.set_reported_model(
                d.get("agent"), d.get("model"), d.get("source", "system-prompt"),
                pid=P, task_id=d.get("task_id")))

        if p == "/api/model/actual":
            # 从客户端会话日志/DB 读**实际**模型（硬证据），可传 zcode_agent 建立关联
            return self._send(200, store.set_actual_model(
                d.get("agent"), zcode_agent=d.get("zcode_agent"), pid=P))

        if p == "/api/reset":
            pd = store.proj_dir(d.get("project") or P)
            # 09 §9#8：reset 连带清账本 ledger.jsonl（五文件清单，写死）
            for f in [pd / "state.json", pd / "tasks.json",
                      pd / "bus" / "messages.jsonl", pd / "bus" / "events.jsonl",
                      pd / "ledger.jsonl"]:
                if f.exists():
                    f.unlink()
            store.ensure_init(d.get("project") or P)
            return self._send(200, {"ok": True})

        return self._send(404, {"error": "not found"})

    def _file(self, path, ctype):
        p = Path(path)
        if not p.exists():
            return self._send(404, "not found", "text/plain; charset=utf-8")
        self._send(200, p.read_bytes(), ctype)


def watchdog_loop(interval=15):
    """服务自带的后台体检线程：每 interval 秒扫一遍，把已死的 agent 标成"中断"。

    这样即使用户没打开看板，中断也会被发现并记进事件总线 —— 不依赖 UI 是否在轮询。
    """
    import threading
    import time as _t

    def run():
        while True:
            try:
                hit = store.watchdog()
                if hit:
                    for h in hit:
                        print(f"[watchdog] {h['agent']} 判定中断：{h['reason']}")
                    sys.stdout.flush()
            except Exception as e:
                print(f"[watchdog] 巡检异常：{e}")
                sys.stdout.flush()
            _t.sleep(interval)

    t = threading.Thread(target=run, daemon=True, name="watchdog")
    t.start()
    return t


def main():
    preferred = int(sys.argv[1]) if len(sys.argv) > 1 else 8777
    port = free_port(preferred)
    store.ensure_init()
    (ROOT / ".port").write_text(str(port), encoding="utf-8")
    watchdog_loop()
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[multi-agent-runtime] http://127.0.0.1:{port}")
    print(f"[multi-agent-runtime] workspace: {WS}")
    print(f"[multi-agent-runtime] 中断看门狗已启动（每 15s 体检，静默 >{store.SILENCE_INTERRUPT}s 或进程消失即判中断）")
    sys.stdout.flush()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
