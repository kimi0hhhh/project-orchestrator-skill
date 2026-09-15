---
description: 唤醒主 Agent 接管项目（走完整唤醒检查单）
agent: orchestrator
---
请接管项目：$ARGUMENTS

严格按「唤醒检查单」执行，顺序不能省（新会话里你是全新上下文，不靠记忆靠文件）：

1. 读 `ORCHESTRATOR.md` —— 阶段状态机与派发模板
2. 读 `.opencode/state/board.md` —— 当前阶段（注意：这是派生文件，真相源是
   `runtime/projects/<pid>/plan.json` + `.opencode/state/gate-log.md`）
3. 读 `docs/PROJECT_BRIEF.md` —— 产品输入书
4. 读 `.opencode/state/open-issues.md` —— 未决项
5. 起看板（**端口由用户指定**，先看现况）：

   !`cd "$(pwd)" && python runtime/board.py status 2>&1`

   - 显示「运行中」→ `python runtime/board.py open`（复用 + 打开浏览器）
   - 显示「未运行 / 未配置 / 被占」→ **先问用户用哪个端口**，再
     `python runtime/board.py open --port <端口>`；若 exit 2，把占用者原样念给用户，
     请他换一个，**不要自己换端口**
   - 端口定下后写进 `runtime/.port`，**长期沿用**（只问一次，不是每次都问）

6. 向用户汇报**五件事**：当前阶段 / 谁在跑谁待命 / 下一步打算 / 需要你拍板什么 /
   **看板地址**（`看板 → http://127.0.0.1:<端口>`）

   **不论浏览器有没有弹出来，都要把地址念给用户** —— 非交互 shell 里
   `webbrowser.open` 有弹不出来的可能，念地址是兜底。地址从 `board.py status` 读，
   不凭记忆；状态是「未运行」就先起好再念，**别给死地址**。

若 `docs/PROJECT_BRIEF.md` 缺「核心问题」或「失败定义」→ 门禁 G-IN-00 判 FAIL，
先向用户要这两项，不许开工。
