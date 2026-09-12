"""契约内联派发 —— WorkBuddy 深度适配 v4.2

## 为什么需要这个模块

上游 ZCode 版把 `agents/<name>.md` 当作子 agent 的 frontmatter 定义，
契约由宿主**作为系统提示自动注入**，所以派发 prompt 里不需要带契约内容。

WorkBuddy **没有这个机制**：
  - 子 agent 一律以 `subagent_type: general-purpose` 派发；
  - `plugins/*/agents/*.md` 里的 agent 类型虽然可作 `subagent_type` 使用，
    但那是**应用启动时注册**的（实测：会话内向 `.workbuddy/agents/` 写入
    `probe-agent.md` 后立即派发，返回 `Task agent probe-agent is not available`）；
  - 而编排的派发发生在**同一个会话内**，不可能中途重启应用。

→ 结论：**契约必须由主 Agent 显式内联进派发 prompt**。
  这不是"降级方案"，而是在 WorkBuddy 上实现「契约必然进入子 agent 上下文」
  这一**唯一可行**的手段，比上游更可靠——上游靠宿主，本版靠代码。

## 同时解决的两个老问题

1. **pre-flight 从"记得写"变成"写不出错"**
   原先 pre-flight checklist 是文档里的一条规则，靠主 Agent 自觉。
   本模块把【目标】【产出物路径】【边界】【task_id】+ 上报要求 + 完成判据
   做成**必填字段校验**：缺一项就拒绝生成派发 prompt（"缺一不派"机械化）。

2. **契约可按节裁剪**，避免把 9 KB 契约全塞给只需要其中两节的子 agent。
"""

import argparse
import sys
from pathlib import Path

# ── 角色登记表 ────────────────────────────────────────────────────────────
# 键 = 运行时/看板用的 agent id；值 = (契约文件名, 中文角色名)
ROLES = {
    "orchestrator": ("00-orchestrator.md", "主 Agent（项目负责人）"),
    "product-manager": ("01-product-manager.md", "产品经理"),
    "architect": ("02-architect.md", "架构师"),
    "frontend-dev": ("03-frontend-dev.md", "前端工程师"),
    "backend-dev": ("04-backend-dev.md", "后端工程师"),
    "dev-lead": ("05-dev-lead.md", "开发组长"),
    "qa": ("06-qa.md", "测试工程师"),
}

# 派发 prompt 的必填字段（缺一不派）
REQUIRED = ("role", "task", "artifacts", "allowed_read", "task_id")

AGENTS_SUBDIR = Path(".workbuddy") / "agents"


# ── 路径解析 ──────────────────────────────────────────────────────────────
def resolve_agents_dir(cwd=None, override=None):
    """返回契约目录。

    优先级：显式 override > 工作区 `.workbuddy/agents/` > 资产源 skill 目录。
    工作区优先的原因见 ORCHESTRATOR.md：资产源是只读模板，引用它会让子 agent
    读到与工作区不同步的版本。
    """
    if override:
        return Path(override)
    base = Path(cwd) if cwd else Path.cwd()
    local = base / AGENTS_SUBDIR
    if local.is_dir() and any(local.glob("*.md")):
        return local
    # 回退：本文件位于 <skill>/runtime/lib/contract.py
    return Path(__file__).resolve().parents[2] / "agents"


