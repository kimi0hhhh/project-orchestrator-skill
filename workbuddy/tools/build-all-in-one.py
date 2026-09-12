#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""重生成 ALL-IN-ONE.md —— 单文件全量版（给不支持读多文件的工具用）。

用法（在 skill 根目录下）:
    python tools/build-all-in-one.py

拼装顺序：SKILL.md → ORCHESTRATOR.md → protocols/* → agents/*。
SKILL.md 会剥掉 YAML frontmatter 与「资产源目录」blockquote（ALL-IN-ONE 场景没有 skill 目录），
其余文件逐字节保留。改完任何分散文件后**必须重跑本脚本**，否则单文件版会漂移。
"""
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "ALL-IN-ONE.md"

PROTOCOLS = ["handoff-schema.md", "gate-rules.md", "revision-loop.md"]
AGENTS = ["00-orchestrator.md", "01-product-manager.md", "02-architect.md",
          "03-frontend-dev.md", "04-backend-dev.md", "05-dev-lead.md", "06-qa.md"]

AGENT_LABEL = {
    "00-orchestrator.md": "orchestrator",
    "01-product-manager.md": "product-manager",
    "02-architect.md": "architect",
    "03-frontend-dev.md": "frontend-dev",
    "04-backend-dev.md": "backend-dev",
    "05-dev-lead.md": "dev-lead",
    "06-qa.md": "qa",
}


def strip_skill_frontmatter_and_source_block(text):
    """剥掉 YAML frontmatter 与「资产源目录」blockquote 块。"""
    lines = text.split("\n")
    # 1) frontmatter
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                lines = lines[i + 1:]
                break
    # 2) 开头的空行
    while lines and not lines[0].strip():
        lines.pop(0)
    # 3) 「资产源目录」blockquote 块：从该行起连续以 > 开头（含空 > 行）直到空白行
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith("> **资产源目录"):
            j = i
            while j < len(lines) and (lines[j].startswith(">") or not lines[j].strip()):
                j += 1
            i = j
            while i < len(lines) and not lines[i].strip():
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out).strip("\n")


def read(p):
    return p.read_text(encoding="utf-8").strip("\n")


def main():
    missing = [str(p) for p in [ROOT / "SKILL.md", ROOT / "ORCHESTRATOR.md"] if not p.exists()]
    if missing:
        print("缺少文件:", missing)
        return 1

    skill = strip_skill_frontmatter_and_source_block(read(ROOT / "SKILL.md"))
    orch = read(ROOT / "ORCHESTRATOR.md")

    ver = "4.2"
    m = re.search(r'version:\s*"([^"]+)"', read(ROOT / "SKILL.md"))
    if m:
        ver = m.group(1)

    parts = []
    parts.append(f"""# 多 Agent 协作开发框架 · 单文件全量版（ALL-IN-ONE）

> **怎么用**：把这份文件的**全部内容**复制，粘贴到任意 AI 工具里
> （Claude / ChatGPT 的 Project Instructions、Cursor 的 `.cursorrules`、
> Codex / Gemini CLI 的 `AGENTS.md`、或网页版对话的第一轮），
> 然后说：「按 ORCHESTRATOR 继续，先做 S0 立项」。
>
> 本文件自洽，不依赖其他文件。代价是子 Agent 无法单独只读自己那份契约
> （支持 Skills 的工具更省 token，见各拆分文件）。

版本：v{ver}（WorkBuddy 版）｜ 重生成：{datetime.now().strftime('%Y-%m-%d %H:%M')}
｜ 7 个角色 · 3 份协议 · 19 个工件

## 目录

| 章节 | 内容 | 谁该看 |
|---|---|---|
| §1 | SKILL.md · 主 Agent 编排总纲、铁律、关键路径重叠、变更分诊、星形参谋、动态编制 | 主 Agent 必读 |
| §2 | ORCHESTRATOR.md · 阶段状态机 + 派发命令模板 + 分诊 | 主 Agent 必读 |
| §3 | 三份协议（工件结构 / 门禁 / 返工） | 全体 |
| §4 | 七个角色契约 | 各角色只读自己那份 |

> 本单文件版**不含**运行时会话工具（`runtime/`）。需要看板与上报时，
> 请用各拆分文件并跑 `install.sh` 把 `runtime/` 移植进工作区。

---
""")

    parts.append("# §1 主 Agent 编排总纲（SKILL.md）\n\n" + skill)
    parts.append("# §2 主编排手册（ORCHESTRATOR.md）\n\n" + orch)

    parts.append("# §3 三份协议\n")
    for name in PROTOCOLS:
        p = ROOT / "protocols" / name
        if not p.exists():
            print("缺少协议:", p)
            return 1
        title = {"handoff-schema.md": "工件交接规范（handoff-schema）",
                 "gate-rules.md": "门禁判定规则（gate-rules）",
                 "revision-loop.md": "返工与升级规则（revision-loop）"}[name]
        parts.append(f"## {title} · 源文件 `protocols/{name}`\n\n" + read(p))

    parts.append("# §4 七个角色契约\n")
    for name in AGENTS:
        p = ROOT / "agents" / name
        if not p.exists():
            print("缺少契约:", p)
            return 1
        parts.append(f"## 角色 {AGENT_LABEL[name]} · 源文件 `agents/{name}`\n\n" + read(p))

    text = "\n\n---\n\n".join(parts) + "\n"
    OUT.write_text(text, encoding="utf-8")
    print(f"已生成 {OUT}  ({len(text.encode('utf-8'))} bytes, {len(text.splitlines())} 行)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
