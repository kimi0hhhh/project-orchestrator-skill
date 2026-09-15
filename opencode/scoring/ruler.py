"""尺子（Scoring Ruler）· v1

用途：给多 agent 交付流程打两个分——
  1) 积木分：每条「检查积木」能不能抓到历史缺陷（红/绿）
  2) 项目分：这次交付本身好不好（另见 project_score.py）

设计原则（三条，来自 FundLens 的真实教训）：
  · 分数由脚本算，不由子 agent 自填（PM-D1 证明自报全绿可以是假的）
  · 判据是「缺陷注入后必须红」（没有红过的检查等于没写过）
  · 每块积木单独记账，不合成加权总分（合成会掩盖是哪一块坏了）

用法：
    python scoring/ruler.py               # 跑全部检查，输出积分表
    python scoring/ruler.py --json        # 机器可读
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent

# ── 项目配置：换项目只改这一段 ──────────────────────────────────
CONFIG = {
    # ★ 工件根目录是**项目约定**，不是框架常量。缺省 `docs/`（框架全家族一致）；
    #   例：某交付包把工件放在 `04_工程文档/`，那里就改成那个名字，
    #   E03 与 project_score.py 都跟着它走。
    #   踩坑记录：曾把这个项目专属目录名硬编码进通用框架，导致通用包对别的项目失效。
    "artifact_root": "docs",
    "src_root": "src",
    # 待产出工件：S7 的输出，此刻还没生成是**正常**的，不该判死引用。
    # 只列**确知会被产出**的（对应 gate-rules S7 就绪清单第 5/6 项）；
    # 别往里塞正常引用 —— 那是把检查关掉，不是修检查。
    "forward_refs": ["retro.md", "20-closeout.md"],
    "contract": "docs/01-architecture/09-api-contract.md",
    "app_py": "src/app.py",
    "holdings_py": "src/holdings.py",
    "fund_predict_py": "src/fund_predict.py",
    "js_dir": "src/static/js",
    "ref_row_iface": "/api/holdings",   # 字段基准接口
}


def read(rel):
    p = ROOT / rel
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8", errors="ignore")


def norm_iface(s):
    """归一化接口名。

    /api/fund/{code}       -> /api/fund/*
    /api/fund/{code}/stocks-> /api/fund/*/stocks
    /api/fund/（前缀路由）  -> /api/fund/*
    只做这两件事，不做贪婪截断——截断会把 /api/fund/*/stocks 误并成 /api/fund/*。
    """
    s = s.split("?")[0].strip().rstrip("　 ")
    s = re.sub(r"\{[^}]*\}", "*", s)
    if s.endswith("/"):
        s += "*"
    return s


# ── 抽取器 ─────────────────────────────────────────────────────
def contract_interfaces(md):
    """契约里声明的接口清单（含 §3 新增节）。"""
    got = set()
    for line in md.splitlines():
        if not line.strip().startswith("#"):
            continue
        if "不做" in line or "不设" in line:
            continue
        for m in re.finditer(r"\b(GET|POST)\s+(/api/[A-Za-z0-9_/{}\.\-]+)", line):
            got.add(norm_iface(m.group(2)))
    return got


def impl_routes(py):
    """实现里的路由清单：path == "/api/x"、path.startswith("/api/x")，
    以及同一行里 startswith + endswith 组合出的 /api/x/*/y。"""
    got = set()
    for m in re.finditer(r"""path\s*==\s*['"](/api/[A-Za-z0-9_/.{}\-]*?)['"]""", py):
        got.add(norm_iface(m.group(1)))
    for m in re.finditer(r"""path\.startswith\(\s*['"](/api/[A-Za-z0-9_/.{}\-]*?)['"]""", py):
        base = norm_iface(m.group(1))
        line_end = py.find("\n", m.end())
        tail = py[m.end(): line_end if line_end > 0 else len(py)]
        endm = re.search(r"""path\.endswith\(\s*['"]([^'"]+)['"]""", tail)
        if endm:
            got.add(base.rstrip("/*") + "/*/" + endm.group(1).lstrip("/"))
        else:
            got.add(base)
    return got


