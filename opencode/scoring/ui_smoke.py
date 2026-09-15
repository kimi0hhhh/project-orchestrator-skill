"""UI 点击冒烟（运行时版 B01）· v1

## 为什么需要它
`ruler.py` 的 B01 是**静态**检查（扫未定义标识符）。静态看不到：
  · `obj.method` 里 obj 是 undefined
  · 作用域遮蔽、条件分支里的裸调用
  · 依赖运行时的 DOM 结构才暴露的问题

PM-D1 就是这样漏过去的：静态扫不出，测试组又只调接口没点界面，
最后是**产品经理在 S6 亲手点**才发现的（代价：一次终验 NOK + S7 未达成）。

本脚本补上运行时那一半：**真开浏览器、真点一遍、断言零 JS 报错。**

## 怎么跑
    python scoring/ui_smoke.py                # 对缺省源码根（src/）跑
    python scoring/ui_smoke.py --src <目录>   # 对指定源码目录跑（红绿验证用）

## 做法（零依赖，只用系统已装的 Chrome/Edge + 标准库）
1. 把 `static/` 复制到临时目录（**不动项目里任何一个字节**）
2. 注入 fetch 桩（免后端）+ 点击跑手，产出 `__smoke.html`
3. `python -m http.server` 起本地服务（ES module 在 file:// 下会被 CORS 拦）
4. Chrome headless `--dump-dom` 跑完，从 DOM 里读结果
5. 清理临时目录

## 判据（这一条必须有牙）
**注入 PM-D1（`crud.openEdit` → 裸 `openEdit`）时，本脚本必须报 FAIL。**
见 `scoring/verify_redgreen.py`。

退出码：0 无 JS 报错 / 2 有报错 / 3 环境不可用（无浏览器）/ 1 其他
"""
import argparse
import http.server
import json
import os
import re
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

BROWSERS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]

# 证据夹具：把「录制下来的真实 API 响应」喂给前端。
#
# ★ 为什么必须用夹具而不是返回空/报错：
#   第一版桩返回 `{ok:false}` → 前端渲染**错误态** → 持仓表格根本没渲染 →
#   `···` 菜单按钮压根不存在 → 点了 14 次就没了，覆盖率形同虚设（实测）。
#   必须让界面渲染出**真实结构**，才点得到真正会坏的东西。
EVIDENCE_DIR = ROOT / "docs" / "05-qa" / "evidence"
FIXTURE_MAP = {
    "/api/holdings": "h01_holdings.json",
    "/api/portfolio": "x04_portfolio.json",
    "/api/predict": "b2_predict.json",
    "/api/review": "b4_review.json",
    "/api/timeline": "b4_timeline_stats.json",
    "/api/coverage": "cov01_coverage.json",
    "/api/tasks": "task01_info.json",
    "/api/fund/": "h04_fund_018957.json",
}


def load_fixtures():
    """读证据夹具；返回 (path->对象字典, 命中数, 总数)。"""
    got = {}
    for ep, fn in FIXTURE_MAP.items():
        p = EVIDENCE_DIR / fn
        if p.is_file():
            try:
                got[ep] = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                pass
    return got, len(got), len(FIXTURE_MAP)


def build_stub(fixtures):
    return """<script>
window.__SMOKE_FIX = %s;
window.__smokeErrors = [];
window.addEventListener('error', function (e) {
  window.__smokeErrors.push(String((e && (e.message || e.error)) || 'error'));
});
window.addEventListener('unhandledrejection', function (e) {
  window.__smokeErrors.push('unhandledrejection: ' + String(e && e.reason));
});
(function () {
  function resp(o) {
    return { ok: true, status: 200,
             json: async function () { return o; },
             text: async function () { return JSON.stringify(o); } };
  }
  window.fetch = async function (url) {
    var path = String(url || '').split('?')[0];
    var K = window.__SMOKE_FIX;
    for (var k in K) {
      if (path === k || path.indexOf(k) === 0) return resp(K[k]);
    }
    return resp({ ok: false, error_code: 'SMOKE_NO_FIXTURE', message: '该接口无夹具' });
  };
})();
</script>
""" % json.dumps(fixtures, ensure_ascii=False)

