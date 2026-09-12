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
5. 起看板：

   !`cd "$(pwd)" && python runtime/daemon.py 8790 2>&1 | tail -2`

   然后 `python runtime/board.py open`（或把 `http://127.0.0.1:$(cat runtime/.port)` 给用户）

6. 向用户汇报**四件事**：当前阶段 / 谁在跑谁待命 / 下一步打算 / 需要你拍板什么

若 `docs/PROJECT_BRIEF.md` 缺「核心问题」或「失败定义」→ 门禁 G-IN-00 判 FAIL，
先向用户要这两项，不许开工。
