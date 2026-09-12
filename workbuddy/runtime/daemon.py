"""把看板服务以「脱离终端」的方式拉起来 —— 一次启动，长期存活。

## 为什么需要它
用普通"后台任务"启动的服务是父 shell 的子进程：父 shell 一结束，服务跟着死。
表现就是**看板莫名其妙又打不开了**（本工作区实测：启动后跑满 9m49s 被杀）。

这里用 Windows 的 `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW`
把服务变成独立进程，脱离调用者的进程树，于是它不再随会话结束而消失。

## 用法
    python runtime/daemon.py [port]        # 启动（已在跑则跳过）
    python runtime/daemon.py [port] stop   # 停止
"""
import os
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOG = ROOT / "server.log"
PIDF = ROOT / ".server.pid"


def alive(port):
    """端口上已有服务在应答？"""
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=1.0):
            return True
    except OSError:
        return False


def read_port():
    f = ROOT / ".port"
    if f.exists():
        try:
            return int(f.read_text(encoding="utf-8").strip())
        except Exception:
            pass
    return 8777


def stop():
    p = None
    if PIDF.exists():
        try:
            p = int(PIDF.read_text(encoding="utf-8").strip())
        except Exception:
            p = None
    if not p:
        print("没有记录到服务 pid")
        return 1
    if os.name == "nt":
        # taskkill 的输出走本地代码页（中文 Windows 为 GBK），按 UTF-8 硬解会乱码
        def _dec(b):
            b = b or b""
            for enc in ("gbk", "utf-8"):
                try:
                    return b.decode(enc).strip()
                except UnicodeDecodeError:
                    continue
            return b.decode("utf-8", errors="replace").strip()

        r = subprocess.run(["taskkill", "/PID", str(p), "/F", "/T"],
                           capture_output=True)
        print(_dec(r.stdout) or _dec(r.stderr) or f"已尝试结束 pid={p}")
    else:
        os.kill(p, 15)
        print(f"已发送 TERM 给 {p}")
    try:
        PIDF.unlink()
    except OSError:
        pass
    return 0


def main():
    # v3.x 修复：stop 写在第二个参数（如 `daemon.py 8777 stop`）时会被忽略，只认 argv[1]
    if "stop" in sys.argv[1:]:
        return stop()
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    port = int(arg) if arg and arg.isdigit() else read_port()

    if alive(port):
        print(f"看板已在运行：http://127.0.0.1:{port}（无需重复启动）")
        return 0

    flags = 0
    if os.name == "nt":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        CREATE_NO_WINDOW = 0x08000000
        flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW

    f = open(LOG, "ab", buffering=0)
    p = subprocess.Popen(
        [sys.executable, str(ROOT / "server.py"), str(port)],
        stdout=f, stderr=f, stdin=subprocess.DEVNULL,
        cwd=str(ROOT.parent), creationflags=flags, close_fds=True,
    )
    PIDF.write_text(str(p.pid), encoding="utf-8")

    import time
    for _ in range(40):
        time.sleep(0.25)
        real = read_port()
        if alive(real):
            print(f"看板已脱离终端启动：http://127.0.0.1:{real}　pid={p.pid}　日志={LOG}")
            return 0
    print(f"启动超时，请查看日志：{LOG}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