# 注入到 </body> 前：多轮点击 + 写结果
#
# ★ 只点「用户当下点得到」的元素。这条是防假阳性的关键：
#   关闭的 <dialog> 里的按钮、隐藏 tab 的内容都在 DOM 里，但用户碰不到；
#   点它们只会暴露"模块还没加载"这类假问题（实测：第一版报 16 个假阳性，
#   全是 window.__crud 未定义——那是 dialog 里的静态 onclick，模块加载前本就点不到）。
#   用户点不到的按钮坏了，不算缺陷。
RUNNER = """<script>
// ★ 必须等 load 之后再开工：本脚本插在 </body> 之前，而 app.js 是 defer 型模块，
//   两者都在文档末尾 —— 直接跑会赶在 app.js 绑定导航 onclick 之前，
//   于是点导航毫无反应、七页全在 DOM 里却一个都进不去（实测：clicked=7 skipped=675）。
//   load 事件在所有 module 执行完之后才触发，是唯一可靠的起跑线。
window.addEventListener('load', function () { setTimeout(start, 800); });

async function start() {
  var errs = window.__smokeErrors, clicked = 0, skipped = 0, cap = 1200;
  var done = (typeof WeakSet === 'function') ? new WeakSet() : null;
  var sleep = function (ms) { return new Promise(function (r) { setTimeout(r, ms); }); };

  // 导航按钮单独处理，不能混进普通扫描 ——
  // 第一版把导航按钮也标记成"已点"，第二轮起就不再点它，于是永远切不回持仓页，
  // 22 个 `···` 菜单按钮全在 DOM 里却一个都没点到（实测 diagnostic: menu=22/0）。
  var NAV   = 'nav#nav button';
  // 导航与弹出菜单触发器单独处理，普通扫描排除它们，避免重复计
  var SEL_NO_MENU = 'button:not(nav#nav button):not([data-menu]),[role="button"]:not([data-menu])'
                  + ',[onclick]:not([data-menu]),a[href^="#"]';
  // 刚冒出来的东西：弹出菜单项、打开的弹层里的按钮
  var FRESH = '[data-act],[role="menuitem"],dialog[open] button,dialog[open] [onclick]';

  function visible(el) {
    var r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) return false;
    var s = getComputedStyle(el);
    if (s.visibility === 'hidden' || s.display === 'none' || s.pointerEvents === 'none') return false;
    for (var p = el; p; p = p.parentElement) {
      if (p.tagName === 'DIALOG' && !p.open) return false;   // 关着的弹层
      if (p.hasAttribute && p.hasAttribute('hidden')) return false;
    }
    return true;
  }

  function fire(el, force) {
    if (!el || clicked >= cap) return false;
    if (!force && done && done.has(el)) return false;
    if (!visible(el)) { skipped++; return false; }
    if (done) done.add(el);
    try { el.click(); clicked++; return true; }
    catch (e) { errs.push('click 抛错 <' + (el.id || el.tagName) + '>: ' + e.message); return false; }
  }

  function q(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

  var menuOpened = 0, menuItemFired = 0;

  // 弹出菜单单独一套打法：
  //   点开 → 点第 k 项 → 菜单被全局 click 监听关掉 → **必须重新点开**才能点第 k+1 项。
  //   第一版点完第 1 项就以为剩下三项也在列表里，实际上它们已经从 DOM 里移除，
  //   `fire()` 因"不可见"跳过 —— 于是第 3 项「编辑」永远轮不到。
  //   PM-D1 坏掉的正是第 3 项（裸调 openEdit），这就是它一直没被抓到的原因。
  function sweepMenus() {
    var menus = q('[data-menu]');
    for (var m = 0; m < menus.length; m++) {
      for (var k = 0; k < 4; k++) {
        if (!fire(menus[m], true)) break;        // force：允许反复点开同一个按钮
        var items = q(FRESH);
        if (k >= items.length) break;
        menuOpened += (k === 0 ? 1 : 0);
        if (fire(items[k], true)) menuItemFired++;
      }
    }
  }

  function sweep() {
    var list = q(SEL_NO_MENU);
    for (var i = 0; i < list.length; i++) {
      if (!fire(list[i])) continue;
      // 立刻处理「刚冒出来」的元素：弹出菜单/打开弹层的按钮
      // 会在下一次点击时被关掉或遮挡，等下一轮就扫不到了。
      var fresh = q(FRESH);
      for (var j = 0; j < fresh.length; j++) fire(fresh[j]);
    }
    sweepMenus();
  }

  // 逐页巡视：切到每一页 → 扫三遍（让异步渲染落地）→ 下一页
  var navs = q(NAV);
  var pages = 0;
  for (var p = 0; p < (navs.length || 1); p++) {
    if (navs.length) { navs[p].click(); await sleep(450); }
    pages++;
    for (var r = 0; r < 3; r++) { sweep(); await sleep(250); }
  }
  // 回第一页再扫一遍：有些元素只在"切回来"后才出现
  if (navs.length) { navs[0].click(); await sleep(450); sweep(); }

  var uniq = [];
  for (var k = 0; k < errs.length; k++) if (uniq.indexOf(errs[k]) < 0) uniq.push(errs[k]);
  function cnt(sel, needVis) {
    var all = document.querySelectorAll(sel), n = 0;
    for (var i = 0; i < all.length; i++) if (!needVis || visible(all[i])) n++;
    return n;
  }
  var secs = q('section.tab').map(function (s) {
    var r = s.getBoundingClientRect();
    return s.id.replace('tab-', '') + (s.classList.contains('on') ? '*' : '') +
           ':' + Math.round(r.width) + 'x' + Math.round(r.height);
  }).join(',');
  // 注意：诊断串里**不要出现方括号** —— 外层解析靠 [ ... ] 定界，
  //       以前 secs=[a,b] 的内层括号会把正则截断（实测踩坑）。
  var diag = 'pages=' + pages + ' menu=' + cnt('[data-menu]') + '/' + cnt('[data-menu]', 1) +
             ' popup=' + menuOpened + '/' + menuItemFired +
             ' dlg=' + cnt('dialog[open] button') +
             ' secs=' + secs.split('[').join('').split(']').join('');
  var d = document.createElement('div');
  d.id = '__smoke_result';
  d.textContent = 'UI-SMOKE errors=' + uniq.length + ' clicked=' + clicked +
                  ' skipped=' + skipped + ' [' + diag + '] :: ' +
                  JSON.stringify(uniq.slice(0, 10));
  document.body.appendChild(d);
}
</script>
"""


