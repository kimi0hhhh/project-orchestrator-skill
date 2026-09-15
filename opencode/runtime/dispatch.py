"""派发管家：把主 Agent 每次派发前后的机械动作收成两条命令。

prepare —— 预检允许读文件（缺一不派）→ 回读该角色历史记忆 → 上看板节点 →
           生成可直接粘进 Agent 工具的派发 prompt。
           一条命令顶掉原六步人工动作；预检不过就拒绝出 prompt
           （引用未落盘文件曾造成整轮返工，98k tokens）。
close   —— 验收工件真实存在且非空（不凭回传信号放行）→ 可选补记 finish →
           打印一行门禁记录建议。工件缺失 exit 1。

    python runtime/dispatch.py prepare --agent backend-dev --title "S3 后端契约实现" \
        --reads docs/PROJECT_BRIEF.md,docs/09-api-contract.md \
        --write "C:\\ws\\fundlens\\server.py" \
        --criteria "09 契约逐字段对齐，自验收全绿" --project fundlens

    python runtime/dispatch.py close --agent backend-dev \
        --artifact "C:\\ws\\fundlens\\server.py" \
        --summary "契约接口全部实现" --project fundlens

服务未启动时 prepare 降级可用（本地预检照跑，记忆/看板跳过并提示）；
close 默认不动运行时（finish 归子 agent 自己报），--finish 用于子 agent 忘报时补记。
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli import call  # 复用直连回环（绕系统代理）的 opener 与端口探测

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def out(x):
    print(json.dumps(x, ensure_ascii=False))


def api_ok(r):
    # call() 失败时返回 {"ok": False}；成功响应可能不带 ok 字段
    return isinstance(r, dict) and r.get("ok") is not False


def preflight(paths):
    """逐个实查文件落盘且非空；返回 (合格[(路径,字节)], 错误清单)。"""
    ok, bad = [], []
    for p in paths:
        f = Path(p)
        if not f.is_file():
            bad.append(f"{p}（不存在）")
        elif f.stat().st_size == 0:
            bad.append(f"{p}（0 字节）")
        else:
            ok.append((p, f.stat().st_size))
    return ok, bad


def fetch_memory(agent, project):
    r = call("GET", f"/api/memory?agent={agent}", project=project)
    if not api_ok(r):
        return None
    return (r.get("content") or "").strip()


def build_prompt(a, reads, memory):
    cli = a.cli_path
    lines = []
    add = lines.append
    add(f"你是 {a.agent}，任务：{a.title}")
    add("")
    add("【允许读】（只读下列文件，禁止浏览整个目录）")
    for p, size in reads:
        add(f"- {p}（{size // 1024 + (1 if size % 1024 else 0)} KB）")
    add("")
    add("【必须写】")
    add(f"- {a.write}（绝对路径；没有交付物就是没有任务）")
    add("")
    add("【硬约束】")
    add("- 禁止修改 runtime/** 与 .opencode/state/**（看板状态归主 Agent 管）")
    add("- 禁止再派发子 agent；需要拆解时在回传里上报主 Agent")
    for x in a.extra or []:
        add(f"- {x}")
    if a.project:
        add("")
        add(f"【上报协议】（所有命令带 --project {a.project}）")
        add(f"- 开工即报：{cli} progress --agent {a.agent} --pct 5 --step \"已启动，正在读 X\"")
        add("- 进度按任务时长定：预计 ≤10 分钟的任务，开工 1 报 + finish 即可，不凑次数；更长任务每约 5 分钟报 1 次")
        add("- 超过 90 秒的命令先发 heartbeat；深思/写码超 10 分钟补 heartbeat --note")
        add("- 验证有上限：自测/核查按【完成判据】的规模执行，禁止自行加码大规模验证")
        add(f"- 收工前把关键决策/踩坑写进记忆：{cli} remember --agent {a.agent} --section 长期经验 --text \"...\"")
        add(f"- 完成：{cli} finish --agent {a.agent} --artifact <产出路径> --artifact-summary \"一句话\"")
    add("")
    add("【完成判据】")
    add(f"- {a.criteria or '交付物已写且自验收通过'}")
    add("")
    add("【角色记忆】（该角色历次留下的经验，与本任务相关就遵守）")
    if memory:
        for seg in memory.splitlines():
            add(f"> {seg}" if seg else ">")
    else:
        add("-（暂无）")
    add("")
    add("【回传】≤15 行，四块齐全：自验收逐条 ✅/❌ / 交付物路径 / 风险与未决项 / 下一步建议")
    return "\n".join(lines)


def cmd_prepare(a):
    read_paths = [p.strip() for p in (a.reads or "").split(",") if p.strip()]
    reads, bad = preflight(read_paths)
    errors = [f"允许读文件未落盘：{x}" for x in bad]

    write = Path(a.write) if a.write else None
    if write:
        write.parent.mkdir(parents=True, exist_ok=True)
        if write.is_file() and write.stat().st_size > 0:
            print(f"⚠ 工件已存在非空：{write}（增量任务请确认是续写而非覆盖）")
    else:
        errors.append("未指定 --write：没有交付物就是没有任务")

    if errors:
        for e in errors:
            print(f"❌ {e}")
        print("—— 预检未过，不生成派发 prompt，先补齐文件或改对路径")
        sys.exit(1)

    memory = fetch_memory(a.agent, a.project)
    if memory is None:
        print("⚠ 运行时未连接，跳过角色记忆回读与看板节点（prompt 照常生成）")
    elif a.no_spawn:
        print("ℹ --no-spawn：跳过看板节点与看板侧动作（记忆照常回读）")
    else:
        r = call("POST", "/api/spawn",
                 {"agent": a.agent, "pid": None, "model": a.model,
                  "task_id": a.task, "task_title": a.title, "project": a.project})
        print("✅ 看板节点已建" if api_ok(r) else "⚠ 看板节点登记失败（服务异常？派发照常）")
        n = len(memory)
        print(f"✅ 角色记忆已回读（{n} 字，已嵌入 prompt）" if n else "ℹ 该角色暂无历史记忆")

    prompt = build_prompt(a, reads, memory or "")
    if a.prompt_file:
        pf = Path(a.prompt_file)
        pf.parent.mkdir(parents=True, exist_ok=True)
        pf.write_text(prompt, encoding="utf-8")
        n = len(prompt.encode("utf-8"))
        print(f"✅ 派发任务书已落盘：{pf}（{n} 字节）")
        print("【Agent 工具调用】prompt 用一行引用（主 Agent 上下文只背这一行，不背任务书全文）：")
        print(f"   读取 {pf} 并严格执行：先完整读完任务书，再按【必须写】【硬约束】【上报协议】执行")
    else:
        print("\n==================== 派发 prompt 开始（subagent_type=%s）====================" % a.agent)
        print(prompt)
        print("==================== 派发 prompt 结束 ====================")
        print("提示：长会话/多次派发建议加 --prompt-file，主 Agent 每次派发只背一行引用")
    if not a.no_spawn and memory is not None:
        print("注意：task 工具回传的 task_id 请用 spawn --agent <id> --session-id <task_id> --session-only 登记（看板据此按角色归因 token 与实际模型）")


def cmd_close(a):
    f = Path(a.artifact)
    if not f.is_file() or f.stat().st_size == 0:
        print(f"❌ 工件未落盘或为空：{a.artifact} —— 不出 gate-log 建议行；"
              f"退回该子 agent 续会话返修，或取证后重派")
        sys.exit(1)
    if a.expect:
        text = f.read_text(encoding="utf-8", errors="ignore")
        if a.expect not in text:
            print(f"❌ 工件缺少预期标记「{a.expect}」——疑未按判据产出，不予放行")
            sys.exit(1)
    print(f"✅ 工件已实查：{a.artifact}（{f.stat().st_size} 字节）")

    if a.finish:
        r = call("POST", "/api/finish",
                 {"agent": a.agent, "step": a.step,
                  "artifact": a.artifact.replace("\\", "/"),
                  "artifact_summary": a.summary, "project": a.project})
        print("✅ finish 已补记" if api_ok(r) else "⚠ finish 补记失败（运行时未连接）")

    print(f"gate-log 建议行：| {date.today().isoformat()} | {a.agent} | "
          f"{f.name} | 【待判】 | {a.summary or ''} | 积木={a.blocks or '未记'} |")
    print("收尾：对照 gate-rules 判 PASS/CONCERN/FAIL 写入 .opencode/state/gate-log.md，"
          "再跑 python runtime/board_sync.py")
    if not a.blocks:
        print("提示：加 --blocks \"D,T,C\" 记录这次验收用了哪几块积木（见 scoring/README.md）——"
              "积木分靠这一列沉淀：2~3 个项目后才能算出『哪种组合最划算』。")


def main():
    ap = argparse.ArgumentParser(prog="dispatch", description="派发管家：prepare 派发 / close 验收")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default=None, help="项目 id，默认当前项目")
    common.add_argument("--agent", required=True, help="角色 id（subagent_type 同名）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", parents=[common], help="预检 + 记忆回读 + 看板节点 + 生成派发 prompt")
    p.add_argument("--title", required=True, help="任务标题（看板节点名）")
    p.add_argument("--reads", default="", help="允许读清单，逗号分隔")
    p.add_argument("--write", required=True, help="必须写的工件绝对路径")
    p.add_argument("--criteria", default="", help="完成判据一句话")
    p.add_argument("--extra", action="append", default=[], help="附加约束，可重复")
    p.add_argument("--task", default=None, help="任务 id（可选）")
    p.add_argument("--model", default=None, help="登记进派发台账的模型档（可选）")
    p.add_argument("--no-spawn", action="store_true", help="只生成 prompt，不动看板与记忆")
    p.add_argument("--prompt-file", dest="prompt_file", default=None,
                   help="任务书落盘到该路径，Agent 调用只写一行引用（主 Agent 上下文每次派发省 1–2k token）")
    p.add_argument("--cli-path", dest="cli_path",
                   default='python "' + str(Path(__file__).resolve().parent / "cli.py") + '"',
                   help="任务书里上报协议用的 cli 调用路径；默认=本 runtime 的绝对路径"
                        "（机器装有多份框架副本时，相对路径会让子 agent 上报分流到错误运行时，"
                        "看门狗随即误判中断——2026-09-12 串行对照臂实测踩坑）")

    p = sub.add_parser("close", parents=[common], help="验收工件 + gate-log 建议行")
    p.add_argument("--artifact", required=True, help="待验收工件路径")
    p.add_argument("--expect", default=None, help="工件必须包含的标记串（可选）")
    p.add_argument("--summary", default="", help="工件一句话摘要")
    p.add_argument("--blocks", default=None,
                   help="本次验收用了哪几块积木（逗号分隔，如 D,T,C 或 R + 见 scoring/README.md）；"
                        "记进 gate-log 建议行，用于跨项目标定「哪种组合最划算」")
    p.add_argument("--finish", action="store_true", help="子 agent 忘报 finish 时由主 Agent 补记")
    p.add_argument("--step", default="已完成", help="finish 的 step 文案（配合 --finish）")

    a = ap.parse_args()
    if a.cmd == "prepare":
        cmd_prepare(a)
    else:
        cmd_close(a)


if __name__ == "__main__":
    main()