def func_body(src, name):
    """取函数体（从 def name( 到下一个行首 def）。"""
    m = re.search(r"^def\s+" + re.escape(name) + r"\s*\(", src, re.M)
    if not m:
        return ""
    nxt = re.search(r"^def\s+\w+", src[m.end():], re.M)
    return src[m.start(): m.end() + (nxt.start() if nxt else len(src))]


def return_keys(src, name):
    """函数体里的键名：既含字面量 "key": ，也含赋值 r["key"] = 。"""
    body = func_body(src, name)
    keys = set(re.findall(r'"([a-z_][a-z0-9_]*)"\s*:', body))
    keys |= set(re.findall(r"""\[\s*['"]([a-z_][a-z0-9_]*)['"]\s*\]\s*=[^=]""", body))
    return keys


def contract_table_fields(md, iface):
    """契约某接口段落里的字段表第一列。返回 (行级字段, 顶层字段)。

    契约里 `holdings[].code` 是行级字段；`ok` / `total_market_value` 是顶层。
    两者实现位置不同，必须分开比，否则会把结构差异误判成缺字段。
    """
    lines = md.splitlines()
    start, buf = None, []
    for i, l in enumerate(lines):
        if l.strip().startswith("#") and iface in l and start is None:
            start = i
            continue
        if start is not None:
            if l.strip().startswith("#"):
                break
            buf.append(l)
    row, top = set(), set()
    for l in buf:
        if not l.strip().startswith("|"):
            continue
        col0 = l.split("|")[1].strip() if l.count("|") >= 2 else ""
        if not col0 or col0 in ("字段", "---") or set(col0) <= set("-: "):
            continue
        is_row = col0.startswith("holdings[].")
        col0 = re.sub(r"^holdings\[\]\.", "", col0)
        for part in re.split(r"\s*/\s*", col0):
            part = part.strip()
            if re.fullmatch(r"[a-z_][a-z0-9_]*", part):
                (row if is_row else top).add(part)
    return row, top


JS_KEYWORDS = set("""if for while switch catch return function typeof new delete void in of do else try
throw case break continue var let const class extends super this await async yield import export default
parseInt parseFloat Number String Boolean Array Object Math JSON Date Promise Set Map RegExp Error
isNaN isFinite encodeURIComponent decodeURIComponent setTimeout setInterval clearTimeout clearInterval
fetch alert confirm prompt requestAnimationFrame addEventListener querySelector querySelectorAll
Symbol WeakMap BigInt console document window""".split())

# CSS/SVG 函数：出现在模板字符串里，不是 JS 调用
CSS_FUNCS = set("""rgba rgb hsl hsla url calc var translate translateX translateY rotate scale
cubic-bezier linear-gradient radial-gradient attr env min max clamp blur saturate drop-shadow
matrix rotateX rotateY skew perspective steps repeat""".split())


BROWSER_GLOBALS = set("""AbortController AbortSignal Blob CustomEvent Event EventTarget FormData
Headers Request Response URL URLSearchParams TextEncoder TextDecoder Worker WebSocket
IntersectionObserver MutationObserver ResizeObserver FileReader Image Audio Notification
localStorage sessionStorage indexedDB history location navigator screen performance crypto
getComputedStyle matchMedia requestAnimationFrame cancelAnimationFrame queueMicrotask
structuredClone atob btoa reportError confirm alert prompt open close focus print scrollTo""".split())


def strip_js_comments(js):
    out, i, n = [], 0, len(js)
    while i < n:
        if js.startswith("//", i):
            j = js.find("\n", i)
            i = n if j < 0 else j
        elif js.startswith("/*", i):
            j = js.find("*/", i)
            i = n if j < 0 else j + 2
        elif js[i] in "'\"`":
            q = js[i]
            j = i + 1
            while j < n:
                if js[j] == "\\":
                    j += 2
                    continue
                if js[j] == q:
                    break
                j += 1
            out.append(js[i:j + 1])
            i = j + 1
        else:
            out.append(js[i])
            i += 1
    return "".join(out)