def find_browser():
    for p in BROWSERS:
        if os.path.isfile(p):
            return p
    return None


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(directory, port):
    handler = lambda *a, **k: Quiet(*a, directory=str(directory), **k)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd


def run(src_root: Path, browser: str, budget_ms: int = 20000, dump_to: str = None):
    static = src_root / "static"
    if not (static / "index.html").is_file():
        return None, f"找不到 {static / 'index.html'}"

    fixtures, nfix, tfix = load_fixtures()
    tmp = Path(tempfile.mkdtemp(prefix="ui_smoke_"))
    try:
        shutil.copytree(static, tmp / "site")
        html = (tmp / "site" / "index.html").read_text(encoding="utf-8", errors="ignore")
        if "</head>" not in html or "</body>" not in html:
            return None, "index.html 结构异常（缺 </head> 或 </body>）"
        html = html.replace("</head>", build_stub(fixtures) + "</head>", 1)
        html = html.replace("</body>", RUNNER + "</body>", 1)
        (tmp / "site" / "__smoke.html").write_text(html, encoding="utf-8")

        port = free_port()
        httpd = serve(tmp / "site", port)
        profile = tmp / "chrome-profile"
        try:
            # ★ 必须给桌面视口。默认 800x600 会落到移动端卡片流布局
            #   （`.rowgrid .c-ops{display:none}`）—— 行内操作列被 CSS 藏起来，
            #   `···` 菜单按钮就永远点不到。实测踩坑：不设视口时 22 个菜单按钮
            #   全在 DOM 里、可见的 0 个，检查形同虚设。
            cmd = [browser, "--headless=new", "--disable-gpu", "--no-sandbox",
                   "--disable-extensions", "--disable-background-networking",
                   "--window-size=1440,900",
                   f"--user-data-dir={profile}", "--dump-dom",
                   f"--virtual-time-budget={budget_ms}",
                   f"http://127.0.0.1:{port}/__smoke.html"]
            r = subprocess.run(cmd, capture_output=True, timeout=120)
            dom = r.stdout.decode("utf-8", errors="replace")
        finally:
            httpd.shutdown()

        if dump_to:
            Path(dump_to).write_text(dom, encoding="utf-8")
            print(f"[ui_smoke] DOM 已落盘：{dump_to}（{len(dom)} 字节）", file=sys.stderr)

        m = re.search(r'id="__smoke_result"[^>]*>(.*?)</div>', dom, re.S)
        if not m:
            return None, "拿不到结果标记（页面可能没跑起来）"
        text = m.group(1).strip()
        mm = re.search(r"UI-SMOKE errors=(\d+) clicked=(\d+)"
                       r"(?: skipped=(\d+))?(?:\s*\[([^\]]*)\])?\s*::\s*(.*)",
                       text, re.S)
        if not mm:
            return None, f"结果格式异常：{text[:120]}"
        return dict(errors=int(mm.group(1)), clicked=int(mm.group(2)),
                    skipped=int(mm.group(3) or 0), diag=(mm.group(4) or "").strip(),
                    detail=mm.group(5).strip(),
                    fixtures=f"{nfix}/{tfix}"), None
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def selftest(browser):
    """红绿自检：注入 PM-D1，断言本脚本会红。

    「没有红过的检查等于没写过」—— 这条自检把该断言固化下来，
    以后改脚本时能立刻发现它被改成了装饰品。
    """
    print("=" * 74)
    print("自检：注入 PM-D1（crud.openEdit → 裸 openEdit），断言 ui_smoke 变红")
    print("=" * 74)
    base, err = run(ROOT / "src", browser)
    if err:
        print(f"  基线跑不起来：{err}")
        return False
    print(f"  基线（干净代码）：errors={base['errors']} clicked={base['clicked']}"
          f"  → {'绿' if base['errors'] == 0 else '红'}")

    tmp = Path(tempfile.mkdtemp(prefix="ui_selftest_"))
    try:
        shutil.copytree(ROOT / "src" / "static", tmp / "static")
        target = tmp / "static" / "js" / "tab-holdings.js"
        src = target.read_text(encoding="utf-8")
        patched = src.replace("crud.openEdit(code)", "openEdit(code)", 1)
        if patched == src:
            print("  ✗ 注入失败：源码里找不到 `crud.openEdit(code)`（缺陷可能已被重构）")
            return False
        target.write_text(patched, encoding="utf-8")
        inj, err2 = run(tmp, browser)
        if err2:
            print(f"  ✗ 注入臂跑不起来：{err2}")
            return False
        print(f"  注入臂：errors={inj['errors']}  {inj['detail'][:110]}")
        ok = base["errors"] == 0 and inj["errors"] > 0
        print()
        print("  结论：" + ("有牙 ✔（干净绿 / 注入红）" if ok
                         else "没牙 ✘ —— 脚本抓不到 PM-D1，需要重写"))
        return ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(prog="ui_smoke")
    ap.add_argument("--src", default=str(ROOT / "src"))
    ap.add_argument("--budget", type=int, default=20000)
    ap.add_argument("--dump-dom-to", dest="dump_to", default=None,
                    help="把渲染后的 DOM 落盘，排查「为什么没渲染出来」用")
    ap.add_argument("--selftest", action="store_true",
                    help="红绿自检：注入 PM-D1 并断言本脚本会红")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    browser = find_browser()
    if not browser:
        print("[ui_smoke] ✗ 找不到 Chrome/Edge，无法做运行时点击检查", file=sys.stderr)
        return 3

    if a.selftest:
        return 0 if selftest(browser) else 1

    res, err = run(Path(a.src), browser, a.budget, a.dump_to)
    if err:
        print(f"[ui_smoke] ✗ {err}", file=sys.stderr)
        return 1

    ok = res["errors"] == 0
    if a.json:
        print(json.dumps(dict(ok=ok, **res), ensure_ascii=False))
    else:
        print(f"[ui_smoke] {'绿' if ok else '红'}  真点了一遍：{res['clicked']} 次点击"
              f"（跳过 {res['skipped']} 个用户点不到的），{res['errors']} 个 JS 报错")
        print(f"           证据夹具 {res['fixtures']} | {res['diag']}")
        if not ok:
            print(f"           {res['detail'][:400]}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
