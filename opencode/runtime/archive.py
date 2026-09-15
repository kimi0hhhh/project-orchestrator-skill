"""交付包归档：把运行时数据随包带走 · v1

## 为什么需要它
本交付包实测教训：打包时把运行时数据清空了（`projects.json` 重置、`.gitkeep` 占位、
`state.json`/`memory.md` 重新初始化成空壳），于是——
  · 事件总线（谁在什么时候说了什么、报了什么进度）—— **全丢**
  · `plan.json` 阶段史 —— **全丢**
  · `ledger/` 台账与 token 账 —— **全丢**
  · `gate-log` —— 重置成模板，**返修率从此没有分母**
  · 6 份角色 `memory.md` —— 全是「（尚无）」，**记忆机制等于没启用**

而工件是齐的（`docs` 104 个文件）。也就是说：**保留了最终答案，丢掉了协作过程** ——
这正是 MAGE 那篇论文开篇论点（"memory must preserve evidence, decisions, procedures,
and experience across interactions, **not only outcomes**"）在打包环节的复现。

跨包保留事件流还有一个直接用途：**「缺陷发现阶段」这类指标只能在事件流里算**。

## 用法
    python runtime/archive.py                      # 归档当前项目
    python runtime/archive.py --pid fundlens       # 指定项目
    python runtime/archive.py --out <目录>          # 指定归档根（默认 05_数据归档/）

归档内容 = 项目目录（bus/plan/ledger/memory/state）+ `.opencode/state/` 三件
         + `projects.json` 注册 + `registry.json`（还原时一并放回，看板就能认出项目）。

**打包前跑一次**；还原方式写在归档目录里的 `RESTORE.md`。
"""
import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
WS = ROOT.parent


def pick_out(arg):
    if arg:
        return Path(arg)
    for name in ("05_数据归档", "archive", "exports"):
        p = WS / name
        if p.is_dir():
            return p
    return WS / "archive"


def size_of(p):
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def main():
    ap = argparse.ArgumentParser(prog="archive")
    ap.add_argument("--pid", default=None, help="项目 id，默认取 projects.json 的 current")
    ap.add_argument("--out", default=None, help="归档根目录（默认 05_数据归档/）")
    a = ap.parse_args()

    idx = ROOT / "projects.json"
    try:
        cur = json.loads(idx.read_text(encoding="utf-8")).get("current")
    except Exception:
        cur = None
    pid = a.pid or cur

    out_root = pick_out(a.out)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = out_root / f"runtime-{pid or 'all'}-{stamp}"
    dest.mkdir(parents=True, exist_ok=True)

    items = []
    if pid:
        src = ROOT / "projects" / pid
        if src.is_dir():
            shutil.copytree(src, dest / "projects" / pid)
            items.append((f"projects/{pid}/", size_of(src)))
    for rel in ("projects.json", "registry.json"):
        p = ROOT / rel
        if p.is_file():
            shutil.copy2(p, dest / rel)
            items.append((rel, p.stat().st_size))
    st = WS / ".opencode" / "state"
    if st.is_dir():
        shutil.copytree(st, dest / "state")
        items.append((".opencode/state/", size_of(st)))

    # 空归档要报警：这次清空就是这么发生的
    bus = dest / "projects" / (pid or "") / "bus"
    n_events = 0
    ev = bus / "events.jsonl"
    if ev.is_file():
        n_events = sum(1 for _ in ev.open("r", encoding="utf-8", errors="ignore"))

    readme = [
        f"# 运行时归档 · {pid or '(全部)'} · {stamp}", "",
        "## 内容", "",
        "| 项 | 字节 |", "|---|---|",
    ]
    for rel, n in items:
        readme.append(f"| `{rel}` | {n} |")
    readme += [
        "", "## 还原方式", "",
        "把上表内容按原路径放回工作区：", "",
        "```",
        "projects/<pid>/      →  runtime/projects/<pid>/",
        "projects.json        →  runtime/projects.json",
        "registry.json        →  runtime/registry.json",
        "state/               →  .opencode/state/",
        "```", "",
        "放回后 `python runtime/board.py status` 应能认出项目；",
        "`python runtime/cli.py projects` 应列出它。", "",
        "## 事件流统计", "",
        f"- `bus/events.jsonl` 行数：**{n_events}**",
    ]
    if n_events == 0:
        readme += ["", "> ⚠ **本次归档里没有事件流。** 说明归档前运行时已被清空，",
                   "> 或者归档跑在一次全新初始化的项目上。",
                   "> 这种情况下「缺陷发现阶段」「返修率」「token 归因」全部算不出来——",
                   "> **打包前必须先跑一次归档，而不是打包后补。**"]
    (dest / "RESTORE.md").write_text("\n".join(readme), encoding="utf-8")

    print(f"[archive] 归档目录：{dest}")
    for rel, n in items:
        print(f"          {rel:28} {n} 字节")
    print(f"          bus/events.jsonl 行数：{n_events}")
    if n_events == 0:
        print("[archive] ⚠ 事件流为 0 行 —— 该归档无法支撑返修率/token 归因。"
              "若这不是预期，说明运行时数据在归档前已被清空。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
