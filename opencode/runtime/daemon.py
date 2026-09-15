"""兼容层：daemon.py 已并入 board.py（v4.4）。

## 为什么合并
`daemon.py` 与 `board.py` 是同一件事的两份实现：两个 pid 文件（.server.pid / .pid）、
两套端口来源（默认 8777 / 候选 8778+）、两处启动逻辑。实测踩坑：

    本工作区 .port=8778（已死）→ daemon.py 回退默认 8777
    → 8777 上恰好是**另一个工作区**的服务在应答
    → alive(8777)=True → 打印「看板已在运行，无需重复启动」并直接返回
    → 本工作区什么都没启动，用户还被指到别人的看板上。

按本体系自己的纪律（handoff-schema §2.3「引用优先于复制，粘贴即产生双份真相」），
同一事实源不该有两份实现。端口与身份判定现在只有一处：`board.py`。

## 用法（与旧版参数兼容）
    python runtime/daemon.py [port]         # 等价 board.py open --port <port>
    python runtime/daemon.py [port] stop    # 等价 board.py stop
    python runtime/daemon.py                # 不带端口：沿用 .port；没配置会要求先指定

退出码与 board.py 一致：0 成功 / 2 端口被别的服务占用 / 3 未指定端口 / 1 其他
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOARD = HERE / "board.py"


def main():
    args = sys.argv[1:]
    port = next((a for a in args if a.isdigit()), None)
    if "stop" in args:
        cmd = [sys.executable, str(BOARD), "stop"]
    else:
        cmd = [sys.executable, str(BOARD), "open"]
        if port:
            cmd += ["--port", port]
    print("[daemon] 已并入 board.py，转发 →", " ".join(cmd[1:]))
    return subprocess.call(cmd, cwd=str(HERE.parent))


if __name__ == "__main__":
    sys.exit(main())
