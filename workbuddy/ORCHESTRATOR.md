# 主编排手册 · 多 Agent 协作开发框架

> 这是主 Agent 的操作台。所有角色定义、协议、工件都在本文件中被串起来。
> **启动流程前，主 Agent 必读本文件 + `.workbuddy/agents/00-orchestrator.md`。**
>
> 框架四层：**协议**（单写手 / 单层编排 / 只读参谋 / 门禁不放水）+ **流程**（6 契约 + S0–S7
> 状态机 + 参谋会回路 + 变更分诊 C0–C2 / L0–L2）+ **可视化**（`runtime/` 作战看板）
> + **追溯**（token 账本 / 事件总线 / 门禁留痕 / retro 四问）。版本 `4.1`。

---

## 唤醒检查单（每次新会话，主 Agent 先做这六步）

新会话里主 Agent 是**全新上下文**，不靠记忆靠文件。按顺序做：

| # | 动作 | 读什么 |
|---|---|---|
| 1 | 认清流程 | 本文件（阶段状态机 + 派发命令） |
| 2 | 看进度 | `.workbuddy/state/board.md` |
| 3 | 看产品输入 | `docs/PROJECT_BRIEF.md` |
| 4 | 看未决项 | `.workbuddy/state/open-issues.md` |
| 5 | 看运行时 | `python runtime/board.py wmi`（已在跑则自动跳过。**受限沙箱里必须用 `wmi`**：宿主会回收调用者的进程树，`detached` 也照杀——见 USAGE.md 坑 3）→ **随即自动打开看板**：`http://127.0.0.1:8777`。**用户要求：每次唤醒必须自动起服务并打开 UI，不等用户开口**（2026-09-10 用户拍板） |
| 6 | 向用户汇报 | 当前阶段 / 谁在跑 / 下一步 / 需要拍板什么 |

服务没起时：先 `python runtime/board.py status`，再看 `runtime/board.log`。

**用户的开场白**（固定句式，说这句就会加载 `project-orchestrator` skill）：

```
启动主 Agent，接管 <项目名>
```

---

## 0. 这套体系解决什么问题

单个 Agent 从头做到尾会犯三种错：

| 错误 | 后果 | 本体系的解法 |
|---|---|---|
| 自己写需求自己验收 | 做出来才发现没人要 | 产品经理与开发分离，终验由 PM 实操 |
| 边做边想架构 | 中途推翻重来 | 架构阶段强制门禁，动手前锁定契约 |
| 前后端各做各的 | 联调爆炸 | 契约即法律，逐字段比对，偏差零容忍 |

**核心设计原则**：每个 Agent 只对**工件**负责，不对"整个项目"负责。
工件通过文件交接，不靠上下文记忆——这样任何一环都能被替换、被打回、被重跑。

---

## 1. 三步启动

```bash
# 1. 填写产品输入书（用户填，或主 Agent 代填后让用户确认）
docs/PROJECT_BRIEF.md          # 模板已就绪，含必填项说明
docs/PROJECT_BRIEF.md                     # 产品输入书（唯一入口）

# 2. 主 Agent 校验 Brief（G-IN-00）
#    缺「核心问题」或「失败定义」→ 不许开工

# 3. 按 §3 状态机逐级派发
```

---

## 2. 目录即流程

```
docs/
├── PROJECT_BRIEF.md        ← S0 用户填
├── 00-charter/             ← S1 产品经理
│   ├── 01-requirements.md
│   ├── 02-prd.md
│   ├── 03-ui-design.md
│   └── 04-ui-wireframe.html
├── 01-architecture/        ← S2 架构师
│   ├── 05-product-arch.md
│   ├── 06-system-arch.md
│   ├── 07-frontend-arch.md
│   ├── 08-backend-arch.md
│   ├── 09-api-contract.md      ★ 前后端唯一法律
│   └── 10-arch-review.md       ★ PM 会签纪要
├── 02-frontend/            ← S3a 前端
│   ├── src/...
│   └── 12-interface-request.md
├── 03-backend/             ← S3b 后端（与前端并行）
│   ├── src/...
│   └── 14-api-impl-report.md
├── 04-integration/         ← S4 组长
│   ├── 15-code-review.md
│   └── build/
├── 05-qa/                  ← S5 测试
│   ├── 17-test-plan.md
│   ├── 18-test-report.md
│   └── 04-defects.md
└── 06-acceptance/          ← S6 产品经理终验
    └── 19-pm-acceptance.md

.workbuddy/
├── agents/       7 个角色契约（本手册的执行细则）
├── protocols/    handoff-schema / gate-rules / revision-loop
└── state/        gate-log.md / open-issues.md / board.md
```

