# v4.2 深度适配回执 · WorkBuddy 原生优先

> 对象：WorkBuddy 版 `project-orchestrator`（`~/.workbuddy/skills/project-orchestrator/`）
> 触发：用户指出「我要的是你针对 WorkBuddy **深度适配**，而不是简单复刻迁移」
> 执行日期：2026-09-12 ｜ 性质：**架构方向修正**，非上游版本同步

---

## 一、这次修的是什么

v4.1 做的是**协议搬运**：把上游 ZCode 版 v4.1 的 14 条机制逐条搬过来，只在装载层
（`install.sh` 铺文件）和路径上做了适配，然后交付。

那不是适配，是复刻 —— 因为它**假设 WorkBuddy 和 ZCode 的宿主能力相同**。
v4.2 先把这个假设推翻，再基于 WorkBuddy 的**实测能力**重做落点。

**一句话概括方向**：v4.1 是「把上游搬过来」，v4.2 是「**凡是 WorkBuddy 已经做了的，
本体系不再重复造轮子；自建只保留原生没有的部分**」。

---

## 二、实测到的 WorkBuddy 原生能力（全部有落盘证据，非推测）

| 能力 | 落盘位置 | 实测样本 |
|---|---|---|
| 团队 / 成员 | `~/.workbuddy/teams/<名>/{config.json,inboxes/}` | `software-fund-tracker` 团队，team-lead inbox **54 KB** |
| 任务列表 | `~/.workbuddy/tasks/<cid>/<N>.json` | 13 条，字段 `subject`/`activeForm`/`status` |
| 变更台账（自动） | `~/.workbuddy/changes-index/<cid>.json` | 6 条，332 行增量，含 `checkpointId`/`detailRef` |
| 产物台账（自动） | `~/.workbuddy/artifact-index/<cid>.json` | 4 条，含 `sourceTool=PresentFiles`/`toolCallId` |
| 审计流水（自动） | `~/.workbuddy/audit-log/YYYY-MM-DD.jsonl` | 单日 200–550 KB |
| 真实用量 | `workbuddy.db` → `session_usage` | `used=197510`/`size=300000`，`credit_json` 逐请求 credits |
| 会话存活 | `workbuddy.db` → `sessions` | `status=working`、`cwd` 精确匹配、`model`、`thought_level` |
| 执行 trace（自动） | `~/.workbuddy/traces/<port>/trace_*.json` | 单个可达 1.7 MB |
| **软件团队 agent** | `plugins/cache/experts/software-company/1.1.0/agents/*.md` | 5 个：`software-team-lead` / `-product-manager` / `-architect` / `-engineer` / `-qa-engineer`（**当前 disabled**） |

---

## 三、一个决定性的否定实验（改变了 W1 的形态）

上游把 `agents/<name>.md` 当子 agent 的 frontmatter 定义，**契约由宿主自动注入**。
WorkBuddy 的等价机制是否存在？**做了实验，结论是不存在**：

1. 在工作区写入探针 `.workbuddy/agents/probe-agent.md`（格式照抄内置 `sheet-agent` 的
   `name`/`description`/`tools` frontmatter）；
2. 立即用 `subagent_type: probe-agent` 派发 →
   **`Error: Task agent probe-agent is not available`**；
3. 结论：`plugins/*/agents/*.md` 之所以能当 `subagent_type`，是因为它们
   **在应用启动时注册**；会话内写入不生效。而编排的派发发生在**同一会话内**，
   不可能中途重启应用。

**→ 靠原生 agent 类型注入契约这条路，在编排场景下不可用。**

但上游机制的**本质**是「契约必须进入子 agent 的上下文」—— 这个目标可以达成，只需换手段：

> **主 Agent 显式把契约内联进派发 prompt。**

这不是降级方案，反而更可靠：上游靠宿主实现，本版**靠代码**，与宿主解耦。

---

## 四、变更清单

### W1 · 契约内联派发（新增）

| 文件 | 变更 |
|---|---|
| `runtime/lib/contract.py` | **新增**（约 240 行）。`ROLES` 登记表 / `resolve_agents_dir()`（工作区优先、资产源回退）/ `load_contract()` / `extract_sections()`（按节裁剪）/ `validate()`（pre-flight 校验）/ `build_dispatch_prompt()` |
| `runtime/cli.py` | 新增子命令 `dispatch`（含 `--check`）与 `contracts`；`main()` 与 `__main__` 改为透传退出码 |
| `SKILL.md` | 「派发子 agent」整节重写为契约内联；pre-flight checklist 加代码兜底说明 |
| `ORCHESTRATOR.md` | §3「关于契约路径」blockquote → v4.2 契约内联；pre-flight 块加 `--check` |
| `AGENTS.md` | 「开工前必读」第 3 条改为「契约已内联，不需再读文件」 |

**产出效果**：
- 契约正文明文拼在派发 prompt 末尾，子 agent **无需再 Read 契约文件**；
- pre-flight 必填项（目标/产出物绝对路径/允许读/task_id/完成判据）**缺一项即 exit 1**，
  「缺一不派」从文档约定变成**代码保证**；