def load_contract(role, agents_dir=None, cwd=None):
    """读取角色契约正文（含标题与 yaml 元信息块，不含任何加工）。"""
    if role not in ROLES:
        raise KeyError(f"未知角色 {role!r}，可选：{', '.join(ROLES)}")
    fname = ROLES[role][0]
    path = resolve_agents_dir(cwd=cwd, override=agents_dir) / fname
    if not path.is_file():
        raise FileNotFoundError(f"契约文件不存在：{path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"契约文件为空：{path}")
    return text


# ── 按节裁剪 ──────────────────────────────────────────────────────────────
def split_sections(text):
    """把契约按 `## ` 一级小节切开，返回 (前言, [(标题, 正文), ...])。"""
    lines = text.splitlines()
    preamble, sections, cur, buf = [], [], None, []
    for ln in lines:
        if ln.startswith("## "):
            if cur is not None:
                sections.append((cur, "\n".join(buf).strip()))
            cur, buf = ln[3:].strip(), [ln]
        elif cur is None:
            preamble.append(ln)
        else:
            buf.append(ln)
    if cur is not None:
        sections.append((cur, "\n".join(buf).strip()))
    return "\n".join(preamble).strip(), sections


def extract_sections(text, wanted):
    """只保留标题以 wanted 中任一项开头的小节（保留前言）。wanted 为空则返回全文。"""
    if not wanted:
        return text
    pre, secs = split_sections(text)
    keys = [w.strip() for w in wanted if w.strip()]
    kept = [body for title, body in secs if any(title.startswith(k) for k in keys)]
    if not kept:
        raise ValueError(f"未匹配到任何小节：{wanted}（可用小节：{[t for t, _ in secs]}）")
    return "\n\n".join([pre] + kept).strip()


# ── 校验 ──────────────────────────────────────────────────────────────────
def validate(fields):
    """返回缺失/不合规项清单；空列表 = 通过。"""
    problems = []
    for k in REQUIRED:
        v = fields.get(k)
        if not v or (isinstance(v, (list, tuple)) and not any(str(x).strip() for x in v)):
            problems.append(f"缺少必填字段 `{k}`")
    if fields.get("role") and fields["role"] not in ROLES:
        problems.append(f"未知角色 `{fields['role']}`（可选：{', '.join(ROLES)}）")

    for key, label in (("artifacts", "产出物路径"),):
        for p in fields.get(key) or []:
            s = str(p).strip()
            if not s:
                continue
            if not (s.startswith("/") or (len(s) > 2 and s[1] == ":")):
                problems.append(f"{label}须为绝对路径（含盘符）：{s}")

    # 注意：`allowed_read` **不**要求绝对路径 —— 它指的是「读哪个工件的哪几节」，
    # 形如 `02-prd.md §3,§5` 或 `docs/09-api-contract.md 全`，按工件名引用是正常用法。

    crit = fields.get("criteria")
    if not crit or (isinstance(crit, (list, tuple)) and not any(str(x).strip() for x in crit)):
        problems.append("缺少 `完成判据`（子 agent 无法自证、主 Agent 无法验收）")
    return problems


# ── 组装 ──────────────────────────────────────────────────────────────────
def _bullets(items, indent="  ", marker="-"):
    return "\n".join(f"{indent}{marker} {str(x).strip()}" for x in items if str(x).strip())


def build_dispatch_prompt(fields, agents_dir=None, cwd=None):
    """组装完整派发 prompt：标准骨架（前）+ 内联契约（后）。"""
    problems = validate(fields)
    if problems:
        raise ValueError("派发 pre-flight 未通过（缺一不派）：\n" + "\n".join(f"  ✗ {p}" for p in problems))

    role = fields["role"]
    _, zh = ROLES[role]
    contract = load_contract(role, agents_dir=agents_dir, cwd=cwd)
    contract = extract_sections(contract, fields.get("sections"))

    crit = fields.get("criteria") or []
    if isinstance(crit, str):
        crit = [crit]
    pid = fields.get("task_id", "")

    lines = [
        f"【你是】{zh}。角色契约见本文末，**全文遵守**，无需再读契约文件。",
        "",
        f"【目标】{fields['task']}",
        "",
        "【产出物路径】（写这些文件，用绝对路径）",
        _bullets(fields["artifacts"]),
        "",
        "【边界】",
        "  - 允许读（精确到节，超出即越界）：",
        _bullets(fields["allowed_read"], indent="      ", marker="·"),
        "  - 禁止：越界读写；向其他 agent 派发子任务（一层编排，需要增援就上报主 Agent）。",
        "  - 读到 `reject` 消息时必须重派补齐，不得置之不理。",
        "",
        f"【task_id】{pid}",
        "",
        "【上报要求】（不给这些，你会被看门狗判成中断）",
        "  ① **开工即报**：第一条 progress 必须在**读完任何文档之前**发出"
        "（`progress --pct 5 --step \"已启动，正在读 X\"`）；",
        "  ② 每个阶段里程碑各报一次 progress；",
        "  ③ 凡跑 **>90 秒**的命令，**先发 heartbeat** 说明在跑什么，再等结果；",
        "  ④ 连续 **>10 分钟**无 progress 时补一条 heartbeat 自证存活"
        "（看门狗分不清「深思」与「挂死」）；",
        "  ⑤ `finish` 必带 `--artifact <产出物路径> --artifact-summary \"一句话\"`，"
        "多份产出逐份 `say --type artifact` 补登记；禁止只 finish 不登记。",
        "",
        "【完成判据】",
        _bullets(crit),
        "",
        "────────────────────────────────────────────────────────",
        f"## 角色契约（内联）· {zh}",
        "",
        contract,
    ]
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(prog="contract", description="契约内联派发（WorkBuddy v4.2）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("dispatch", help="生成完整派发 prompt")
    p.add_argument("--agent", required=True, choices=list(ROLES))
    p.add_argument("--task", help="【目标】文本")
    p.add_argument("--task-file", help="从文件读【目标】文本（与 --task 二选一）")
    p.add_argument("--artifact", action="append", default=[], help="产出物绝对路径，可重复")
    p.add_argument("--allowed-read", action="append", default=[], help="允许读项（精确到节），可重复")
    p.add_argument("--criteria", action="append", default=[], help="完成判据，可重复")
    p.add_argument("--task-id", default="", help="task_id（如 demo/S2）")
    p.add_argument("--section", action="append", default=[], help="只保留这些小节（按标题前缀），可重复")
    p.add_argument("--agents-dir", default=None, help="契约目录，默认自动解析")
    p.add_argument("--check", action="store_true", help="只做 pre-flight 校验，不输出 prompt")

    q = sub.add_parser("list", help="列出角色与契约文件")
    q.add_argument("--agents-dir", default=None)

    a = ap.parse_args(argv)

    if a.cmd == "list":
        d = resolve_agents_dir(override=a.agents_dir)
        print(f"契约目录：{d}")
        print("-" * 60)
        for rid, (fname, zh) in ROLES.items():
            ok = "ok " if (d / fname).is_file() else "缺失"
            size = (d / fname).stat().st_size if (d / fname).is_file() else 0
            print(f"  [{ok}] {rid:<16} {zh:<14} {fname:<26} {size:>6} B")
        return 0

    task = a.task
    if a.task_file:
        task = Path(a.task_file).read_text(encoding="utf-8")
    if not task and not a.check:
        print("[contract] 缺少 --task 或 --task-file", file=sys.stderr)
        return 2

    fields = {
        "role": a.agent,
        "task": (task or "").strip(),
        "artifacts": a.artifact,
        "allowed_read": a.allowed_read,
        "criteria": a.criteria,
        "task_id": a.task_id,
        "sections": a.section,
    }

    if a.check:
        problems = validate(fields)
        if problems:
            print("pre-flight 未通过（缺一不派）：")
            for x in problems:
                print(f"  ✗ {x}")
            return 1
        print("pre-flight 通过")
        return 0

    try:
        print(build_dispatch_prompt(fields, agents_dir=a.agents_dir))
    except (ValueError, KeyError, FileNotFoundError) as e:
        print(f"[contract] {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
