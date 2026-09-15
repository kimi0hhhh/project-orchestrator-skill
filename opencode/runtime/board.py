"""看板服务 · 体检 / 自启 / 打开 —— 主 Agent 唤醒时先跑它。

    python runtime/board.py check --port 8788   # 只体检，不起服务（预检用）
    python runtime/board.py open  --port 8788   # 体检 → 起服务 → 打开浏览器 ★推荐
    python runtime/board.py open                # 用 .port 里已配置的端口（不自动挑）
    python runtime/board.py status              # 只看当前状态
    python runtime/board.py stop                # 停掉（按 .pid）

端口纪律（v4.4 起）：
- **端口由用户指定，不自动分配。** 自动挑端口会让两套实现各挑各的，
  实测踩坑：本工作区 .port=8778 已死，daemon.py 回退默认 8777，
  而 8777 上恰好是**另一个工作区**的服务在应答 → 误报「已在运行」，
  把用户指到别人的看板上，且本工作区什么都没启动。
- 端口一旦定下就写进 `.port`，**长期沿用**；只在被占/失效时才重新问用户。
- 端口被占时必须分清「自己的」和「别人的」：
    MINE_ALIVE → 复用（服务已在跑，只打开浏览器）
    FOREIGN    → **报错退出，把占用者摊给用户看**，绝不偷偷换端口、绝不劫持
    UNKNOWN    → 认不出身份时按 FOREIGN 处理（fail-safe：宁可问用户，不可抢端口）

退出码：0 成功 / 2 端口被别的服务占用 / 3 未指定端口且 .port 不可用 / 1 其他失败
"""
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # runtime/
WS = ROOT.parent                                # 工作区根
PORTFILE = ROOT / ".port"
PIDFILE = ROOT / ".pid"
SERVER = ROOT / "server.py"

sys.path.insert(0, str(ROOT / "lib"))
try:
    import store  # noqa: E402
except Exception:
    store = None

EXIT_OK, EXIT_OTHER, EXIT_FOREIGN, EXIT_NEEDPORT = 0, 1, 2, 3


# ── 基础探测 ──────────────────────────────────────────────────
def alive(port, timeout=0.6):
    """能连上 TCP 就算活着 —— 比进程名判断更可靠（Windows 上尤其）。"""
    if not port:
        return False
    try:
        with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
            return True
    except Exception:
        return False


def read_port():
    try:
        return int(PORTFILE.read_text(encoding="utf-8").strip())
    except Exception:
        return None


def write_port(port):
    PORTFILE.write_text(str(port), encoding="utf-8")


def port_pid(port):
    """找出占用该端口的进程号（netstat 解析，纯标准库）。"""
    try:
        r = subprocess.run(["netstat", "-ano"], capture_output=True, timeout=12)
        txt = r.stdout.decode("gbk", errors="replace")
    except Exception:
        return None
    pat = re.compile(r"^\s*TCP\s+\S+:%d\s+\S+\s+LISTENING\s+(\d+)\s*$" % int(port), re.M)
    m = pat.search(txt)
    return int(m.group(1)) if m else None


def _decode(b):
    """按本地代码页解码子进程输出。

    坑：中文 Windows 的 PowerShell 默认按 GBK 输出，硬解 UTF-8 会把
    `FundLens_交付包_20260911` 解成 `FundLens_������_20260911`，
    于是自己的服务被误判成别人的（实测踩坑）。daemon.py 里也有一份同样的处理。
    """
    b = b or b""
    for enc in ("gbk", "utf-8"):
        try:
            return b.decode(enc).strip()
        except UnicodeDecodeError:
            continue
    return b.decode("utf-8", errors="replace").strip()


def proc_cmdline(pid):
    """取进程命令行（Windows；失败返回 None）。强制 PowerShell 按 UTF-8 输出。"""
    if os.name != "nt" or not pid:
        return None
    ps = ("[Console]::OutputEncoding=[System.Text.Encoding]::UTF8;"
          f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, timeout=15)
        return _decode(r.stdout) or None
    except Exception:
        return None


def state_snapshot(port, timeout=3.0):
    """问这个端口要 /api/state —— 一次性拿到身份与项目名。"""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{int(port)}/api/state",
                                    timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


def same_path(a, b):
    try:
        return os.path.normcase(os.path.abspath(str(a))) == \
               os.path.normcase(os.path.abspath(str(b)))
    except Exception:
        return False


def own_projects():
    """本项目认识的 project id 集合（projects.json 的 list + current）。"""
    ids = set()
    p = ROOT / "projects.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("current"):
            ids.add(d["current"])
        for it in d.get("list") or []:
            if isinstance(it, dict) and it.get("id"):
                ids.add(it["id"])
            elif isinstance(it, str):
                ids.add(it)
    except Exception:
        pass
    return ids