def js_undefined_calls(js):
    """找模块内被裸调用、但既未在本文件定义、也不在白名单里的标识符。

    排除：注释、字符串、方法定义（NAME(...) {）、函数参数、关键字、
    浏览器内置、`new X()` 构造、以及首字母大写者（外部类/全局）。
    这正是 PM-D1 的形状：crud.openEdit 被写成裸 openEdit。
    """
    src = strip_js_comments(js)
    defined = set(re.findall(r"\bfunction\s+([A-Za-z_$][\w$]*)", src))
    defined |= set(re.findall(r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)", src))
    defined |= set(re.findall(r"\bclass\s+([A-Za-z_$][\w$]*)", src))
    imported = set()
    for m in re.finditer(r"\bimport\s+\{([^}]*)\}\s+from", src):
        imported |= {x.strip().split(" as ")[-1].strip() for x in m.group(1).split(",")}
    # 注意：**不**把对象方法简写（`openEdit(code) {`）算作「已定义」。
    # 它是 crud 对象的属性，不是模块作用域的名字——裸调它一样会 ReferenceError。
    # 这正是 PM-D1 的形状，也是这条检查存在的理由。
    # 函数参数：function f(a, b) / (a, b) => / const f = (a, b) =>
    params = set()
    for m in re.finditer(r"\bfunction\s*[A-Za-z_$\w]*\s*\(([^)]*)\)", src):
        params |= {p.strip().split("=")[0].strip() for p in m.group(1).split(",")}
    for m in re.finditer(r"\(([^)]*)\)\s*=>", src):
        params |= {p.strip().split("=")[0].strip() for p in m.group(1).split(",")}
    params = {p for p in params if re.fullmatch(r"[A-Za-z_$][\w$]*", p)}

    bad = []
    for m in re.finditer(r"(?<![\w.$])([A-Za-z_$][\w$]*)\s*\(", src):
        name = m.group(1)
        if (name in JS_KEYWORDS or name in defined or name in imported
                or name in params or name in BROWSER_GLOBALS
                or name in CSS_FUNCS or name[:1].isupper()):
            continue
        if re.search(r"\bnew\s+$", src[:m.start()]):
            continue
        tail = src[m.end():m.end() + 220]
        if re.match(r"[^)]*\)\s*\{", tail):      # 是定义不是调用
            continue
        line = js[:m.start()].count("\n") + 1
        bad.append((line, name))
    return bad


def silent_excepts(py_src, fname):
    """找 except 分支吞掉异常：except ...: pass 或 体只有 pass。"""
    bad = []
    lines = py_src.splitlines()
    for i, l in enumerate(lines):
        if not re.match(r"\s*except\b", l):
            continue
        if re.search(r":\s*pass\s*$", l):
            bad.append((i + 1, l.strip()))
            continue
        for j in range(i + 1, min(i + 3, len(lines))):
            s = lines[j].strip()
            if not s or s.startswith("#"):
                continue
            if s == "pass":
                bad.append((j + 1, l.strip() + " → pass"))
            break
    return [(fname, ln, txt) for ln, txt in bad]


GUARD_RE = re.compile(
    r"or\s+0"                          # x or 0
    r"|if\s*\(?\s*[\w\[\]\"'\.]+\s+and\s"  # if (a and b) else / if a and b else
    r"|if\s*\(?\s*\w+\s+else"          # if total_mv else
    r"|\bif\s+not\s"                   # if not x
    r"|is\s+not\s+None"
)

OPT_OUT = "ruler-ok"


def unsafe_divs(py_src, fname):
    """可能 None 的字段参与除法且无防护（SHOULD-4 的形状）。

    认三种防护：`or 0`、行内 if/else 条件、上一行的 None 判断。
    人工确认无害时可在该行写 `# ruler-ok: 理由` 主动豁免（豁免必须写理由，
    否则等于把检查关掉——那是门禁放水的代码版）。
    """
    bad = []
    lines = py_src.splitlines()
    for i, l in enumerate(lines):
        if not re.search(r"/\s*total", l):
            continue
        if OPT_OUT in l:
            continue
        ctx = l + (lines[i - 1] if i else "")
        if GUARD_RE.search(ctx):
            continue
        if re.search(r'\w+\[["\'][a-z_]+["\']\]\s*/', l) or re.search(r"\b\w*market_value\s*/", l):
            bad.append((fname, i + 1, l.strip()[:110]))
    return bad


def json_loads_unguarded(py_src, fname):
    """json.loads/json.load 所在函数必须有 try 或显式错误分支。"""
    bad = []
    lines = py_src.splitlines()
    for m in re.finditer(r"json\.loads?\s*\(", py_src):
        line = py_src[:m.start()].count("\n") + 1
        if OPT_OUT in lines[line - 1]:
            continue
        head = py_src[:m.start()]
        fstart = head.rfind("\ndef ")
        body = py_src[fstart: m.end() + 1500] if fstart >= 0 else py_src[:m.end()]
        body_upto = py_src[fstart:m.start()]
        if "try" in body_upto:
            continue
        fnm = re.search(r"def\s+(\w+)", body)
        fn = fnm.group(1) if fnm else "?"
        bad.append((fname, line, f"函数 {fn} 内 json.load 无 try 防护"))
    return bad


# ── 检查清单：每块积木一个函数，返回 (ok, 详情) ────────────────────
def run_checks():
    # 只读「值是文件路径」的那些键；artifact_root / forward_refs 是配置不是路径，
    # 混进来会 TypeError（实测踩坑：加 forward_refs 后整支检查崩掉）。
    PATHLESS = {"js_dir", "artifact_root", "src_root", "forward_refs"}
    C = {k: ("" if k in PATHLESS else read(v)) for k, v in CONFIG.items()}
    md = C["contract"]
    results = []

    # E01 契约接口穷举 ────────────────────────────────
    ci, ir = contract_interfaces(md), impl_routes(C["app_py"])
    missing = sorted(ci - ir)
    results.append(dict(
        id="E01", block="E 穷举对照",
        name="契约声明的接口，实现里都必须有路由",
        ok=(len(missing) == 0),
        detail=f"契约 {len(ci)} 个 / 实现 {len(ir)} 个" + (f"；缺：{missing}" if missing else "；零缺项"),
    ))

    # E02 契约字段穷举（两个页面必须逐字段对齐同一基准）────
    row_fields, top_fields = contract_table_fields(md, CONFIG["ref_row_iface"])
    h = C["holdings_py"]
    list_keys = return_keys(h, "_build_rows")
    single_keys = return_keys(h, "estimate_fund")
    envelope = h + C["app_py"]          # 顶层字段由 handler 组装，可能落在 app.py
    gap_list = sorted(row_fields - list_keys)
    gap_single = sorted(row_fields - single_keys)
    gap_top = sorted(f for f in top_fields if not re.search(r'"%s"' % re.escape(f), envelope)
                     and not re.search(r'["\']%s["\']' % re.escape(f), envelope))
    ok = not gap_list and not gap_single and not gap_top
    results.append(dict(
        id="E02", block="E 穷举对照",
        name=f"列表页与单基金页都逐字段对齐 {CONFIG['ref_row_iface']} 契约表",
        ok=ok,
        detail=(f"行级基准 {len(row_fields)} 个；" +
                ("两处零缺项" if ok else
                 f"列表页缺 {gap_list}；单基金页缺 {gap_single}；顶层缺 {gap_top}")),
    ))

    # E03 协议/契约里的工件路径必须可解析 ────────────────
    # 抓「路径漂移」：文档里写 `某根/xxx`，而那个根目录并不存在。
    # 实测踩坑：14 处 `docs/` 引用而 `docs/` 目录不存在 → 唤醒流程第一步就断、
    # dispatch pre-flight 拒绝出 prompt。这类漂移靠人眼看不住，只能靠机器查。
    #
    # 判定口径：只要引用的根**长得像工件根**（配置值 / 缺省 `docs` / `数字_中文` 形态），
    # 而整条路径在磁盘上不存在，就算死引用。
    # 反过来说：工件根改名后忘了同步文档 → 红；文档写了个不存在的根 → 也红。
    bad_e03 = []
    art_root = CONFIG.get("artifact_root", "docs")
    root_alt = r"(?:%s|docs|\d\d_[^/`\s]+)" % re.escape(art_root)
    ref_re = re.compile(r"`((%s)/[^`\s]+?\.(?:md|html|json|py|js))`" % root_alt)
    doc_dirs = [".opencode/protocols", ".opencode/agents",
                ".opencode/commands", ".opencode/skills/project-orchestrator"]
    for dd in doc_dirs:
        d = ROOT / dd
        for f in sorted(d.glob("*.md")):
            for line_no, line in enumerate(
                    f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                for m in ref_re.finditer(line):
                    ref, ref_root = m.group(1), m.group(2)
                    if (ROOT / ref).exists():
                        continue
                    if os.path.basename(ref) in CONFIG.get("forward_refs", []):
                        continue          # 待产出工件（S7 输出），尚未生成属正常
                    bad_e03.append(
                        f"{f.name}:{line_no} 死引用 `{ref}`（`{ref_root}/` 不存在）")
    results.append(dict(
        id="E03", block="E 穷举对照",
        name="协议与契约里引用的工件路径必须真的能解析",
        ok=(not bad_e03),
        detail=("零死引用" if not bad_e03 else
                f"{len(bad_e03)} 处：" + "；".join(bad_e03[:4])),
    ))

    # B01 JS 未定义标识符 ──────────────────────────────
    jsdir = ROOT / CONFIG["js_dir"]
    bad_b01 = []
    js_files = sorted(jsdir.glob("*.js")) if jsdir.is_dir() else []
    for f in js_files:
        for line, name in js_undefined_calls(f.read_text(encoding="utf-8", errors="ignore")):
            bad_b01.append(f"{f.name}:{line} 调用了未定义的 `{name}`")
    results.append(dict(
        id="B01", block="B 交互可点性",
        name="前端不得调用未定义的标识符（点了没反应的第一大来源）",
        ok=(not bad_b01),
        detail=(f"扫描 {len(js_files)} 个 JS 文件；" + ("零未定义调用" if not bad_b01 else f"{len(bad_b01)} 处：" + "；".join(bad_b01[:4]))),
    ))

    # B02 隐私打码不得绕过 ─────────────────────────────
    # 只抓「把原始值插进金额位」：模板里出现 ¥${...} 且没走 fmtMoney。
    # 已打码的字面量（¥****）与纯文案不算。
    bad_b02 = []
    for f in js_files:
        src = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"`[^`]*`", src):
            seg = m.group(0)
            if not re.search(r"¥\s*\$\{", seg):
                continue
            if "fmtMoney" in seg:
                continue
            line = src[:m.start()].count("\n") + 1
            bad_b02.append(f"{f.name}:{line} 模板里裸拼金额（未走 fmtMoney）")
    results.append(dict(
        id="B02", block="B 交互可点性",
        name="金额必须走统一格式化函数（否则绕过隐私打码）",
        ok=(not bad_b02),
        detail=("零裸拼金额" if not bad_b02 else f"{len(bad_b02)} 处：" + "；".join(bad_b02[:4])),
    ))

    # X01 静默吞异常 ───────────────────────────────────
    bad_x01 = []
    for rel in (CONFIG["fund_predict_py"], CONFIG["holdings_py"], CONFIG["app_py"]):
        p = ROOT / rel
        if p.is_file():
            bad_x01 += silent_excepts(p.read_text(encoding="utf-8", errors="ignore"), p.name)
    results.append(dict(
        id="X01", block="X 注入测试",
        name="异常不得被静默吞掉（失败必须可控可感知）",
        ok=(not bad_x01),
        detail=("零静默吞异常" if not bad_x01 else f"{len(bad_x01)} 处：" +
                "；".join(f"{a}:{b} {c[:60]}" for a, b, c in bad_x01[:4])),
    ))

    # G01 None 参与除法的防护 ──────────────────────────
    bad_g01 = []
    p = ROOT / CONFIG["holdings_py"]
    if p.is_file():
        bad_g01 += unsafe_divs(p.read_text(encoding="utf-8", errors="ignore"), p.name)
    results.append(dict(
        id="G01", block="G 不变量断言",
        name="可能为 None 的字段参与除法必须先防护",
        ok=(not bad_g01),
        detail=("零未防除 None" if not bad_g01 else f"{len(bad_g01)} 处：" +
                "；".join(f"{a}:{b} {c[:70]}" for a, b, c in bad_g01[:4])),
    ))

    # G02 json 加载必须显式兜底 ────────────────────────
    bad_g02 = []
    for rel in (CONFIG["holdings_py"], CONFIG["app_py"]):
        p = ROOT / rel
        if p.is_file():
            bad_g02 += json_loads_unguarded(p.read_text(encoding="utf-8", errors="ignore"), p.name)
    results.append(dict(
        id="G02", block="G 不变量断言",
        name="json.load 所在函数必须有 try 或显式错误分支",
        ok=(not bad_g02),
        detail=("零无防护加载" if not bad_g02 else f"{len(bad_g02)} 处：" +
                "；".join(f"{a}:{b} {c}" for a, b, c in bad_g02[:4])),
    ))
    return results


def score_block(results, defects):
    """按题库算覆盖：某条缺陷只要有积木覆盖，就算「尺子量得到」。

    · 覆盖 + 检查绿  = 缺陷已修，尺子确认（这条最理想）
    · 覆盖 + 检查红  = 缺陷仍在，尺子抓到了（ruler 的价值在这里）
    · 无覆盖         = 尺子自己的盲区，要补新积木
    """
    by_id = {r["id"]: r for r in results}
    confirmed, detected, uncovered = [], [], []
    for d in defects:
        cid = d.get("check")
        if not cid or cid not in by_id:
            uncovered.append(f"{d['id']}  {d['desc'][:44]}")
            continue
        chk = by_id[cid]
        entry = f"{d['id']}（{cid}）"
        if chk["ok"]:
            confirmed.append(entry)
        else:
            detected.append(entry + f"  ← {chk['detail'][:70]}")
    return confirmed, detected, uncovered


def main():
    ap = argparse.ArgumentParser(prog="ruler")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    results = run_checks()
    dpath = Path(__file__).resolve().parent / "defects.json"
    defects = json.loads(dpath.read_text(encoding="utf-8"))["defects"]
    confirmed, detected, uncovered = score_block(results, defects)

    if a.json:
        print(json.dumps(dict(checks=results, confirmed=confirmed, detected=detected,
                              uncovered=uncovered), ensure_ascii=False, indent=2))
        return

    print("=" * 78)
    print("积木分 · 检查执行结果（绿 = 合格，红 = 检出问题）")
    print("=" * 78)
    for r in results:
        print(f"[{'绿' if r['ok'] else '红'}] {r['id']}  {r['block']:<10} {r['name']}")
        print(f"        {r['detail']}")
    green = sum(1 for r in results if r["ok"])
    print()
    print(f"检查通过 {green}/{len(results)}")
    print()
    print("=" * 78)
    print(f"积木分 · 题库覆盖（题库 = 该项目真实发生过的 {len(defects)} 条缺陷）")
    print("=" * 78)
    print(f"有积木覆盖 {len(confirmed) + len(detected)}/{len(defects)}"
          f"   其中：{len(confirmed)} 条已确认修复 / {len(detected)} 条被检出仍在")
    for x in confirmed:
        print("   ✓ 已确认 " + x)
    for x in detected:
        print("   ✗ 检出   " + x)
    if uncovered:
        print(f"无积木覆盖 {len(uncovered)}  ← 尺子的盲区，要补新积木")
        for x in uncovered:
            print("   · " + x)


if __name__ == "__main__":
    main()
