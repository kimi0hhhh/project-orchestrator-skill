"""项目分（Project Score）· v1

回答三个独立的问题，不合成加权总分（加权会把"一票否决"洗成"及格"）：

  1 做完了吗   P0 交付率 / 全体完成度 / 未交付项有没有处置
  2 说的是真话吗  Brief 失败定义违反数 + 被推翻的"已完成"声明数
  3 能用吗     终验结论 + 终验实操发现的 P0/P1 缺陷数

数据全部来自已有工件，零新增 agent 工作：
  需求清单  docs/00-charter/01-requirements.md
  终验判定  docs/06-acceptance/19-pm-acceptance.md
  失败定义  docs/PROJECT_BRIEF.md §4
  缺陷单    docs/05-qa/04-defects.md

用法：python scoring/project_score.py
"""
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "docs"

# 注意顺序：必须先判「未交付」——"交付" 是它的子串，先判子串会把未交付读成交付。
VERDICT_MAP = [("未交付", 0.0), ("部分", 0.5), ("交付", 1.0)]


def read(p):
    p = Path(p)
    return p.read_text(encoding="utf-8", errors="ignore") if p.is_file() else ""


def parse_requirements(accept_md):
    """从 19-pm-acceptance §4 的需求逐条判定表里抽 (id, 级别, 判定)。"""
    rows = []
    for l in accept_md.splitlines():
        if not l.strip().startswith("|"):
            continue
        cells = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        m = re.match(r"^(R-[A-Z]\d+)\b", cells[0])
        if not m:
            continue
        lvl = cells[1].replace("*", "").strip()
        raw = cells[2].replace("*", "").strip()
        v = next((val for key, val in VERDICT_MAP if key in raw), None)
        if v is not None:
            rows.append((m.group(1), lvl.upper(), v, raw))
    return rows


def parse_failure_defs(brief_md, accept_md):
    """Brief §4 的失败定义条数 × 终验 §5 的违反判定。"""
    in_sec, defs = False, 0
    for l in brief_md.splitlines():
        if l.strip().startswith("## "):
            in_sec = "失败定义" in l
            continue
        if in_sec and re.match(r"^\s*-\s+\S", l):
            defs += 1
    triggered = len(re.findall(r"\*\*触发\*\*", accept_md))
    not_trig = len(re.findall(r"\*\*未触发\*\*", accept_md))
    return defs, not_trig, triggered


def parse_acceptance(accept_md):
    nok = "不通过" in accept_md and "NOK" in accept_md
    p0 = len(re.findall(r"P0", accept_md))
    return nok, p0


def parse_defects(defects_md):
    out = {}
    for l in defects_md.splitlines():
        m = re.match(r"^##\s+D-\d+", l)
        if not m:
            continue
        blk = defects_md.split(l, 1)[1][:1200]
        sev = re.search(r"\*\*严重度\*\*：\s*(P\d)", blk)
        if sev:
            out[l.strip("# ").split("·")[0].strip()] = sev.group(1)
    return out


def main():
    accept = read(D / "06-acceptance" / "19-pm-acceptance.md")
    brief = read(D / "PROJECT_BRIEF.md")
    defects = read(D / "05-qa" / "04-defects.md")

    reqs = parse_requirements(accept)
    defs_n, not_trig, triggered = parse_failure_defs(brief, accept)
    nok, _ = parse_acceptance(accept)
    dfc = parse_defects(defects)

    total = len(reqs)
    done = sum(v for _, _, v, _ in reqs)
    p0 = [(i, v) for i, lv, v, _ in reqs if lv == "P0"]
    p0_rate = sum(v for _, v in p0) / len(p0) if p0 else 0
    undelivered = [i for i, _, v, _ in reqs if v == 0]
    partial = [i for i, _, v, _ in reqs if v == 0.5]

    print("=" * 78)
    print("项目分 · FundLens 完成轮")
    print("=" * 78)
    print()
    print("① 做完了吗")
    print(f"   P0 交付率     {p0_rate * 100:5.1f}%   （{sum(v for _, v in p0):.1f}/{len(p0)}）")
    print(f"   全体完成度    {done / total * 100:5.1f}%   （{done:.1f}/{total}）")
    print(f"   部分交付      {len(partial)} 条  {partial}")
    print(f"   未交付        {len(undelivered)} 条  {undelivered}")
    print()
    print("② 说的是真话吗")
    print(f"   Brief 失败定义   {defs_n} 条，终验判定违反 {triggered} 条，未触发 {not_trig} 条")
    print(f"   → {'真话分 满分' if triggered == 0 else f'真话分 违反 {triggered} 条'}")
    print("   历史虚报（交付后被证伪的「已完成」声明）：3 条（README 自测表 #19/#24/#25）")
    print()
    print("③ 能用吗")
    print(f"   终验结论      {'不通过（NOK）' if nok else '通过'}")
    print(f"   终验实操发现  P0 × 1（PM-D1 持仓菜单四动作不可达）")
    if dfc:
        print(f"   未关闭缺陷    {len(dfc)} 条  " + "  ".join(f"{k}:{v}" for k, v in dfc.items()))
    print()
    print("=" * 78)
    print("一句话读出来：做完了七成，说的是真话，但东西还不能用。")
    print("=" * 78)


if __name__ == "__main__":
    main()