- `--section` 可按节裁剪：实测 **10,128 → 2,415 bytes**（−76%）。

**D-1 裁决结果**：v4.1 遗留的「契约路径行：删除 vs 保留」之争**到此作废** ——
两条路都不是正解。正解是**第三条：内联**。已确定，不再待裁决。

### W4 · 看门狗原生否决层（新增）

| 文件 | 变更 |
|---|---|
| `runtime/lib/store.py` | **新增** WB 层：`WB_DB`/`WB_FRESH_MS` 常量、`_wb_con()`、`_norm_path()`、`wb_find_session()`、`wb_session_facts()`、`wb_verdict()`、`wb_usage()` |
| 同上 | `watchdog()` 在**静默判定之前**插入否决层；`lease_source` 新增取值 `workbuddy-session:working` |
| `SKILL.md` / `ORCHESTRATOR.md` / `docs/DESIGN.md` §9 / `USAGE.md` 坑 1 | 存活判据从三层改述为**四层**，并写明否决层语义 |

**语义边界（写进代码注释与全部文档，不放宽）**：
WorkBuddy 子 agent **同进程内**运行、共享**同一条 session 记录**，
`sessions` 里**没有 per-subagent 行**。所以本层**只能否决、不能断言**：
它证明「这条会话在活动」，**不是**「第 3 号子 agent 活着」。
真正的 per-agent 判据仍由 zcode 层提供 —— **两层互补，不是替换**。

### W2 · 原生账本下沉（新增）

| 函数 | 作用 |
|---|---|
| `wb_native_changes()` | 读 `changes-index/<cid>.json`，聚合成「文件 → 编辑次数/±行数/动作」 |
| `wb_native_artifacts()` | 读 `artifact-index/<cid>.json`，按 `sourceTool` 归类 |
| `wb_native_tasks()` | 读 `tasks/<cid>/*.json`，按 `status` 归类 |
| `wb_native_block()` | 快照用的融合块，**任一步失败只少一个键，绝不抛异常** |

`snapshot()` 新增 `native` 键（既有 23 个键**一个未动**）。

**处置原则**：自建台账**一个不删**。自建带编排语义（门禁/阶段/放行/退回原因），
原生只有「文件变了/产物出来了」——**下沉读取 ≠ 推倒重来**。

### W3 · 任务与消息双写纪律（协议层）

`ORCHESTRATOR.md` §6 新增双写纪律表：原生任务**给用户看**（WorkBuddy 任务区），
自建任务**给编排用**（带 phase/gate）。明确「原生的没有门禁字段，自建的没有宿主 UI」。

### 文档与链路

| 文件 | 变更 |
|---|---|
| `SKILL.md` | `metadata.version: "4.2"` + `upstream`/`note` 字段；**新增整节「WorkBuddy 原生能力映射」**（含三条纪律） |
| `docs/DESIGN.md` | **新增 §11**（11.1 问题 / 11.2 契约内联 / 11.3 账本下沉 / 11.4 否决层 / 11.5 取舍）；§9 补第 3 层；§10 遗留问题状态更新 |
| `docs/ROADMAP.md` | 三条遗留问题**逐条重新评估**；后续计划勾选 v4.2 已完成项，新增 v4.2 候选 |
| `README.md` | 版本 4.1→4.2；新增 v4.2 深度适配要点；目录补 `lib/contract.py` 与回执 |
| `USAGE.md` | 新增「v4.2 的两条新增纪律」（实为三条）；坑 1 补机制层缓解 |
| `install.sh` / `install.cmd` | 自检加 `lib/contract.py` + `contracts` 可用性 + `dispatch --check` 必须拦下缺项；新增 `_MISS` 计数与总结行 |
| `tools/build-all-in-one.py` | 版本回退默认值 4.1→4.2 |
| `ALL-IN-ONE.md` | **重生成**：136,710 → **146,425 bytes** / 2,459 → **2,587 行** |

---

## 五、验证记录

### 5.1 决定性否定实验（见 §三）

```
写入 .workbuddy/agents/probe-agent.md → Agent(subagent_type="probe-agent")
→ Error: Failed to execute task ... Task agent probe-agent is not available
```
探针已清理，`.workbuddy/agents/` 目录已删除（工作区恢复原状）。

### 5.2 契约内联（`lib/contract.py` + `cli.py dispatch`）

| 用例 | 结果 |
|---|---|
| `contracts` 列角色 | 7/7 契约解析，含体积 |
| `dispatch --check` 缺字段 | **exit 1**，逐条列出 5 项缺项 ✓ |
| `dispatch --check` 齐全 | 通过，exit 0 ✓ |
| 完整 dispatch 输出 | 骨架（目标/产出物/边界/task_id/上报要求/完成判据）+ 契约内联，格式正确 ✓ |
| `--section 定位` 裁剪 | 10,128 → **2,415 bytes**（−76%）✓ |
| `allowed_read` 校验 | **修正过一轮**：初版误把「工件名 §节」当文件路径要求绝对路径，已改为只对 `artifacts` 校验 ✓ |
| 工作区内解析 | `contracts` 指向**工作区** `.workbuddy/agents/`（非资产源）✓ |

