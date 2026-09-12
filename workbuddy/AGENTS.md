# AGENTS.md

本工作区启用**多 Agent 协作开发框架**（版本 `4.1`）：主 Agent 负责派发与验收，
子 Agent 只对工件负责。工件通过**文件**交接，不靠上下文记忆。

框架四层：**协议**（单写手 / 单层编排 / 只读参谋 / 门禁不放水）+
**流程**（6 契约 + S0–S7 状态机 + 参谋会回路 + 变更分诊 C0–C2 / L0–L2）+
**可视化**（`runtime/` 作战看板）+ **追溯**（token 账本 / 事件总线 / 门禁留痕 / retro 四问）。

## 开工前必读（按序）

1. `ORCHESTRATOR.md` —— 阶段状态机与派发命令模板（主 Agent 的主手册）
2. `docs/PROJECT_BRIEF.md` —— 产品输入书，整套流程的唯一入口
3. **你自己的角色契约** —— v4.2 起它**已经内联在派发 prompt 末尾**（标题为
   「角色契约（内联）· <角色名>」），**不需要再去读 `.workbuddy/agents/*.md`**。
   只在派发 prompt 里没看到契约时才回退去读文件（例如用了 `--section` 裁剪、
   或派发方是手写 prompt）。
4. `.workbuddy/protocols/handoff-schema.md` —— 工件文件头与四块正文结构
5. `.workbuddy/protocols/gate-rules.md` —— 你的工件怎么算 PASS
6. `.workbuddy/state/board.md` —— 当前阶段

完整规则见 `SKILL.md`；单文件全量版见 `ALL-IN-ONE.md`（给不支持读多文件的工具用）。

> **v4.2 说明**：WorkBuddy 不会把角色契约作为子 agent 的系统提示自动注入，
> 所以主 Agent 用 `cli.py dispatch` 把契约**内联**进你的派发 prompt。
> 这比"让你自己去读文件"可靠——你不会因为漏读而丢掉角色方法论。

## 三条铁律

1. **主 Agent 不下场干活** —— 不写代码、不写产品文档、不替子 Agent 做决策。
   要改内容就写清意见 → 退回 → 让它改。
2. **工件走文件交接** —— 任何一环都能被替换、被打回、被重跑；没有交付物就是没有任务。
3. **门禁不放水** —— CONCERN 就登记到 `.workbuddy/state/open-issues.md`，不用「差不多」换进度。

## 每份工件必须有文件头

```
---
artifact: <工件名>
owner: <角色>
version: v1
status: draft
supersedes: <被取代的文档，无则写 —>
created: YYYY-MM-DD
reviewers: [<会签角色>]
gate: <门禁编号>
---
```

正文四块：结论 → 依据 → 影响 → 未决项。

## 上报纪律（有看板时）

```bash
python runtime/board.py wmi                                    # 起看板（受限沙箱必须用 wmi）
python runtime/cli.py spawn     --agent <id> --project <pid>
python runtime/cli.py progress  --agent <id> --pct 5  --step "已启动，正在读 X" --project <pid>
python runtime/cli.py heartbeat --agent <id> --step "长跑中：<在做什么>" --project <pid>
python runtime/cli.py finish    --agent <id> --project <pid>
```

**★ v4.1 心跳纪律三条**（不遵守会被自己的看门狗判死，这是设计上的必然）：

- **开工即报**：第一条 progress 在**读任何文档之前**发出（`--pct 5 --step "已启动，正在读 X"`）；
- **>90 秒的长命令先发 heartbeat**，再等结果（否则静默看门狗 240s 会把你判成中断）；
- **>10 分钟无 progress 补 heartbeat 自证存活**——看门狗**无法区分「深思」与「挂死」**。

**进度 ≥3 次**：读文档完 20% → 数据就位 40% → 核心跑通 60% → 验证完 90%。

**★ 存活判据（v4.1）**：看门狗优先读客户端 DB（`~/.zcode/cli/db/db.sqlite`）把
「活着 / 结束 / 异常」从猜变成读，读不到回退会话日志，最后才静默超时。
诚实边界：回合进行中时「在深思」与「已挂死」从外部无法区分，这类只表现为
「**疑似停滞**」，不构成结论。中断性质分三级：`dead` / `stalled` / `abnormal`。

## ★ 增量模式（收到标注「增量模式」的派发时，v4.1）

上线后的 C0/C1 改动**不开阶段状态机**，走的是一条快车道。你收到这类派发时必须：

- **只改相关节 / 追加条目**，**禁止重排或重写全文**——重写会让评审退化为全文重读，
  是快车道变慢的主因；
- 允许读清单会被**精确到节**（契约只给相关接口条目），不要自行扩大读取范围；
- 返修退回**同一** agent 续会话（就是你），别重读上下文。

## 缺陷分流（别把所有 bug 都给开发）

| 症状 | 给谁 |
|---|---|
| 做错了 | 开发（前端 / 后端） |
| 做对了但不该这么定义 | 产品经理 |
| 做对了但结构撑不住 | 架构师 |
| 两边都没错，是话说岔了 | 架构师改契约 |

## 禁止项

- 禁止修改 `runtime/**`（编排工具）。需要新能力，回报主 Agent 由主 Agent 改。
- 禁止不并行写同一文件的两个 Agent 并行派发（前后端可并行，因为文件隔离）。
- 禁止向其他 agent 派发子任务（一层编排）；需要拆解或增援时上报主 Agent。
- 回传信号不超过 15 行。
