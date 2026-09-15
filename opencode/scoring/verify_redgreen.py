"""红绿验证：证明这些检查「有牙」。

一个检查如果在缺陷存在时不会变红，它就是装饰品。
本脚本把两条已修复的历史 P0/BLOCK 缺陷**注入回一份临时副本**，再跑检查：

    BLOCK-1  → E02 应变红
    PM-D1    → B01 应变红

真仓库文件一个字节都不动（全程在临时目录的副本上操作）。
用法：python scoring/verify_redgreen.py
"""
import re
import shutil
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import ruler  # noqa: E402

cases = [
    dict(
        defect="BLOCK-1",
        check="E02",
        target="src/holdings.py",
        desc="删掉 estimate_fund 返回里的 weight 键（还原 BLOCK-1）",
        inject=lambda s: s.replace('        "weight": weight,\n', "", 1),
        expect="weight",
    ),
    dict(
        defect="PM-D1",
        check="B01",
        target="src/static/js/tab-holdings.js",
        desc="把 crud.openEdit 改回裸 openEdit（还原 PM-D1）",
        inject=lambda s: s.replace("crud.openEdit(code)", "openEdit(code)", 1),
        expect="openEdit",
    ),
    dict(
        defect="路径漂移（工件根写错）",
        check="E03",
        target=".opencode/commands/takeover.md",
        desc="把正确工件根改成不存在的 `docs/`（还原当初那 14 处漂移的形状）",
        inject=lambda s: s.replace("docs/PROJECT_BRIEF.md",
                                   "04_工程文档/PROJECT_BRIEF.md", 1),
        expect="docs/",
    ),
]


def run_checks_in(base: Path):
    """把 ruler 的 ROOT 指到副本，跑一遍检查。"""
    old = ruler.ROOT
    ruler.ROOT = base
    try:
        return {r["id"]: r for r in ruler.run_checks()}
    finally:
        ruler.ROOT = old


def main():
    print("=" * 78)
    print("基线：对当前源码跑检查（修复后的状态）")
    print("=" * 78)
    base = run_checks_in(ROOT)
    for cid in ("E01", "E02", "B01", "B02", "X01", "G01", "G02"):
        r = base[cid]
        print(f"  [{'绿' if r['ok'] else '红'}] {cid}")
    print()

    passed_all = True
    for c in cases:
        tmp = Path(tempfile.mkdtemp(prefix="ruler_rg_"))
        try:
            for sub in ("src", "docs", ".opencode"):
                src = ROOT / sub
                if src.exists():
                    shutil.copytree(src, tmp / sub,
                                    ignore=shutil.ignore_patterns("node_modules", "__pycache__"))
            f = tmp / c["target"]
            src = f.read_text(encoding="utf-8")
            patched = c["inject"](src)
            changed = patched != src

            print("=" * 78)
            print(f"注入 {c['defect']}：{c['desc']}")
            print(f"  文件 {c['target']} 是否真的改了：{'是' if changed else '否 ← 注入失败，用例作废'}")
            f.write_text(patched, encoding="utf-8")

            res = run_checks_in(tmp)
            r = res[c["check"]]
            baseline_ok = base[c["check"]]["ok"]
            verdict = "变红 ✔ 检查有牙" if (baseline_ok and not r["ok"]) else \
                      "没变红 ✘ 检查是装饰品" if baseline_ok else \
                      "基线已是红，无法判定"
            print(f"  基线 {c['check']}：绿   注入后：{'红' if not r['ok'] else '绿'}")
            print(f"  判定：{verdict}")
            print(f"  检出详情：{r['detail'][:150]}")
            if "变红" not in verdict:
                passed_all = False
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=" * 78)
    n = len(cases)
    print("结论：" + (f"{n} 条检查都能在缺陷存在时变红 —— 尺子有牙。"
                     if passed_all else "有检查没变红 —— 那些检查需要重写。"))
    print("=" * 78)
    return 0 if passed_all else 1


if __name__ == "__main__":
    sys.exit(main())
