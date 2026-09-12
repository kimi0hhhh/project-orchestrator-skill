---
description: 让主 Agent 汇报四件事（阶段 / 谁在跑 / 下一步 / 待拍板）
agent: orchestrator
---
请汇报当前项目状态，四件事，每条一段，不要展开成报告：

1. **当前阶段**：现在在 S 几，门禁过了哪些（读 `.opencode/state/gate-log.md`，
   别只读 board.md —— board 是派生文件）
2. **谁在跑谁待命**：`python runtime/cli.py projects --project <pid>` +
   `.opencode/state/board.md` 的「在跑的 Agent」段
3. **下一步打算**：你准备派谁做什么
4. **需要用户拍板什么**：只列四种打断场景（Brief 缺核心信息 / 会签冲突 /
   要砍需求 / 终验不通过），没有就写「无」

若 `board.md` 与 gate-log 对不上，先跑 `python runtime/board_sync.py` 再汇报。