---

## 2.5 关键路径重叠（v4.1，提速不减质）

阶段串行是默认，但**依赖提前解除**的两段可以并行开工（并发预算照常 ≤3）：

### ① S5 测试计划前置

**S2 契约门禁 PASS 后**，即可派 `qa` 起草 `docs/05-qa/17-test-plan.md`——
用例设计**只依赖 `09-api-contract` 与 `02-prd`，不依赖实现代码**。
qa 与 S3 前后端**并行**（正好占满 ≤3 预算），于是 **S5 阶段只剩执行与 `18-test-report`**。
`17` 照常走门禁（G-QA-01）。

- **席位约束**：qa 进场时 S3 前后端已占两席，正好满编；
  若 S3 期间还有**外援在场**，则 qa **推迟**到任一席位空出。
- 若 `09` 契约在 S3 期间发生变更 → qa 的用例清单必须以**变更后的契约**为准并复审，
  不得沿用旧契约静默跑（这正是把 17 前置后新增的耦合点）。

### ② S4 增量评审

`dev-lead` **不必等前后端全部完工**——前端 / 后端各自的「**草稿完成检查点**」先介入一轮评审
（前置条件：该端源码目录已有可读产出且 `12/14` 报告已落盘），
最后**只做集成裁定与 `15-code-review` / `16-build` 定稿**。

### 禁止提前的

- **PM×架构师会签保持串行**（要吵出结论，不能各写各的）；
- **S6 终验不开参谋、不并行**（签字必须单一）。

---

## 2.6 变更分诊：不是每次改动都走全流程（v4.1）

S0–S7 只服务「新项目 / 新功能面」。**上线后的增量改动在入口先分诊**——
主 Agent **自行判定，不派评估 agent**；被分到 C0/C1 的改动**不开阶段状态机**：

| 级 | 判据 | 走法 |
|---|---|---|
| **C0 轻改** | 单角色单文件可完成；**不触碰 `09` 契约与 `02` 冻结口径**（文案 / 样式 / 局部修正 / 补用例） | 直接派对应角色 **1 个** → dev-lead 快审单点判定 |
| **C1 小需求** | 需改 1–2 个工件；契约可能动 | 谁的工件谁增量改；**仅当契约变更时**才走 PM×架构师会签；**只派受影响端** |
| **C2 新需求** | 跨端 / 新功能面 / 口径级变化 | 走完整 S1–S7 |

**增量纪律（C0/C1 通用）**：

- 派发 prompt 标注「**增量模式**」：只改相关节 / 追加条目，**禁止重排或重写全文**——
  重写让评审退化为全文重读，是快车道变慢的主因；
- **改动清单精确到节、写绝对路径**；允许读清单同样精确到节（契约只给相关接口条目）；
- 门禁降为**单点复查**：只核变更涉及的条目，`gate-log` 记一行
  `C0 fast-pass` / `C1 delta-pass`；出 CONCERN 照常登记 `open-issues`，**不放水**；
- 返修退回**同一**子 agent 续会话，省去重读上下文。

**判不准按 C1 走**——增量会签本来就便宜，漏掉契约变更的会签才贵
（与阶段分诊「拿不准就降档」方向相反，因为这里低估的代价不再被门禁兜住：契约漂移在集成期才暴露）。

**自检标尺**：一次 C0 的合理开销是 **1 次派发 + 1 行门禁记录**；超过 3 次派发，
说明它被当成 C2 在跑，停下来重新分诊。

---

## 3. 阶段状态机与派发命令

