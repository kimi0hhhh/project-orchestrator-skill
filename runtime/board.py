"""看板服务自启 / 自检 / 打开 —— 主 Agent 唤醒时先跑它。

    python runtime/board.py ensure     # 没起就起，打印 URL（唤醒时用这个）
    python runtime/board.py status     # 只检查，不起
    python runtime/board.py open       # 起好并打开默认浏览器
    python runtime/board.py stop       # 停掉（按 .pid）

设计要点：
- 端口不写死。优先沿用 runtime/.port，被占就顺延找空闲端口。
- 已经活着就**不重复启动**（多个 server 抢同一份 jsonl 会互相覆盖）。
- 启动后**等到真能连通**再打印 URL，避免"给了地址但打不开"。
- 子进程完全脱离父进程（主 Agent 的会话结束后看板仍存活）。
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
CANDIDATES = [8778, 8779, 8780, 8781, 8782, 8790, 8877]


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
    elif cmd == "stop":
        stop()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