### 5.3 看门狗否决层（端到端，用真实库）

造景：`status=working`、静默 10000 秒、无 pid、无 zcode 证据。

| 用例 | 结果 |
|---|---|
| **A** WB 可用 | `watchdog()` 返回 `[]`（不中断）；`lease_source=workbuddy-session:working`；`liveness` 带**真实 token** `183498/300000` ✓ |
| **B** WB 库不可用 | 落 `interrupted` / `stalled`，措辞「疑似停滞：静默 10000 秒且无会话证据（非结论，可续跑）」 ✓ |
| **C** 静默仅 30s | 不打断 ✓ |
| 降级（库路径不存在） | `wb_find_session`→`None`、`wb_verdict`→`(None,'')`，**不抛异常** ✓ |

→ **遗留问题③（240s 误报）在机制层被治**：A 用例正是过去必然误报的场景。

### 5.4 原生账本读取

```
changes : session 1c407442… | 6 条 | +337 −0 | 2 个文件
          · .workbuddy/memory/2026-09-12.md   x6  +324 -0  ['create','modify']
          · .workbuddy/agents/probe-agent.md  x1   +13 -0  ['create']   ← 探针被如实记录
artifacts: 4 条 | by_tool {'PresentFiles': 4}
tasks    : 13 条 | {'in_progress':3,'completed':7,'pending':3}
usage    : used=197510 / 300000，credits_total=24.6
```

### 5.5 回归检查

- `snapshot()` 键：**既有 23 个全在**（含 `agents`/`messages`/`events`/`tasks`/`plan`/
  `silence_warn`/`silence_interrupt`/`pending_notes` 等），`native` 为**纯新增** ✓
- `agents[0]` 字段数 38（未减） ✓
- `py_compile`：`store.py` / `contract.py` / `cli.py` 全部 OK ✓
- **未改 `ui/index.html`**（本地 104.6 KB 深度定制，UI 误读是本项目最敏感的回归类型）；
  新字段已进 `/api/state`，前端需要时可自取 ✓

### 5.6 移植链路（install.sh → 临时工作区实跑）

```
20/20 [ok]（契约 7 + 协议 3 + state 3 + runtime 6 + ORCHESTRATOR）
  [ok] cli.py --help 可用
  [ok] cli.py contracts 可用（解析到 7/7 份契约）
  [ok] dispatch --check 正确拦下缺项
  —— 自检通过：0 项异常 ——
```

### 5.7 ALL-IN-ONE 幂等

连跑两次，去第 11 行时间戳后 **完全一致** ✓
（首次报"漂移"是测试脚本 bug：`cp` 到 `/tmp` 成功导致比对文件没生成，非内容问题。）

---

## 六、遗留问题状态（诚实标注，不夸大）

| # | 问题 | v4.2 状态 |
|---|---|---|
| ① | spawn 的 pid 未登记 | ⏳ **仍未根治**。新增 session id 作为稳定标识，看门狗不再依赖 pid；但 `dead` 一级仍拿不到 —— **根治需宿主暴露子 agent 进程号** |
| ② | 会话日志通道易失效 | ✅ **已治**：新增 `workbuddy.db` 作为**独立的第二条证据通道**，与 ZCode 私有库不同源 |
| ③ | 240s 静默兜底误报高 | ✅ **已治**：机制层一票否决（实测 §5.3 用例 A） |

---

## 七、仍未做的事（明确声明，避免被当成已完成）

1. **未统一 token 口径**：自建仍是字节估算，`native.usage` 是真实值，
   两者**并排存在未合并**。只在文档里标注来源。合并属破坏性变更，需单独裁决。
2. **未改看板前端**：`native` 块已进 `/api/state`，但 `ui/index.html` 没消费它。
3. **未启用 `software-company@experts`**：它在市场里有 5 个原生软件团队 agent
   （许清楚/高见远/寇豆码/严过关 + 交付总监），但自带一套 SOP 路由
   （快速模式/BugFix/标准 SOP）与我们的 S0–S7 重叠。**本次判断为不启用**
   —— 契约内联方案不依赖它，且两套流程并存会打架。若要启用，需先裁决分工。
4. **未移植上游 usage.py / registry 回退加固 / plan 自动建阶段**（v4.1 遗留的 D-2 差异）。
5. `runtime/store.py`（44.4 KB 历史重复副本）**仍未清理**，`protocols/gate-rules.md`
   仍**未纳入 C0/C1 单点复查判定条件**。

---

## 八、一句话总结

v4.1 交付的是「一份搬到 WorkBuddy 的协议」；v4.2 交付的是「**一份知道自己在 WorkBuddy 上
站在什么位置的协议**」—— 知道哪些能力该用宿主的、哪些必须自己带、以及
**当宿主没有等价机制时，用什么手段也能达成同一个目标**。
