"""看板服务自启 / 自检 / 打开 —— 主 Agent 唤醒时先跑它。

    python runtime/board.py ensure     # 没起就起，打印 URL
    python runtime/board.py wmi        # ★ 受限沙箱（主 Agent 调 Bash 工具）用这个
    python runtime/board.py status     # 只检查，不起
    python runtime/board.py open       # 起好并打开默认浏览器（本机手动用）
    python runtime/board.py stop       # 停掉（按 .pid）

设计要点：
- 端口不写死。优先沿用 runtime/.port，被占就顺延找空闲端口。
- 已经活着就**不重复启动**（多个 server 抢同一份 jsonl 会互相覆盖）。
- 启动后**等到真能连通**再打印 URL，避免"给了地址但打不开"。
- ensure() 用 DETACHED_PROCESS 脱离父进程 —— 对本机手动启动足够。
  **但在受限沙箱里不够**：宿主会在每次调用结束时回收整棵进程树，detached 也照杀。
  那种场景必须用 `wmi`（见 start_via_wmi 的注释与 USAGE.md 坑 3）。
"""
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent          # runtime/
WS = ROOT.parent                               # 工作区根
PORTFILE = ROOT / ".port"
PIDFILE = ROOT / ".pid"
SERVER = ROOT / "server.py"
# 8777 放最前：与 server.py 的默认端口保持一致。此前 board.py 从 8778 起，
# 而 server.py 默认 8777，两个入口给出不同端口，排查时容易误判"服务没起来"。
CANDIDATES = [8777, 8778, 8779, 8780, 8781, 8782, 8790, 8877]


def alive(port: int, timeout: float = 0.6) -> bool:
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


def free_port():
    for p in CANDIDATES:
        if not alive(p):
            with socket.socket() as s:
                try:
                    s.bind(("127.0.0.1", p))
                    return p
                except OSError:
                    continue
    raise RuntimeError("候选端口全被占用，请手动指定端口")


def start(port: int) -> bool:
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


def start_via_wmi(port=None) -> bool:
    """用 WMI 在**调用者进程树之外**启动服务（受限沙箱下的唯一可靠解法）。

    为什么必需：某些宿主（本机实测 WorkBuddy 的 Bash 工具）会在**每次调用结束时
    回收整棵进程树** —— `DETACHED_PROCESS` 也救不了，服务会在调用结束的瞬间被杀，
    表现为「刚打印出地址，下一次调用就连不上」，而日志里没有任何异常（不是崩溃）。
    实测证据：同一次调用内 curl 通、下一次调用 connection refused；同一台机器上
    由用户手动启动的服务则能连续存活数小时。

    WMI 创建进程时父进程是 WmiPrvSE.exe，位于调用者的作业对象之外，因此不受回收。
    """
    for c in (port, read_port()):
        if c and alive(c):
            print(f"[board] 已在运行  →  http://127.0.0.1:{c}")
            return True

    script = ROOT / "serve.cmd"
    if not script.exists():
        print(f"[board] 缺少 {script}，无法用 WMI 启动", file=sys.stderr)
        return False

    cmdline = f'cmd.exe /c "{script}"'
    ps = ("([wmiclass]'Win32_Process').Create('"
          + cmdline.replace("'", "''")
          + "') | Select-Object -ExpandProperty ReturnValue")
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                           capture_output=True, text=True, timeout=40)
    except Exception as e:
        print(f"[board] WMI 启动失败：{e}", file=sys.stderr)
        return False

    if (r.stdout or "").strip() != "0":
        print(f"[board] WMI 返回异常：{((r.stdout or '') + (r.stderr or '')).strip()[:160]}",
              file=sys.stderr)
        return False

    # serve.cmd → board.py ensure 会自己挑端口并写 .port，这里轮询等它就绪
    for _ in range(40):
        p = read_port()
        if alive(p):
            print(f"[board] 已通过 WMI 脱离启动  →  http://127.0.0.1:{p}")
            return True
        time.sleep(0.25)
    print("[board] WMI 已下发，但端口未在 10 秒内就绪；看 runtime/board.log",
          file=sys.stderr)
    return False


def ensure(verbose: bool = True):
    port = read_port()
    if alive(port):
        if verbose:
            print(f"[board] 已在运行  →  http://127.0.0.1:{port}")
        return port
    port = free_port()
    if not start(port):
        print("[board] 启动失败：端口未在 6 秒内就绪，请手动执行 "
              f"{sys.executable} runtime/server.py {port}", file=sys.stderr)
        return None
    PORTFILE.write_text(str(port), encoding="utf-8")
    if verbose:
        print(f"[board] 已启动    →  http://127.0.0.1:{port}")
    return port


def stop():
    if not PIDFILE.exists():
        print("[board] 没有记录到 pid，跳过")
        return
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


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "ensure"
    if cmd == "ensure":
        ensure()
    elif cmd == "status":
        port = read_port()
        print(f"[board] {'运行中' if alive(port) else '未运行'}  port={port}")
    elif cmd == "open":
        port = ensure(verbose=False)
        if port:
            url = f"http://127.0.0.1:{port}"
            print(f"[board] 打开    →  {url}")
            webbrowser.open(url)
    elif cmd in ("wmi", "detach"):
        # 受限沙箱（主 Agent 在 WorkBuddy 会话里调 Bash 工具）专用：
        # 普通 ensure() 起的服务活不过本次调用，必须由 WMI 从进程树外创建。
        start_via_wmi()
    elif cmd == "stop":
        stop()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
