# 路线图 / ROADMAP

> WorkBuddy 版 `project-orchestrator`。协议源：[kimi0hhhh/project-orchestrator-skill](https://github.com/kimi0hhhh/project-orchestrator-skill) tag `v4.1`。
> 本次同步（2026-09-12）已把 v4.1 的协议与流程新机制移植进 WorkBuddy 结构。
> **完整回执见 skill 根目录 `SYNC-RECEIPT-v4.1.md`**（逐项结果 + 差异裁决 + 验证记录）；
> 本文件是路线图 + 遗留问题清单。

## 本次同步回执（v4.1 移植）

| # | 项 | 状态 |
|---|---|---|
| 1 | S5 测试前置（S2 PASS 后 qa 起草 17，与 S3 并行，≤3 预算） | **已移植** |
| 2 | S4 增量评审（草稿完成检查点先介入，最后只做集成裁定与 15/16 定稿） | **已移植** |
| 3 | 变更分诊 C0–C2（新章节，进 SKILL.md 与 ORCHESTRATOR.md） | **已移植** |
| 4 | 派发 pre-flight checklist（4 条，缺一不派） | **已移植** |
| 5 | 心跳纪律（开工即报 --pct 5 / >90s heartbeat / >10min 补 heartbeat） | **已移植** |
| 6 | 星形参谋机制 + 动态编制 L0–L2 | **已移植**（源：上游 `docs/ARCHITECTURE.md` §3.5 与 `docs/DESIGN.md` §5） |
| 7 | 删除 SKILL.md 过期「角色契约路径」行 | **已移植（有差异）**——见下「差异裁决记录」D-1 |
| 8 | runtime/lib/store.py 看门狗 v3.17–v3.19 移植 | **已移植**——见下「差异裁决记录」D-2 |
| 10 | SKILL/README/AGENTS 定位升级（四层） | **已移植** |
| 11 | 新增「开源 skill 引用」节 | **已移植** |
| 12 | 自建实验数据降权为「开发验证（简述）」 | **已移植** |
| 13 | ALL-IN-ONE.md 同步重生成 | **已移植** |
| 14 | `metadata.version` = `"4.1"` + install.sh 临时工作区验证 | **已移植** |

## 差异裁决记录

### D-1 · 「角色契约路径」行的处理方式（有差异）

**上游做法**：v4.1 直接**删除**派发模板里的契约路径行，理由是「契约已作子 agent 的系统提示，无需自查文件」。

**本版做法（有意保留差异）**：WorkBuddy 侧子 agent 以 `general-purpose` 派发，
**契约不会作为系统提示自动注入**，所以派发 prompt 仍必须让它先读工作区里的契约文件。
本版的处理是**修正**而非删除：

- SKILL.md 的通用「派发 prompt 必须包含」清单里，把原来写死的
  `.workbuddy/agents/0X-*.md` 占位行**删除**，改为「角色契约已由移植机制铺进工作区，
  只需在【本次任务】说明它扮演哪个角色」；
- ORCHESTRATOR.md 的阶段模板保留具体契约文件名（`01-product-manager.md` 等），
  但明确它们是**工作区相对路径**，并**禁止引用资产源目录**（`~/.workbuddy/skills/...`）
  —— 引用只读源会让子 agent 读到与工作区不同步的版本。

**裁决**：保留上述差异。若未来 WorkBuddy 支持以角色名直接派发（契约作系统提示），
则回退到上游的纯删除做法。

### D-2 · store.py 与上游不同源，移植范围收窄（有差异）

本地 `runtime/lib/store.py` 与上游 v4.1 **不同源且较旧**（上游 81.8 KB / 本地 48.4 KB）。
按本次任务只移植「看门狗 v3.17–v3.19 演进」，**以下差异未移植**，列此待裁决：

| 上游 delta | 为什么没移植 | 影响 |
|---|---|---|
| 拆出 `runtime/lib/usage.py`（真实用量适配层，ZCode/OpenCode 双后端） | 属 token 账本演进（v3.16.x），不在本次三项之列；本地 `token_summary` 是**字节估算**口径，换后端会改成本口径 = 破坏性变更 | 看板 token 仍是估算值（本地既有行为，未回退） |
| `registry()` 的模板回退 `_template_fallbacks()` / `normalize_model()` / `_MODEL_ALIAS` | 同上，属模型账本加固，非看门狗范畴 | 老项目 registry 缺字段时的回退仍走本地的 `load_json(TEMPLATE)` 路径 |
| `set_plan_stage()` 的 `_default_stage()` 自动建阶段 | **2026-09-12 已补** —— 见下「验收修复」 | 已解决 |
| `zcode_session_tokens()` / `actual_cost_usd()` | 依赖价格表的 `raw_per_1m` 字段，本地价格表没有；且属 token 账本 | 未提供真实成本核算（本地既有行为） |

**接口兼容性结论**：本次移植**未破坏任何既有接口**。新增的都是**可选**参数与**新增**路由/子命令：

- `cli.py`：`spawn --zcode-agent`（新增可选参数）、新增子命令 `actual-model` / `model-report`；
- `server.py`：新增 `GET /api/model/main`、`POST /api/model/report`、`POST /api/model/actual`；
- `store.py`：新增 `zcode_verdict` / `zcode_session_facts` / `zcode_fresh_ms` / `_zc_con` /
  `zcode_session_actual` / `zcode_session_alive` / `main_session_actual` /
  `set_actual_model` / `set_reported_model`；`watchdog()` 签名不变、返回值语义不变（仍返回新判列表中）；
  `snapshot()` 只**新增**字段，未删改既有字段。

**一处本版补全（上游的漏）**：上游 v4.1 的 `cli.py spawn` 会发送 `zcode_agent` 字段，
但 `server.py /api/spawn` **没有接收它**，导致会话 id 只可能通过 `actual-model` 事后登记，
看门狗的 DB 判据在首次派发后的一段时间里读不到会话。本版在 `/api/spawn`
（含 resume 分支）补上接收并落盘 —— **增量、向后兼容**，不改变任何既有调用方行为。

## 验收修复（2026-09-12，起 demo 项目时暴露）

> 用三个内部 demo 项目实跑看板时暴露（已脱敏，代号见 tools/seed-demo.py）。
> **4 项里 2 项是真 bug，2 项属"文档承诺与实际能力脱节"。**

| # | 问题 | 性质 | 修法 |
|---|---|---|---|
| **F-1** | **主 Agent 起服务后服务立刻死**：宿主在每次工具调用结束时**回收整棵进程树**，`DETACHED_PROCESS` 也照杀。日志里**没有 traceback**（所以不是崩溃），表现为「刚打印出地址，下一次调用就 connection refused」；同机对照：用户手动启动的服务连续存活 3h+ | 真 bug —— 框架可用性前提 | `board.py` 新增 `wmi` 子命令，走 `Win32_Process.Create`（父进程 `WmiPrvSE.exe`，在调用者作业对象之外）；新增 `runtime/serve.cmd`；SKILL / ORCHESTRATOR / README / AGENTS / USAGE 五份文档的启动命令统一改掉 |
| **F-2** | **新建项目后作战地图永远写不进**：`create_project()` 不生成 `plan.json`，`get_plan()` 恒返回 `{"stages": []}`，于是**每一个** `set_plan_stage()` 都返回「未知阶段：S0」 | 真 bug —— 正是 D-2 里搁置的 `_default_stage()` 缺失 | ① `create_project()` 按 `registry.phases` 预置 S0–S7（等权重 pending）；② `set_plan_stage()` 找不到阶段时就地建（老项目 / 未来新增阶段双保险） |
| F-3 | `runtime/start.cmd` 里 `set PY=` 指向**上游作者的路径** `C:\Users\junben.lai001\...` | 移植残留 | 改为本机路径（保留 `if not exist` 回退） |
| F-4 | `board.py` 候选端口从 **8778** 起，而 `server.py` 默认 **8777** | 一致性 | `CANDIDATES` 首位补 8777 |

**F-1 的严重性**：这不是"某个功能不好用"，而是**"主 Agent 在会话里根本无法把服务起起来"**。
不修的话，SKILL.md 里「每次唤醒必须自动起服务并打开 UI」这条用户拍板的纪律就是空头承诺。

**F-2 的隐蔽性**：单看每个函数都"正常"（`set_plan_stage` 逻辑没错、`get_plan` 默认值也没错），
只有**组合起来**才暴露——新项目的地图永远空白。这类 bug 靠读代码找不到，必须真跑。

**验证**：`board.py wmi` 起服务后**跨多次工具调用持续存活**（对照：旧方式下一次调用即 refused）；
`create_project` 后 `stages == [S0..S7]`、加权 `overall_progress` 计算正确、`S99` 仍正确报未知阶段、
`plan.json` 缺失时能自动补建。

## 已知遗留问题（v4.2 状态更新）

> 三条问题在 v4.2 的 WorkBuddy 深度适配里被重新评估。**逐条标注真实状态，不夸大**。

1. **spawn 的 pid 未登记 —— ⏳ 仍未根治（但危害已降级）**
   子 agent 由 Agent 工具派发，**没有稳定的 OS 进程号**可登记（`$$` 在 Git Bash 里是 MSYS
   自己的 PID，不是 Windows PID，拿它查进程永远是"已死"）。
   后果：`pid_alive()` 常返回 `None`，中断性质只能落在 `stalled` 而非 `dead`。
   *v4.2 新增缓解*：现在**并发写入两个稳定标识**——`zcode_agent`（客户端会话 id，v4.1）
   与 WorkBuddy 的 **session id**（v4.2，由 `wb_find_session(cwd)` 按工作区解析并进 `native.session_id`）。
   看门狗因此不再**依赖** pid 就能拿到证据。但 `dead` 这一级仍然拿不到——
   **根治需要宿主暴露真实子 agent 进程号，本版做不到，如实留在这里。**

2. **会话日志证据通道易失效 —— ✅ 已治（v4.2）**
   `zcode_session_alive()` / `zcode_session_actual()` 依赖 `~/.zcode/cli/rollout/model-io-*.jsonl`
   的命名约定，宿主改名/换目录就会**静默返回 None**，看门狗退回纯静默超时。
   *v4.2 修法*：新增**独立的第二条证据通道** `~/.workbuddy/workbuddy.db`
   （`sessions` + `session_usage`）。它与 ZCode 私有库**不同源**，一方失效另一方仍在。
   已在 watchdog 里作为否决层接入，`lease_source` 会写明是哪一层给的证据。

3. **240s 静默兜底误报率仍偏高 —— ✅ 已治（v4.2，机制层）**
   `SILENCE_INTERRUPT = 240` 对长 thinking / 写大文件偏紧，实测 S3 双 agent 被同时误判。
   *v4.2 修法*：不再是"纪律层兜底"，而是**机制层一票否决**——静默判定之前先查 WorkBuddy
   会话级证据（`sessions.status='working'` 且 `last_activity_at` / `session_usage.updated_at`
   新鲜，实测每秒级更新），命中则**直接续约、绝不判停滞**。
   *实测验证*：造景「agent 静默 10000 秒、无 pid、无 zcode 证据」——
   原生层可用时判 `working` 并续约（`lease_source=workbuddy-session:working`）；
   原生层不可用时才落 `stalled` 并给「疑似停滞」措辞。
   *未做*：按任务类型自适应阈值（保留为后续项）。

## 后续计划

- [x] **v4.2 已完成**：WorkBuddy 原生账本下沉（`changes-index` / `artifact-index` /
      `session_usage` / `tasks`）→ `/api/state` 新增 `native` 块
- [x] **v4.2 已完成**：契约内联派发（`runtime/lib/contract.py` + `cli.py dispatch`），
      把 pre-flight 从文档约定变成代码校验
- [x] **v4.2 已完成**：看门狗原生否决层 + 三条遗留问题重新评估
- [ ] **v4.1.x 候选**：把 `usage.py` 适配层移植进来，让 token 账本从"字节估算"切到
      "客户端 DB 真实值"（需先给价格表补 `raw_per_1m`，并同步 `_calc_cost` 口径 —— 破坏性变更，需裁决）
      *注*：v4.2 已用 `native.usage`（WorkBuddy `session_usage` 真实值）**旁路**提供真实口径，
      上面这条"替换口径"的破坏性变更因此**优先级下降**
- [ ] **v4.1.x 候选**：`registry()` 模板回退加固（`_template_fallbacks` / `normalize_model`）
- [ ] **v4.1.x 候选**：`plan` 的 `_default_stage()` 自动建阶段
- [ ] **v4.2 候选**：看板前端消费 `native` 块（真实 token / 原生台账交叉验证面板）
      —— 本次**刻意未动 `ui/index.html`**（本地 104.6 KB 深度定制，UI 误读是本项目最敏感的回归）
- [ ] **v4.2 候选**：`protocols/gate-rules.md` 正式纳入 C0/C1 单点复查判定条件
- [ ] **v4.2 候选**：把 `native.usage.used_tokens` 与自建字节估算并排显示时**显式标注来源**，
      避免两个口径被当成同一个数（见 SKILL.md「原生能力映射」纪律 3）
- [ ] 契约↔代码逐条对齐抽查门禁（上游 v4.1 计划项，本版未落地）
- [ ] role-pool persona 条目分发（上游 v4.1 计划项）
- [ ] 清掉 `runtime/store.py` 这份**历史遗留的重复副本**（`server.py` 实际加载的是
      `runtime/lib/store.py`；两份并存会让人误改错文件）—— 需先确认无外部引用
- [ ] n≥5 + 双评审交叉的复现实验（上游 v4.1 计划项）

## 长期想法（不承诺）

- 分诊规则从人工清单升级为预测模型（Google 研究已证明 87% 可选对架构）
- 门禁日志与 retro 的跨项目学习回路
- 看板多项目聚合视图