> 下列命令中的 `{...}` 为变量。派发时用 `Agent` 工具，
> `subagent_type: general-purpose`，把整段 prompt 作为 `prompt` 传入。
>
> **★ v4.2 契约内联（WorkBuddy 深度适配，取代「让子 agent 自读契约」）**：
> 上游 ZCode 版把 `agents/<角色>.md` 当子 agent 的 frontmatter 定义，**契约由宿主自动注入**。
> WorkBuddy **没有这个机制**——子 agent 一律 `general-purpose`；`plugins/*/agents/*.md`
> 虽可作 `subagent_type`，但那是**应用启动时注册**的
> （已实测：会话内向 `.workbuddy/agents/` 写入探针 agent 后立即派发，返回 `not available`），
> 而编排派发发生在同一会话内，不可能中途重启。
>
> → 所以**契约必须由主 Agent 显式内联进派发 prompt**。用一条命令生成，不手搓：
>
> ```bash
> python runtime/cli.py dispatch --agent architect \
>   --task "为 X 设计 Y" \
>   --artifact "<产出物绝对路径>"            `# 可重复` \
>   --allowed-read "02-prd.md §3,§5"        `# 可重复，精确到节` \
>   --criteria "<完成判据>"                  `# 可重复，必填` \
>   --task-id "<项目>/S2" \
>   [--section 定位 --section 工作方法]      `# 可选：只内联这几节，避免上下文过载`
> ```
>
> 该命令把契约正文明文拼进 prompt 末尾（子 agent 无需再 Read 任何契约文件），
> 并**强制执行 pre-flight 校验**：缺【目标】【产出物路径】【允许读】【task_id】【完成判据】
> 任一项即拒绝输出（exit 1，列出缺项）——**「缺一不派」从文档约定变成代码保证**。
> `python runtime/cli.py contracts` 可列出角色与契约文件（校验移植完整性）。
>
> 契约目录解析顺序：工作区 `.workbuddy/agents/` > 资产源 `~/.workbuddy/skills/.../agents/`。
> **不要**在派发 prompt 里引用资产源路径——那是只读模板，会让子 agent 读到与工作区不同步的版本。
> 唯一例外是 `cli.py dispatch` 在未 install 的工作区里回退读资产源，这是预期行为。

> **★ 派发时必写的一条（否则看板会长时间静默）**：要求子 Agent **开工即报** ——
> 第一条 `progress` 必须在**读完任何文档之前**发出（`--pct 5 --step "已启动，正在读 X"`），
> 之后每个阶段里程碑各报一次。只写"每做完一步上报"是不够的：读几十 KB 文档要几分钟，
> 这段时间看板上只有一条 spawn 事件，用户会以为看板坏了或 Agent 死了。

> **★ 派发 pre-flight checklist（机械执行，缺一不派）**：
> ① 被引用文件**逐个实查已落盘且非空**（`ls -la`，不凭记忆）——引用未落盘文件曾造成整轮返工（98k tokens）；
> ② 「允许读」清单与子 agent 实际需要一致，且**精确到节**（多给=上下文过载，少给=拒收重来）；
> ③ 工件路径为**绝对路径**且父目录存在（必要时先 `mkdir -p`）；
> ④ 上报要求、`--project <id>`、**完成判据**逐条写全，不留「它应该知道」。
>
> **v4.2 起 ②③④ 由代码兜底**：`cli.py dispatch --check` 会机械校验必填项与绝对路径，
> 缺项即 exit 1 并列出清单。**先 `--check` 过一遍，再生成 prompt 派发**——
> 别指望自己记得住四条，这是工具该干的事。
> 派发前另需先跑 `cli.py models --project <pid>` 读生效模型，并先
> `cli.py spawn --agent <id> --zcode-agent <agent_xxx> --title <阶段+任务>` 建节点。

> **★ v4.1 心跳纪律（不给这条，子 agent 会被自己的看门狗判死）**：
> 运行时有**静默看门狗**，agent 声称 working 但静默超 240s 会被判成「中断」。所以：
> ① **开工即报**第一条 progress（`--pct 5`，在读任何文档之前）；
> ② 凡会跑 **>90 秒**的命令，**先发 heartbeat** 说明在跑什么，再等结果；
> ③ 思考/写码 **>10 分钟**无 progress 时补一条 heartbeat 自证存活——
>    看门狗**无法区分「深思」与「挂死」**，定期心跳能省掉整轮取证与误判重派。
>
> **v4.2 存活判据（四层，每层只在拿到硬证据时给结论）**：
> ① `pid` 确认活着 → 永不判中断；
> ② **zcode per-agent**（`~/.zcode/cli/db/db.sqlite` 的 `turn_usage`/`tool_usage`/`model_usage`）
> → 最精确，能分辨 alive / abnormal / finished；
> ③ 会话日志（`~/.zcode/cli/rollout/*.jsonl`）→ 次优证据；
> ④ **WorkBuddy 原生会话级**（`~/.workbuddy/workbuddy.db` 的 `sessions` + `session_usage`）
> → **否决层**：会话确在活动时，不得因单 agent 静默判其停滞。**只否决、不断言**——
> 子 agent 是同进程共享同一条 session 记录，所以它证明的是「会话在活动」，
> 不是「某个子 agent 活着」；
> ⑤ 最后才是静默超时。
>
> 诚实边界（不变）：回合进行中时「在深思」与「已挂死」从外部无法区分，这类只能表现为
> 「**疑似停滞**」，**不能断言「中断」**。中断性质落盘三级：`dead` / `stalled` / `abnormal`。
> 排查时**先看 `lease_source`** —— 它写明这次续约是**哪一层**给的证据
> （`client-db:*` / `client-session-log` / `workbuddy-session:working`），一眼看出判据来自哪里。

> **★ v3.7 派发铁律（模型不可用时的受控降级，2026-09-11 生效）**：
> ⑧ **不做自动切模型，但做受控降级**——系统没有额度感知，**不会**自己切模型。
> 当某次派发/续跑返回「额度耗尽 / 模型不可用 / 429」这类失败时，主 Agent 执行：
> ① 按各角色配置的**降级链**（registry `fallback` 字段，`cli.py models` 可见）顺位换下一个模型
> **重派一次**；② 在事件流 `say` 记录「角色 X 因额度降级到 Y」（留痕，不许静默）；
> ③ 降级过一次仍失败 → **停下来找用户**，不得连续重试烧额度；
> ④ 该轮 retro 记录降级次数与原因，用于回看成本。
> 降级只影响**下一次派发**，不改变项目配置里的档位/模型名。

> **★ v3.6 派发铁律（模型设置可应用，2026-09-11 生效；起因：用户反馈设置面板是「假设置」）**：
> ⑦ **派发前读生效模型**——主 Agent 每次派发前必须执行
> `python runtime/cli.py models --project <pid>`，把各角色的生效模型作为 `model`
> 参数传给 Agent 工具（设置面板与 `cli.py model` 写的就是这份 registry）。
> 不得凭记忆或默认值派发，否则面板上的模型配置等于没生效。

> **★ v2 派发铁律（F4 契约加固，2026-09-10 生效）**：
> ① **派发三要素必填**——每份派发 prompt 必须含【目标】【产出物路径】【边界】且必带
> task_id，缺一子 Agent 可拒收（三步：heartbeat → say type=reject → finish，话术见
> 08-backend-arch §5）；读到 reject 消息必须重派补齐，不得置之不理。
> ② **并行预算 ≤3**——同时 working 的子 Agent 不得超过 3 个，先收敛再派新。
> ③ **嵌套禁止**——子 Agent 一律不得向其他 agent 派发子任务（一层编排），
> 需要拆解/增援时上报主 Agent。详见各角色契约「v2 加固」节。

> **★ v3.1 派发铁律（工件可见性补丁，2026-09-10 生效，起因：本轮 S1~S6 工作内容看板全空）**：
> ④ **派发即建节点**——主 Agent 每次派发前先跑 `cli.py spawn --agent <id> --title <阶段+任务>`
> 建任务节点（Agent 工具派发不经 runtime，不 spawn 则看板无节点、工件面板无从展开）。
> ⑤ **finish 必带工件**——派发 prompt 的【完成后】小节必须写明：
> `finish --artifact <产出物相对路径> --artifact-summary "一句话"`；产出多份时逐份
> `say --type artifact --artifact <路径> --body <摘要>` 补登记。禁止"只 finish 不登记"。
> ⑥ **历史漏登记即时补**——发现看板缺工作内容，先用 ⑤ 的 say 方式兜底补登记，再修流程。

> **R0 · 地基复跑（architect，串行，先于 S1）**：~~历史项目专用~~
> **本工作区（orchestrator 自我改造）不适用**——改造对象是 runtime + 契约文档，
> 地基就是现有代码本身，无外部数据依赖。此条为 历史工作区拷贝残留，已作废（主 Agent 2026-09-10）。

### S1 · 需求（product-manager，串行）

```
你是产品经理，角色契约见 .workbuddy/agents/01-product-manager.md，请先完整阅读。

【本次任务】基于 docs/PROJECT_BRIEF.md 完成需求挖掘、PRD、UI 设计三份文档
【允许读】docs/PROJECT_BRIEF.md、.workbuddy/protocols/handoff-schema.md
【必须写】
  - docs/00-charter/01-requirements.md
  - docs/00-charter/02-prd.md
  - docs/00-charter/03-ui-design.md
  - docs/00-charter/04-ui-wireframe.html
【硬性约束】
  - 每条需求必须含「场景 + 痛点 + 需求 + 验收」四段
  - 每个功能点必须含「输入/处理/输出/异常」四要素
  - PRD 必须含「不做清单」，至少 5 条
  - UI 必须定义四种状态：空态/加载中/错误/成功
  - 优先级只允许 P0/P1/P2
【禁止】不要指定任何技术选型或框架；不要修改契约或架构文件
【完成后】按 handoff-schema.md §4 回传信号，不超过 15 行
```

**验收**：G-PM-01 / G-PM-02 / G-PM-03 全 PASS → 进 S2。

---

### S2 · 架构（architect，串行，必须与 PM 会签）

```
你是产品项目开发架构师，角色契约见 .workbuddy/agents/02-architect.md，请先完整阅读。

【本次任务】完成功能架构、系统架构、前后端架构、接口契约，并与产品经理会签定稿
【允许读】docs/PROJECT_BRIEF.md、docs/00-charter/*.md、.workbuddy/protocols/*.md
【必须写】
  - docs/01-architecture/05-product-arch.md
  - docs/01-architecture/06-system-arch.md
  - docs/01-architecture/07-frontend-arch.md
  - docs/01-architecture/08-backend-arch.md
  - docs/01-architecture/09-api-contract.md
  - docs/01-architecture/10-arch-review.md
【硬性约束】
  - 功能架构按「能力域」分层，不是技术分层；每节点标注不确定性等级
  - 系统架构必须回答五问：数据来源/存储/通信/失败表现/边界
  - 契约每个字段必须写：类型 + 单位 + 精度 + 口径说明；枚举必须穷举
  - 字段名全项目统一 snake_case
  - 10-arch-review.md 必须记录与产品经理 ≥1 轮实质分歧及结论
【禁止】不要写代码；不要为"以后可能"加抽象层
【完成后】按 handoff-schema.md §4 回传信号
```

> **会签做法**：主 Agent 先派架构师出架构草案，再派产品经理做"挑刺评审"
> （复用 product-manager，任务改为「评审架构并挑刺」），
> 最后由架构师把分歧与结论写进 `10-arch-review.md`。
> **两个 Agent 必须真的吵起来**，零分歧反而可疑。

**验收**：G-AR-01 ~ G-AR-06，重点看 `10-arch-review` 有无实质分歧记录。

---

### S3 · 开发（frontend-dev ‖ backend-dev，**可并行**）

两个 Agent 写的文件完全隔离（`docs/02-frontend/` vs `docs/03-backend/`），可同时派发。
但**前端先出 `12-interface-request`**，后端拿到后才能精准实现——
所以严格说是「前端先启半天，后端跟进」的错峰并行。

```
# 前端
你是前端开发，角色契约见 .workbuddy/agents/03-frontend-dev.md，请先完整阅读。
【本次任务】按 UI 设计与架构实现产品壳，并输出接口需求清单
【允许读】docs/00-charter/03-ui-design.md、04-ui-wireframe.html、
          docs/01-architecture/07-frontend-arch.md、09-api-contract.md
【必须写】docs/02-frontend/**（源码）、docs/02-frontend/12-interface-request.md
【硬性约束】
  - 四态全部实现；请求统一走封装层；数字格式化走统一工具函数
  - 涨红跌绿；金额带 ¥ 与千分位
  - 假数据只能放 mock/ 目录且默认关闭
【禁止】禁止修改 09-api-contract.md；禁止发明契约外的接口；禁止前端计算业务数据
【完成后】回传信号

# 后端
你是后端开发，角色契约见 .workbuddy/agents/04-backend-dev.md，请先完整阅读。
【本次任务】实现核心业务逻辑与前端所需接口
【允许读】docs/01-architecture/08-backend-arch.md、09-api-contract.md、
          docs/02-frontend/12-interface-request.md、docs/00-charter/02-prd.md
【必须写】docs/03-backend/**（源码）、docs/03-backend/14-api-impl-report.md
【硬性约束】
  - 逐字段与契约一致（字段名/类型/单位/精度/枚举）
  - 数据缺失返回显式错误或 null，禁止返回"看起来对"的兜底数字
  - 金额用 Decimal 或整数分；外部调用必须有超时处理
  - 业务口径在注释中标注 PRD 来源
【禁止】禁止静默修改契约，偏差必须写进 14-api-impl-report
【完成后】回传信号
```

**验收**：G-FE-01/02、G-BE-01/02。契约偏差必须由架构师裁定后统一改。

---

### S4 · 集成（dev-lead）

> **★ v4.1 增量评审**：`dev-lead` 不必等前后端全部完工。前端 / 后端各自的
> 「**草稿完成检查点**」（该端源码目录已有可读产出且 `12-interface-request` /
> `14-api-impl-report` 已落盘）先介入一轮评审；最后**只做集成裁定与 `15/16` 定稿**。
> 每轮评审都要写进 `15-code-review.md`（标注轴：前端草稿轮 / 后端草稿轮 / 集成定稿轮），
> 这样"增量评审"才有留痕，不会退化成"偷偷提前看完就算了"。

```
你是开发组长，角色契约见 .workbuddy/agents/05-dev-lead.md，请先完整阅读。
【本次任务】<增量评审轮：前端草稿 / 后端草稿 | 集成定稿轮：集成裁定 + 15/16 定稿>
【允许读】docs/00-charter/02-prd.md、docs/01-architecture/**、
          docs/02-frontend/**、docs/03-backend/**
【必须写】docs/04-integration/15-code-review.md、docs/04-integration/build/**
【硬性约束】
  - 先过「方向偏差六项检查」，再过代码设计
  - 问题标注 BLOCK/SHOULD/NIT 严重度
  - 发现前端用假数据填满界面 → 直接 FAIL
  - 不替开发改代码，只写意见
  - build 附 README-START.md，三步内可启动
【完成后】回传信号
```

---

### S5 · 测试（qa）

> **★ v4.1 测试前置**：本阶段的 `17-test-plan.md` **应在 S2 契约门禁 PASS 后即与 S3 并行起草**
> （用例只依赖契约与 PRD，不依赖代码；qa 与前后端合计占满 ≤3 预算）。
> 因此 **S5 阶段本身只剩「执行 + `18-test-report`」**；
> 若 S3 期间有外援在场导致席位不足，则 qa 推迟到任一席位空出再进场。
> 进场前若有契约变更，用例清单必须以**变更后的 09 契约**为准复审。

```
你是测试，角色契约见 .workbuddy/agents/06-qa.md，请先完整阅读。
【本次任务】<前置轮：基于 09 契约与 02 PRD 起草 17-test-plan | 执行轮：执行用例并产出 18 报告与缺陷单>
【允许读】docs/00-charter/02-prd.md、03-ui-design.md、
          docs/01-architecture/09-api-contract.md、docs/04-integration/build/**
【必须写】docs/05-qa/17-test-plan.md、18-test-report.md、04-defects.md
【硬性约束】
  - P0 功能每个 ≥3 条用例（正常/边界/异常）
  - 数值类功能必须有口径正确性用例
  - 失败必须附证据；缺陷六项必填；数据错误一律 P0
  - 缺陷只提给 dev-lead，不直接找前后端
【禁止】不要修改任何产品代码
【完成后】回传信号
```

---

### S6 · 终验（product-manager 二次出场，必须实操）

```
你是产品经理，现在是终验环节。角色契约见 .workbuddy/agents/01-product-manager.md。
【本次任务】以真实用户身份实操开发版产品，判定是否通过验收
【允许读】docs/PROJECT_BRIEF.md、docs/00-charter/**、docs/04-integration/build/**、
          docs/05-qa/18-test-report.md
【必须写】docs/06-acceptance/19-pm-acceptance.md
【硬性约束】
  - 必须实际启动并走完 P0 主流程，不能只读测试报告
  - 对照 01-requirements 逐条走查
  - 区分「体验问题」（组长排期，不阻塞）与「功能与需求不符」（新缺陷，回流）
【完成后】回传信号
```

---

### S7 · 交付（主 Agent）+ 迭代回顾（v3 · 2026-09-10 业界对标）

> 来源：迭代回顾 retrospective（Scrum）+ 交付就绪清单（release-readiness checklist，
> 三签清单见 gate-rules.md S7 节：dev-lead/qa/product-manager 三签，缺一签不交付）。

交付动作：核对三签 → 向用户汇总交付说明与已知限制清单。

**交付后主 Agent 必产出一页 retro 工件（`docs/retro.md`，四问，每问 ≤3 行）**：
1. 门禁拦住了什么真问题？
2. 哪些门禁/流程是形式主义？
3. token 大头在哪个角色/阶段（看板 tokens 区直接读）？
4. 下一轮只改哪一条（一次只改一条，改完再观察）？

**阈值**：返工 ≥2 轮的模块必须进 retro 议题（与 revision-loop §2 阈值联动）。

---

## 4. 并行与串行规则（关键）

| 阶段 | 模式 | 原因 |
|---|---|---|
| S1 → S2 | **串行** | 架构必须基于定稿的需求 |
| 架构师 ↔ 产品经理会签 | **串行来回** | 必须吵出结论，不能各写各的 |
| 前端 ↔ 后端 | **错峰并行** | 文件隔离，但后端依赖前端的接口需求清单 |
| **S2 契约 PASS → qa 起草 17（v4.1）** | **与 S3 并行** | 用例只依赖契约不依赖代码；合计 ≤3 席；外援在场则推迟 |
| **dev-lead 增量评审（v4.1）** | **草稿完成检查点即介入** | 不等全部完工；最后只做集成裁定与 15/16 定稿 |
| S4 → S5 → S6 | **串行** | 构建 → 测试 → 终验，有强依赖 |

**禁止并行写同一文件**。两个 Agent 同时改 `09-api-contract.md` 必然冲突。

**★ 星形参谋（只读，可与主笔并行）**：高价值工件可在门禁前开一轮参谋会——
主角色唯一写笔 + 2–3 只只读参谋一轮挑刺（挑战清单 ≤15 行）+ 主笔一次返修。
参谋**不写工件、不担门禁、互不对话**；意见与契约冲突时**契约赢**。
禁用于 S6 终验（签字必须单一）。完整协议见 `SKILL.md`「星形参谋机制」。

**★ 动态编制 L0–L2**：派发前按「工作量 × 可分解性」分诊，**简单任务不加人**；
复杂 ≠ 可拆（顺序耦合工件加人有害）；拿不准就降档。见 `SKILL.md`「动态编制 L0–L2」。

---

## 5. 用户介入点（只在此时打断用户）

主 Agent 只在以下四种情况打断用户，其余一律自行决策：

1. **S0**：Brief 缺核心信息，需要用户补全
2. **S2 会签后**：架构与需求存在无法内部消化的冲突（如"想要实时但数据源不支持"）
3. **S4**：出现需要砍需求才能按时交付的情况
4. **S6**：产品经理终验不通过，需要用户裁决是改还是砍

其余时刻一律自行推进。**频繁打断用户是编排失败的表现。**

---

## 6. 记录与可追溯

每次门禁判定写入 `.workbuddy/state/gate-log.md`：

```
2026-09-10 10:52 | G-PM-02 | 02-prd v1 | CONCERN | 缺「不做清单」，已限期补充
```

未决项写入 `.workbuddy/state/open-issues.md`：

```
### ISSUE-003 | 负责人: product-manager | 期限: S2 开始前
PRD v1 缺少不做清单，导致范围可能蔓延
```

进度写入 `.workbuddy/state/board.md`，**同时用 TaskCreate 同步到任务面板**。

### ★ v4.2 双写纪律：原生任务 vs 自建任务（各有各的用户）

两套任务记录**都要写**，因为它们服务的对象不同，不是冗余：

| | 落点 | 字段 | 给谁看 |
|---|---|---|---|
| **原生任务** | `TaskCreate` → `~/.workbuddy/tasks/<cid>/<N>.json` | `subject`/`description`/`activeForm`/`status` | **给用户看**：在 WorkBuddy 任务区直接看到进度，不必开看板 |
| **自建任务** | `cli.py` / `.workbuddy/state/` | 上面的 `phase`/`stage`/门禁结论/负责人/退回原因 | **给编排用**：门禁判定与看板读它 |

- **原生的没有门禁字段**，**自建的没有宿主 UI 呈现** —— 缺任一方都会瞎一块。
- 所以：每开一个阶段任务 → `TaskCreate` 一条（`subject` 写人话，`activeForm` 写进行时）；
  状态推进 → `TaskUpdate` 同步；任务收口 → 标记 `completed`。
- **不要**试图把门禁结论塞进原生 `description` —— 那是编排语义，放自建里。
- 跨 agent 的正式协作消息可用 `SendMessage`（落盘 `~/.workbuddy/teams/<team>/inboxes/`）；
  编排内部的广播仍走 `cli.py say`（带 `type`/`artifact`/`meta` 等编排字段）。

**原生台账无需手动写**：`changes-index` / `artifact-index` / `audit-log` 由 WorkBuddy 自动落盘，
**照常 `finish --artifact` 登记即可**（自建登记带编排语义，原生那份是宿主权威事实）。
`/api/state` 的 `native` 块会把两者并排暴露，便于交叉验证。

**★ 增量改动（C0/C1）的门禁记录格式**：不开阶段状态机，但**留痕不裁**——
只核变更涉及的条目，记**一行**即可：

```
2026-09-12 14:03 | C0 fast-pass | 前端 | docs/02-frontend/src/format.js §数字格式化 | 不涉契约
2026-09-12 14:21 | C1 delta-pass | 后端+架构师会签 | 09-api-contract §3.2 新增 retry 字段 | 仅后端受影响
```

出 CONCERN 照常登记 `open-issues.md`，不放水。返修退回**同一**子 agent 续会话。

---

## 7. 体系自身运行指标（v3 · 2026-09-10 业界对标）

> 北极星思想：体系改造的收益必须可测量，否则无法回答"这轮改造值不值"。
> 数据源全部现成：看板 tokens 区（账本）+ gate-log.md + 04-defects.md。

每轮项目交付时（S7 产出 retro 时）在 retro 工件头部记三行，与上一轮对比：

| 指标 | 来源 | 含义 |
|---|---|---|
| 总 token | /api/state → tokens.total_tokens | 改造开销（红线：单轮涨幅 >20% 即失守，见 Brief §4） |
| 返工轮次 | 04-defects.md 的轮次记录 | 质量成本 |
| 门禁拦截数 | gate-log.md 中 FAIL/CONCERN 条数 | 门禁是否真在工作 |

**阈值决策（pivot / persevere / pause 简化版）**：总 token 或返工轮次**连续两轮上升 ≥30%**
→ 下一轮开工前必须三选一：pivot（改机制）/ persevere（再观察一轮）/ pause（冻结改造）。
