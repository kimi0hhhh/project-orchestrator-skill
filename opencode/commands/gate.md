---
description: 按 gate-rules 判定一个工件并落盘 gate-log
agent: orchestrator
---
对工件 `$2` 执行门禁 `$1`。

步骤（不许跳）：

1. 读 `.opencode/protocols/gate-rules.md` 里 `$1` 的判定条件与红线。
2. 先过 DoR / DoD 两问：
   - DoR：上游工件 `status=approved` 已落盘？派发三要素齐全？
   - DoD：子 agent 自验收全勾？「必须写」工件全部落盘？回传信号 ≤15 行？
     任一不过 → 直接 CONCERN，不读正文。
3. 逐条核对工件 `$2`：文件真存在有内容 → 四块结构（摘要/正文/自验收/下游交接）齐全 →
   对照红线判 PASS / CONCERN / FAIL。
4. **落盘**到 `.opencode/state/gate-log.md`，格式：

   `时间 | 门禁 | 工件版本 | 判定 | 一句话理由`

   若是 **C0/C1 增量改动**（v4.1 变更分诊）：门禁降为**单点复查**，只核变更涉及的条目，
   记一行 `时间 | C0 fast-pass | 工件/变更点 | 判定 | 一句话理由`（C1 同格式换 `delta-pass`）；
   判不准按 C1 走。
5. CONCERN 的未决项登记到 `.opencode/state/open-issues.md`（负责人 + 期限）。
6. 重跑 `python runtime/board_sync.py`，让 board.md 反映最新门禁。

判定纪律：主 Agent 不得自批自验；不许用「差不多」换进度。
