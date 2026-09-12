"""子 Agent 命令行工具（多项目版）。

每个子 agent 只用它跟运行时打交道：自报家门、发消息、报进度、读写私有记忆。
所有数据按项目隔离——不指定 --project 就操作当前项目。

    python runtime/cli.py projects
    python runtime/cli.py new --id my-project --name "My Project"
    python runtime/cli.py use  --id my-project
    python runtime/cli.py model --agent pm --model reasoning --project my-project

    python runtime/cli.py spawn    --agent pm --pid 1234 --model reasoning --task T001 --title "需求挖掘"
    python runtime/cli.py say      --from pm --to architect --body "..." --artifact docs/00-charter/02-prd.md
    python runtime/cli.py inbox    --agent architect
    python runtime/cli.py progress --agent pm --pct 40 --step "..." --task T001 --ctx 12
    python runtime/cli.py remember --agent pm --section 长期经验 --text "..."
    python runtime/cli.py recall   --agent pm
    python runtime/cli.py finish   --agent pm --step "PRD v1 已交付"

中断与恢复（看门狗会自动把死掉的 agent 标成 interrupted）：
    python runtime/cli.py resumes                              # 看有哪些待恢复
    python runtime/cli.py resume    --agent architect --note "用户要求优先修数据刷新"
    python runtime/cli.py spawn     --agent architect --pid 9999 --resume   # 续跑，非新开
    python runtime/cli.py resume-done --agent architect
    python runtime/cli.py heartbeat --agent architect --step "长跑中：refresh_px 拉 41 只"

用户 ↔ agent 留言通道：
    python runtime/cli.py note      --to orchestrator --body "把绿徽章阈值改成 55%"
    python runtime/cli.py inbox     --agent orchestrator
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def port():
    f = ROOT / ".port"
    return int(f.read_text(encoding="utf-8").strip()) if f.exists() else 8777


# ★ v4.1 移植：回环直连，不理会 HTTP_PROXY/HTTPS_PROXY。
# 为什么必需：有企业代理的环境里（本机实测 HTTP_PROXY=127.0.0.1:xxxx），
# urllib 默认会**把 127.0.0.1 的请求也送去代理**，代理对回环返回 502 Bad Gateway，
# 于是所有上报命令（spawn/progress/heartbeat/finish/…）全部失败，
# 表现为「服务未启动？」——而服务其实活得好好的。
# 这是最难查的一类故障：排查脚本自己就把自己骗了。
_NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def call(method, path, payload=None, project=None):
    if project:
        path += ("&" if "?" in path else "?") + "project=" + project
    url = f"http://127.0.0.1:{port()}{path}"
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with _NO_PROXY_OPENER.open(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print(f"[cli] 调用失败（服务未启动？）: {e}")
        return {"ok": False}


def build_parser():
    ap = argparse.ArgumentParser(prog="agent-cli")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default=None, help="项目 id，默认当前项目")
    sub = ap.add_subparsers(dest="cmd", required=True)
    add = lambda name, help_: sub.add_parser(name, parents=[common], help=help_)

    p = add("projects", "列出所有项目")
    p = add("new", "新建项目")
    p.add_argument("--id", required=True)
    p.add_argument("--name", default=None)
    p.add_argument("--brief", default="")

    p = add("use", "切换当前项目")
    p.add_argument("--id", required=True)

    p = add("model", "设置某个 agent 的模型档位")
    p.add_argument("--agent", required=True)
    p.add_argument("--model", required=True, choices=["default", "lite", "reasoning"])

    # v3.6：把「设置」变成「可应用」——派发前主 Agent 跑这条拿生效模型，
    # 并把 model 参数传给 Agent 工具。设置面板写的就是这里读的（同一份 registry）。
    add("models", "列出各 agent 的生效模型 + 派发参数（主 Agent 派发前必读）")

    p = add("spawn", "自报家门：登记 PID 与模型")
    p.add_argument("--zcode-agent", dest="zcode_agent", default=None,
                   help="Agent 工具返回的 agent_xxx：看门狗按客户端 DB/会话日志判存活、看板显示实际模型")
    p.add_argument("--agent", required=True)
    p.add_argument("--pid", type=int, default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--task", dest="task_id", default=None)
    p.add_argument("--title", dest="task_title", default="")
    p.add_argument("--resume", action="store_true", help="续跑模式：同 agent id、保留记忆与进度")

    p = add("resume", "登记恢复请求（中断后由主 Agent 执行续跑）")
    p.add_argument("--agent", required=True)
    p.add_argument("--note", default="")

    p = add("resumes", "列出待处理的恢复请求")

    p = add("resume-done", "把某 agent 的恢复请求标记为已处理")
    p.add_argument("--agent", required=True)
    p.add_argument("--resolution", default="")

    p = add("note", "留言给某个 agent（用户→主 Agent 的补充/纠偏通道）")
    p.add_argument("--body", required=True)
    p.add_argument("--to", default="orchestrator")
    p.add_argument("--urgent", action="store_true", help="加急：插队到待处理队列最前")

    p = add("uninterrupt", "撤销一次中断判定（主 Agent 取证确认 agent 其实还活着）")
    p.add_argument("--agent", required=True)
    p.add_argument("--note", default="", help="撤销理由，会写进事件总线留痕")

    p = add("note-ack", "标记某条用户指令已处理（从待处理队列摘掉）")
    p.add_argument("--id", required=True)

    p = add("notes", "查看待处理的用户指令（加急在前）")

    p = add("heartbeat", "长命令期间上报仍在运行")
    p.add_argument("--agent", required=True)
    p.add_argument("--step", default="")

    p = add("plan", "查看/更新项目整体规划（主 Agent 的作战地图）")
    p.add_argument("--stage", default=None, help="阶段 id，如 S1")
    p.add_argument("--status", default=None, help="done/working/pending/blocked")
    p.add_argument("--progress", type=int, default=None)
    p.add_argument("--note", default=None)
    p.add_argument("--goal", default=None, help="改规划表头：本期目标")
    p.add_argument("--blockers", default=None, help="改规划表头：当前阻塞项")
    p.add_argument("--next", dest="nxt", default=None, help="改规划表头：下一步")

    p = add("say", "向其他 agent 发消息")
    p.add_argument("--from", dest="frm", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--artifact", default=None)
    p.add_argument("--type", dest="mtype", default="message",
                   help="类型枚举：message（默认）/ directive / artifact / reject")

    p = add("inbox", "读取发给我的消息")
    p.add_argument("--agent", required=True)
    p.add_argument("--limit", type=int, default=50)

    p = add("progress", "上报进度")
    p.add_argument("--agent", required=True)
    p.add_argument("--pct", type=int, required=True)
    p.add_argument("--step", default="")
    p.add_argument("--task", dest="task_id", default=None)
    p.add_argument("--title", dest="task_title", default="")
    p.add_argument("--phase", default="")
    p.add_argument("--ctx", dest="context_messages", type=int, default=None)
    p.add_argument("--status", default="", help="留空则按 pct 自动判定（100% 视为完成）")

    p = add("task", "创建或更新任务")
    p.add_argument("--id", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--agent", required=True)
    p.add_argument("--phase", default="")
    p.add_argument("--status", default="working")
    p.add_argument("--progress", type=int, default=0)

    p = add("remember", "写入私有记忆")
    p.add_argument("--agent", required=True)
    p.add_argument("--section", default="长期经验")
    p.add_argument("--text", required=True)

    p = add("recall", "读取私有记忆")
    p.add_argument("--agent", required=True)

    p = add("finish", "标记完成")
    p.add_argument("--agent", required=True)
    p.add_argument("--step", default="已完成")
    p.add_argument("--artifact", default=None,
                   help="可选：登记工件（工作区相对路径，正斜杠）")
    p.add_argument("--artifact-summary", dest="artifact_summary", default=None,
                   help="可选：工件一句话摘要，超 100 字服务端截断")

    p = add("token-export", "导出 token 账本汇总与明细（REQ-6，只读动作）")
    p.add_argument("--path", default=None,
                   help="导出目标相对路径，缺省=项目目录下 token-export.json")

    # v4.1 移植：模型三口径（配置 / 声明 / 实际 / 自报）对账用
    p = add("actual-model", "从客户端会话日志/DB 读**实际**模型与思考档位（硬证据，主 Agent 用）")
    p.add_argument("--agent", required=True)
    p.add_argument("--zcode-agent", dest="zcode_agent", default=None,
                   help="Agent 工具返回的 agent_xxx（子 agent 会话 id），首次登记用")

    p = add("model-report", "登记子 agent 回传的实测模型自报（[模型] 行，主 Agent 用）")
    p.add_argument("--agent", required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--source", default="system-prompt")
    p.add_argument("--task", dest="task_id", default=None)

    p = add("blocked", "标记阻塞等待")
    p.add_argument("--agent", required=True)
    p.add_argument("--step", default="等待中")

    p = add("phase", "切换全局阶段")
    p.add_argument("--phase", required=True)

    p = add("reset", "清空当前项目运行时数据")

    # ★ v4.2 契约内联派发：WorkBuddy 下契约不会被自动注入，须由主 Agent 拼进 prompt。
    # 本命令把「契约内联 + pre-flight 校验」机械化，缺一不派（详见 lib/contract.py）。
    p = add("dispatch", "生成契约内联的完整派发 prompt（含 pre-flight 校验）")
    p.add_argument("--agent", required=True, help="角色 id（contracts 子命令可列出）")
    p.add_argument("--task", default=None, help="【目标】文本")
    p.add_argument("--task-file", dest="task_file", default=None, help="从文件读【目标】（与 --task 二选一）")
    p.add_argument("--artifact", action="append", default=[], help="产出物绝对路径，可重复")
    p.add_argument("--allowed-read", dest="allowed_read", action="append", default=[],
                   help="允许读项，精确到节，可重复")
    p.add_argument("--criteria", action="append", default=[], help="完成判据，可重复")
    p.add_argument("--task-id", dest="task_id", default="", help="task_id，如 demo/S2")
    p.add_argument("--section", action="append", default=[], help="只保留这些契约小节（标题前缀），可重复")
    p.add_argument("--agents-dir", dest="agents_dir", default=None, help="契约目录，默认自动解析")
    p.add_argument("--check", action="store_true", help="只做 pre-flight 校验")

    p = add("contracts", "列出角色与契约文件（校验移植完整性）")
    p.add_argument("--agents-dir", dest="agents_dir", default=None)

    return ap


def main():
    a = build_parser().parse_args()
    P = a.project
    out = lambda x: print(json.dumps(x, ensure_ascii=False))

    if a.cmd == "projects":
        r = call("GET", "/api/projects")
        print(f"当前项目: {r.get('current')}")
        for p in r.get("list", []):
            mark = "*" if p["id"] == r.get("current") else " "
            print(f" {mark} {p['id']:<16} {p['name']:<20} {p.get('phase','')} "
                  f"消息{p.get('messages',0)} 活跃{p.get('active',0)}")
    elif a.cmd == "new":
        out(call("POST", "/api/projects",
                 {"id": a.id, "name": a.name or a.id, "brief": a.brief}))
    elif a.cmd == "use":
        out(call("POST", "/api/projects/switch", {"id": a.id}))
    elif a.cmd == "model":
        out(call("POST", "/api/settings/model",
                 {"agent": a.agent, "model": a.model, "project": P}))
    elif a.cmd == "models":
        # 生效模型 = model_id（具体模型名）优先，否则回退 model（档位）
        d = call("GET", "/api/state", project=P) or {}
        ags = d.get("agents") or []
        if not ags:
            print("（无 agent 配置）")
        else:
            print(f"项目：{d.get('project','')}　生效模型（派发时传给 Agent 工具的 model 参数）")
            print("-" * 64)
            for x in ags:
                if x.get("id") == "orchestrator":
                    continue
                mid = (x.get("model_id") or "").strip()
                tier = (x.get("model") or "").strip()
                eff = mid or tier or "default"
                src = "模型名(model_id)" if mid else ("档位(model)" if tier else "默认档")
                print(f"  {x.get('name') or x.get('id'):<8} {x.get('id'):<16} → "
                      f"{eff:<20} 来自 {src}　（本轮实际：{x.get('runtime_model') or '—'}）")
            print("-" * 64)
            print("降级链（额度耗尽/模型不可用时，按序换下一个重派一次）：")
            for x in ags:
                if x.get("id") == "orchestrator":
                    continue
                fb = x.get("fallback") or []
                if fb:
                    print(f"  {x.get('id'):<16} {' → '.join(fb)}")
            print("派发用法：Agent 工具传 model=\"<上面那列>\"; 需具体模型名时同时传 model_id。")
    elif a.cmd == "spawn":
        out(call("POST", "/api/spawn", {"agent": a.agent, "pid": a.pid, "model": a.model,
                                        "task_id": a.task_id, "task_title": a.task_title,
                                        "zcode_agent": getattr(a, "zcode_agent", None),
                                        "resume": bool(getattr(a, "resume", False)),
                                        "project": P}))
    elif a.cmd == "resume":
        out(call("POST", "/api/agent/resume", {"agent": a.agent, "note": a.note, "project": P}))
    elif a.cmd == "resumes":
        r = call("GET", "/api/resume", project=P)
        rs = r.get("resume_requests", [])
        if not rs:
            print("(无待处理的恢复请求)")
        for x in rs:
            print(f"#{x['id']}  {x['agent']}  <- {x.get('by')}  |  任务 {x.get('task_id') or '—'}"
                  f"  |  停在 {x.get('progress', 0)}%  {x.get('step') or ''}")
            if x.get("interrupt_reason"):
                print(f"      中断原因：{x['interrupt_reason']}")
            if x.get("note"):
                print(f"      留言：{x['note']}")
    elif a.cmd == "resume-done":
        out(call("POST", "/api/resume/clear",
                 {"agent": a.agent, "resolution": a.resolution, "project": P}))
    elif a.cmd == "note":
        out(call("POST", "/api/note", {"body": a.body, "to": a.to, "project": P,
                                       "priority": "urgent" if a.urgent else "normal"}))
    elif a.cmd == "uninterrupt":
        out(call("POST", "/api/interrupt/clear",
                 {"agent": a.agent, "note": a.note, "by": "orchestrator", "project": P}))
    elif a.cmd == "note-ack":
        out(call("POST", "/api/note/ack", {"id": a.id, "project": P}))
    elif a.cmd == "notes":
        r = call("GET", "/api/state", project=P)
        ns = r.get("pending_notes", [])
        if not ns:
            print("(无待处理的用户指令)")
        for m in ns:
            tag = "【加急】" if (m.get("meta") or {}).get("priority") == "urgent" else ""
            print(f"#{m['id']} {tag}[{m['ts']}] -> {m.get('to')}")
            print(f"  {m['body']}")
            print()
    elif a.cmd == "heartbeat":
        out(call("POST", "/api/heartbeat", {"agent": a.agent, "step": a.step, "project": P}))
    elif a.cmd == "plan":
        if a.goal or a.blockers or a.nxt:
            out(call("POST", "/api/plan", {"meta": True, "goal": a.goal,
                                           "blockers": a.blockers, "next": a.nxt,
                                           "project": P}))
        elif a.stage:
            out(call("POST", "/api/plan", {"stage": a.stage, "status": a.status,
                                           "progress": a.progress, "note": a.note,
                                           "project": P}))
        else:
            r = call("GET", "/api/plan", project=P)
            print(f"{r.get('title','')}　整体进度 {r.get('overall',0)}%")
            print(f"目标：{r.get('goal','')}")
            if r.get("blockers"):
                print(f"阻塞：{r['blockers']}")
            if r.get("next"):
                print(f"下一步：{r['next']}")
            print("-" * 78)
            for s in r.get("stages", []):
                bar = "#" * int(s.get("progress", 0) / 5)
                print(f"  {s['id']:<4} {s['name']:<12} {str(s.get('status')):<8}"
                      f" w{s.get('weight',0):<3} {s.get('progress',0):>3}% [{bar:<20}]"
                      f"  ← {s.get('owner','')}")
                if s.get("note"):
                    print(f"       {s['note']}")
    elif a.cmd == "say":
        out(call("POST", "/api/message", {"from": a.frm, "to": a.to, "body": a.body,
                                          "artifact": a.artifact, "type": a.mtype,
                                          "project": P}))
    elif a.cmd == "inbox":
        r = call("GET", f"/api/inbox?agent={a.agent}&limit={a.limit}", project=P)
        ms = r.get("messages", [])
        if not ms:
            print("(收件箱为空)")
        for m in ms:
            print(f"[{m['ts']}] {m['from']} -> {m['to']}")
            print(f"  {m['body']}")
            if m.get("artifact"):
                print(f"  附件: {m['artifact']}")
            print()
    elif a.cmd == "progress":
        out(call("POST", "/api/progress", {"agent": a.agent, "pct": a.pct, "step": a.step,
                                           "task_id": a.task_id, "task_title": a.task_title,
                                           "phase": a.phase,
                                           "context_messages": a.context_messages,
                                           "status": a.status, "project": P}))
    elif a.cmd == "task":
        out(call("POST", "/api/task", {"id": a.id, "title": a.title, "agent": a.agent,
                                       "phase": a.phase, "status": a.status,
                                       "progress": a.progress, "project": P}))
    elif a.cmd == "remember":
        out(call("POST", "/api/memory", {"agent": a.agent, "section": a.section,
                                         "text": a.text, "project": P}))
    elif a.cmd == "recall":
        print(call("GET", f"/api/memory?agent={a.agent}", project=P).get("content", ""))
    elif a.cmd == "finish":
        payload = {"agent": a.agent, "step": a.step, "project": P}
        # 09 §9#5：老命令行不含新参数时 payload 与原来一致
        if a.artifact:
            payload["artifact"] = a.artifact
        if a.artifact_summary:
            payload["artifact_summary"] = a.artifact_summary
        out(call("POST", "/api/finish", payload))
    elif a.cmd == "token-export":
        payload = {"project": P}
        if a.path:
            payload["path"] = a.path
        out(call("POST", "/api/token-export", payload))
    elif a.cmd == "actual-model":
        out(call("POST", "/api/model/actual", {"agent": a.agent, "zcode_agent": a.zcode_agent,
                                              "project": P}))
    elif a.cmd == "model-report":
        out(call("POST", "/api/model/report", {"agent": a.agent, "model": a.model,
                                               "source": a.source, "task_id": a.task_id,
                                               "project": P}))
    elif a.cmd == "blocked":
        out(call("POST", "/api/blocked", {"agent": a.agent, "step": a.step, "project": P}))
    elif a.cmd == "phase":
        out(call("POST", "/api/phase", {"phase": a.phase, "project": P}))
    elif a.cmd == "reset":
        out(call("POST", "/api/reset", {"project": P}))
    elif a.cmd in ("dispatch", "contracts"):
        # 本地命令，不经 runtime 服务（因此不带上 --project）
        sys.path.insert(0, str(ROOT / "lib"))
        import contract  # noqa: E402
        if a.cmd == "contracts":
            return contract.main(["list"] + (["--agents-dir", a.agents_dir] if a.agents_dir else []))
        argv = ["dispatch", "--agent", a.agent]
        if a.task:
            argv += ["--task", a.task]
        if a.task_file:
            argv += ["--task-file", a.task_file]
        for x in a.artifact:
            argv += ["--artifact", x]
        for x in a.allowed_read:
            argv += ["--allowed-read", x]
        for x in a.criteria:
            argv += ["--criteria", x]
        for x in a.section:
            argv += ["--section", x]
        if a.task_id:
            argv += ["--task-id", a.task_id]
        if a.agents_dir:
            argv += ["--agents-dir", a.agents_dir]
        if a.check:
            argv += ["--check"]
        return contract.main(argv)


if __name__ == "__main__":
    sys.exit(main())