def classify(port):
    """判定端口归属：FREE / MINE_ALIVE / FOREIGN / UNKNOWN。

    证据按可靠性排序，**首选问服务本人「你是谁」**——它直接回答 workspace 路径，
    不受控制台代码页影响。认不出归属时一律当 FOREIGN（宁可问用户，不可抢端口）。
    """
    if not alive(port):
        return "FREE", "端口空闲"

    snap = state_snapshot(port)
    proj = (snap or {}).get("project")
    ws = (snap or {}).get("workspace")

    # 证据 1（首选，编码无关）：服务自报 workspace
    if ws:
        if same_path(ws, WS):
            return "MINE_ALIVE", f"本工作区看板（自报 workspace 一致）"
        return "FOREIGN", f"被别的工作区的看板占用：\n      {ws}"

    # 证据 2：进程命令行（老版本 server.py 没有 workspace 字段时）
    pid = port_pid(port)
    cmd = proc_cmdline(pid)
    if cmd:
        norm = cmd.replace("/", "\\").lower()
        if str(SERVER).replace("/", "\\").lower() in norm:
            return "MINE_ALIVE", f"本工作区看板（pid={pid}）"
        if "server.py" in norm:
            return "FOREIGN", f"被别的进程占用：pid={pid}\n      {cmd[:170]}"

    # 证据 3（弱）：能应答 /api/state 且 project 名是本项目认识的
    if proj and proj in own_projects():
        return "MINE_ALIVE", f"本项目看板（project={proj}）"
    if proj:
        return "FOREIGN", f"被另一个项目的看板占用（project={proj}）"

    # 认不出 → fail-safe
    return "UNKNOWN", (f"端口有服务在应答，但认不出归属"
                       f"（pid={pid}）；按占用处理，请换端口")


# ── 启动 / 停止 ───────────────────────────────────────────────
def start(port):
    """脱离父进程启动服务，等端口真的通。"""
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "DETACHED_PROCESS", 0) | \
                getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    p = subprocess.Popen(
        [sys.executable, str(SERVER), str(port)],
        cwd=str(WS),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    for _ in range(24):
        if alive(port):
            PIDFILE.write_text(str(p.pid), encoding="utf-8")
            return True
        time.sleep(0.25)
    return False


def stop():
    if not PIDFILE.exists():
        print("[board] 没有记录到 pid，跳过")
        return EXIT_OK
    pid = PIDFILE.read_text(encoding="utf-8").strip()
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", pid, "/F"], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(int(pid), 15)
        print(f"[board] 已停止 pid={pid}")
    except Exception as e:
        print(f"[board] 停止失败：{e}")
        return EXIT_OTHER
    return EXIT_OK


# ── 两个动作 ─────────────────────────────────────────────────
def do_check(port):
    kind, why = classify(port)
    icon = {"FREE": "空闲", "MINE_ALIVE": "是自己", "FOREIGN": "被占", "UNKNOWN": "认不出"}[kind]
    print(f"[board] 端口 {port} → {icon}")
    print(f"        {why}")
    return {"FREE": EXIT_OK, "MINE_ALIVE": EXIT_OK,
            "FOREIGN": EXIT_FOREIGN, "UNKNOWN": EXIT_FOREIGN}[kind]


def do_open(port, opener=webbrowser.open):
    kind, why = classify(port)

    if kind in ("FOREIGN", "UNKNOWN"):
        print(f"[board] ✗ 端口 {port} 不能用 —— {why}")
        print("[board]   请换一个端口重试：python runtime/board.py open --port <新端口>")
        print("[board]   （不会自动改端口：偷偷换端口会把两套服务指到不同地方）")
        return EXIT_FOREIGN

    if kind == "FREE":
        if not start(port):
            print(f"[board] ✗ 端口 {port} 未在 6 秒内就绪，请手动执行 "
                  f"{sys.executable} runtime/server.py {port}", file=sys.stderr)
            return EXIT_OTHER
        write_port(port)
        print(f"[board] 已启动    →  http://127.0.0.1:{port}（已写入 .port，下次沿用）")
    else:                                    # MINE_ALIVE
        write_port(port)
        print(f"[board] 已在运行  →  http://127.0.0.1:{port}  ({why})")

    url = f"http://127.0.0.1:{port}"
    try:
        ok = opener(url)
        print("[board] 已调用浏览器打开" if ok else
              "[board] 浏览器未确认打开；请手动访问上面的地址")
    except Exception as e:
        print(f"[board] 打开浏览器失败（{e}）；请手动访问 {url}")
    return EXIT_OK


def main():
    args = sys.argv[1:]
    cmd = args[0] if args and not args[0].startswith("-") else "open"
    port = None
    if "--port" in args:
        i = args.index("--port")
        if i + 1 < len(args) and args[i + 1].isdigit():
            port = int(args[i + 1])
    # 兼容旧写法：位置参数当端口
    for a in args[1:]:
        if a.isdigit():
            port = int(a)
            break

    if cmd == "stop":
        return stop()
    if cmd == "status":
        p = read_port()
        kind, why = classify(p) if p else (None, "未配置")
        print(f"[board] {'运行中' if kind == 'MINE_ALIVE' else '未运行'}  port={p}  {why}")
        return EXIT_OK

    if port is None:
        port = read_port()

    if cmd == "check":
        if port is None:
            print("[board] 还没配置端口。请让用户指定一个，然后："
                  "python runtime/board.py check --port <端口>")
            return EXIT_NEEDPORT
        return do_check(port)

    if cmd in ("open", "ensure"):
        if port is None:
            print("[board] ✗ 还没有配置端口。")
            print("[board]   请**询问用户**要用哪个端口**，然后执行：")
            print("[board]     python runtime/board.py open --port <用户给的端口>")
            print("[board]   （不自动挑端口：自动挑会让下一次启动不知道去哪儿找看板）")
            return EXIT_NEEDPORT
        return do_open(port)

    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
