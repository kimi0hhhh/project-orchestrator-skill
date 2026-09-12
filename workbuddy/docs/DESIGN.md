# 设计决策与依据 / DESIGN

> 每条设计决策都标注了它的依据：外部研究（带链接）或本仓库实测（见 `ROADMAP.md`「开发验证」）。
> WorkBuddy 版 `4.1`，协议源 [kimi0hhhh/project-orchestrator-skill](https://github.com/kimi0hhhh/project-orchestrator-skill) 的 `docs/DESIGN.md` / `docs/ARCHITECTURE.md`。

## 1. 为什么是"6 个单责角色"而不是"6 个角色团队"

**依据**：Anthropic《How we built our multi-agent research system》——多智能体消耗 ~15× tokens，
编码任务真正可并行的部分远少于研究；LangChain 多智能体基准——supervisor 的中继层丢上下文且更贵；
MAST 失败分类——"agent 间错位"（隐瞒信息 / 忽略他人输入 / 任务跑偏）是核心失败类别，
字面模仿 SDLC 的角色扮演框架（ChatDev/MetaGPT 系）实测失败率 41–86.7%。

**结论**：6 个单责角色 + 门禁，而不是每个角色扩成合写团队。团队化只在"**主笔唯一 + 参谋只读**"的形态下引入（见 §5）。

## 2. 为什么单层编排、禁止嵌套

**依据**：LangChain《Benchmarking multi-agent architectures》——supervisor 的转述层是主要损失点，
修复交接后 +50%；每层中继 = 一次上下文转述 = 一次决策衰减。

**实现**：角色契约 frontmatter 的 `tools` 不含 Agent 工具——**结构上堵死，不靠提示词自觉**。

## 3. 为什么 PM×架构师会签、三签交付

**依据**：MAST 的"任务验证"类失败（过早终止 / 验证薄弱）；框架实测中会签拦下的最高频问题是
"需求缺陷被当成开发 bug"——缺陷定性分流表因此只归开发组长。

## 4. 为什么"读可以并行，写/合并不行"

**依据**：LangChain 方法论文章；Cognition《Don't Build Multi-Agents》的 Flappy Bird 案例
（两个并行写手各画各的，合并即冲突）。因此 S3 允许前后端并行（文件天然隔离），
同一工件的写作权永不并行。

## 5. 星形参谋（2026 收敛形态）/ Star advisors

**依据**：Cognition 2026-04《Multi-Agents: What's Actually Working》承认生产中真正有效的是
**零共享上下文的干净评审 agent**（generator–verifier，~2 缺陷/PR、58% 严重级）；
Anthropic Agent Teams（2026-02）的口径也是单写手 + 只读验证者 + 禁止嵌套。

**协议**：草稿 → 主 Agent 派 **2–3 个只读参谋**并行挑刺 → 合并去重 → 主笔**一次**返修 → 门禁照常。

### 5.1 参谋会运行回路

```
主角色（唯一写笔）──交付草稿──▶ 主 Agent（编排）
                                   ├─▶ 参谋A（只读）──▶ 挑战清单 ≤15 行（BLOCK/SHOULD/NIT）
                                   └─▶ 参谋B（只读）──▶ 挑战清单 ≤15 行（互不对话）
        主 Agent：合并去重 · 判定吸收/驳回/升级会签
主笔 ◀──退回返修（一次）── 主 Agent
主笔 ──定稿 + 逐条回应表──▶ 主 Agent ──▶ 门禁判定 PASS/CONCERN/FAIL
```

### 5.2 纪律（违反即机制失效）

- 参谋**不写工件、不担门禁、互不对话**；
- 主角色保持**唯一写笔**，横向一致性由主角色自己收敛；
- 挑战与契约冲突时**契约赢**（改契约走会签）；
- 参谋 **2–3 只**、挑战清单 **≤15 行**、**只挑战一轮**、主笔**只返修一次**；
- **S6 终验禁开参谋**（签字必须单一）；
- 参谋 prompt 只给「**视角 + 挑战格式**」，**不写**「首席/总监」之类职级剧本。

### 5.3 反向修正

Dochkina 25,000 次实验（arXiv:2603.28990）证明**预指派职级人设是负资产**（自组织 +14%），
因此参谋 prompt 只给"视角 + 挑战格式"，不写死职级剧本。

**实测**：吸收率 81%；参谋在草稿期拦下过真实设计缺陷（如"无后端产品却写留存率北极星"）。

## 6. 动态编制（分诊 L0–L2）/ Dynamic staffing

**依据**：Google《Towards a Science of Scaling Agent Systems》（arXiv:2512.08296，180 配置）
——顺序任务上多智能体全线 **−39~70%**，中心化编排只在可并行任务 +80.9%，
且有预测模型能在 87% 未见任务上选对架构；等预算研究（arXiv:2604.02460）——多智能体表观收益多为未记账算力。

**协议**：评估维度是两个——**工作量** 与 **可分解性**（能否切成互不抢决策的块）。
**拿不准就降档**（高估的代价确定、低估被门禁拦截）；阈值靠 retro 回调。

```
阶段任务
   │
   ▼
分诊：工作量 × 可分解性（复杂 ≠ 可拆）
   ├─ 默认（指标低于阈值）────────▶ L0 单角色（可加迭代次数，不加人）
   ├─ 命中触发词（资金/权限/新市场/多端）─▶ L1 主角色 + 1~2 只读参谋
   └─ 多项命中 且 可分解 ──────────▶ L2 主角色 + 3 参谋一轮
                                        └─ 仅 S3 模块拆分（文件隔离 + 机器可验证）→ 文件锁模式
   L0 / L1 / L2 ──▶ 门禁 PASS/CONCERN/FAIL
                      └─ retro：吸收率 <20% 降档；L0 频繁返工 升档 → 回到分诊
```

### 6.1 反模式清单

- 把**顺序耦合**的工件（架构契约）拆给多个 agent 写 —— 加人有害；
- 给"只想要一个补丁"的任务配参谋组 —— 分诊 L0 存在的意义就是拦住它；
- 参谋挑刺超过一轮 —— 会退化成"主笔被反复打断"，不是评审；
- 用参谋替代门禁 —— 参谋无判定权，门禁必须单点。

## 7. 关键路径重叠（v4.1）

**依据**：依赖提前解除的工件并行，省的是**墙上时钟**；依赖没解除的并行，省的只是返工。

- **17-test-plan 只依赖契约**（`09-api-contract` + `02-prd`），不依赖实现代码 →
  可在 **S2 契约门禁 PASS 后**与 S3 并行起草；
- **dev-lead 的草稿评审**只依赖"该端草稿完成检查点" → 可在 S3 期间分轴介入，
  最后只做集成裁定与 15/16 定稿。

**护栏不重叠**：并发预算 ≤3（qa 进场时前后端已占两席，正好满编；外援在场则 qa 推迟）；
PM×架构师会签**绝不并行**；S6 终验**不开参谋、不并行**。

## 8. 流程开销要配得上改动大小（v4.1 变更分诊）

**依据**：阶段状态机是为「新需求面」设计的。对单点轻改跑全流程，**门禁的固定开销反而超过质量收益**。

**协议**：入口变更分诊 **C0 / C1 / C2**（判据见 `SKILL.md`「变更分诊」）。
**增量模式只裁流程步数，不裁门禁判定与留痕。**

**关键的不对称**：C0/C1 判不准时**按 C1 走**（与阶段分诊「拿不准就降档」方向相反）——
因为这里低估的代价不再被门禁兜住：**契约漂移在集成期才暴露**，那时改起来贵一个量级。

## 9. 存活判据（v4.1，运行时）

**依据**：看门狗原来的判据是"静默超时"（启发式），而宿主客户端自己把**精确**状态记在
`~/.zcode/cli/db/db.sqlite`：`turn_usage`（回合生命周期）、`tool_usage`（工具执行）、
`model_usage`（实际模型 + 思考档）。这些把"活着 / 结束 / 异常"从**猜**变成**读**。

**协议（判据优先级从硬到软）**：

1. 客户端 DB 事实：进行中 → 活着；异常结束 → 立即告警；回合已完成 → 收口为 done；
2. 会话日志近期有写入 → 活着（次优证据）；
3. **WorkBuddy 会话级原生判据 → 否决层**（**v4.2 新增**，见 §11.4：只否决、不断言）；
4. 静默超时 → 兜底。

**v4.2 变更提示**：第 3 层插在静默兜底之前，专门治「误报」；它证明的是「会话在活动」，
不是「某个子 agent 活着」。完整的四层判据与语义边界见 §11.4。

**诚实边界**：回合进行中时，**「在深思」与「已挂死」从外部无法区分** ——
这类只能表现为「**疑似停滞**」（`stalled`），不能断言「中断」。
中断性质分三级：`dead`（进程号确认消失，较硬）/ `stalled`（疑似，无会话证据）/
`abnormal`（客户端回合异常结束）。

**另一条必须堵的漏洞**：**服务自己宕机期间的静默，不算 agent 的错**。
服务一停，所有心跳都打不进来、静默白白累积；服务一恢复就会把其实一直在干活的 agent
集体判成中断。修法是 `age_seconds(..., since_epoch=SERVER_START)` ——
**静默只统计"服务确实在运行"的那段时间**。

## 10. 已知取舍与未解问题

- 对照实验 **n=2**，方向一致但**无统计学意义**，推广前应做 n≥5 + 双评审；
- 参谋组只在高价值任务开：+13% 质量对应 2.2× 成本；
- 工件变多后"契约精度向代码传导"会衰减，故前端完工后加"契约↔代码逐条对齐"抽查门禁（**本版未落地**）；
- 三条已知遗留问题（见 `ROADMAP.md`，v4.2 已逐条重新评估）：
  **pid 未登记 —— 仍未根治**（需宿主暴露子 agent 进程号）；
  会话日志通道易失效 —— v4.2 已加第二条独立通道；
  240s 兜底误报 —— v4.2 已加机制层否决。

## 11. WorkBuddy 原生适配层（v4.2）

### 11.1 问题：上游机制在 WorkBuddy 上不存在

上游 ZCode 版把 `agents/<name>.md` 作为子 agent 的 frontmatter 定义，**契约由宿主自动注入**。
WorkBuddy 没有这个机制：

- 子 agent 一律以 `subagent_type: general-purpose` 派发；
- `plugins/*/agents/*.md` 里的 agent 类型确实能当 `subagent_type` 用，
  但那是**应用启动时注册**的 —— 实测：会话内向工作区 `.workbuddy/agents/` 写入
  `probe-agent.md` 后立即派发，返回 `Task agent probe-agent is not available`；
- 而编排的派发发生在**同一会话内**，不可能中途重启应用。

**→ 硬套上游机制不可行。但上游机制的本质是「契约必须进入子 agent 的上下文」，
这个目标是可以达成的，只需换手段。**

### 11.2 解法：契约内联（`runtime/lib/contract.py`）

| | 上游 ZCode | 本版 v4.2 |
|---|---|---|
| 机制 | 宿主注入 frontmatter | 主 Agent 显式内联进 `prompt` |
| 可靠性 | 依赖宿主实现 | **依赖代码**，与宿主解耦 |
| 可裁剪 | 否（整份注入） | 是（`--section`，实测 10.1 KB → 2.4 KB） |
| pre-flight | 文档约定，靠自觉 | **代码校验**，缺项 exit 1 |

顺带把「派发三要素 + 上报要求 + 完成判据」做成**必填字段**：
`validate()` 缺一项即拒发。这把一条「模型容易忘的规则」变成了「工具不会忘的约束」——
凡是能让代码兜底的事，都不该指望模型记住。

### 11.3 解法：原生账本下沉（不重复造轮子）

WorkBuddy 对每条会话**自动**落盘，实测确认（2026-09-12）：

| 台账 | 路径 | 实测内容 |
|---|---|---|
| 变更 | `changes-index/<cid>.json` | 6 条，332 行增量，含 checkpointId/detailRef |
| 产物 | `artifact-index/<cid>.json` | 4 条，含 sourceTool=`PresentFiles`、toolCallId |
| 审计 | `audit-log/YYYY-MM-DD.jsonl` | 单日 200–550 KB |
| 用量 | `workbuddy.db` → `session_usage` | `used=197510`/`size=300000`，`credit_json` 逐请求 credits |
| 会话 | `workbuddy.db` → `sessions` | `status=working`、`cwd` 精确匹配、`model`、`thought_level` |
| trace | `traces/<port>/trace_*.json` | 单个可达 1.7 MB |

**处置原则：原生是权威源，自建退到编排语义层。** 二者不是替代关系：
自建记录带门禁/阶段/放行语义，原生只有「文件变了/产物出来了」。
所以 `snapshot()` 新增 `native` 块**旁路暴露**原生事实，既有自建记录**一个不删**。

**为什么不删**：删了会丢编排语义，且 `ui/index.html` 是本地 104.6 KB 深度定制，
UI 误读是本项目最敏感的回归类型。**下沉读取 ≠ 推倒重来。**

### 11.4 解法：看门狗原生否决层

四层判据，每层只在拿到硬证据时给结论：

```
pid 确认活着 ────────────────────────────────► 永不判中断
  ↓ 否则
zcode per-agent（turn_usage/tool_usage/model_usage）► alive / abnormal / finished（最精确）
  ↓ 无据
zcode 会话日志（rollout/*.jsonl）    ─────────────► alive（次优）
  ↓ 无据
WorkBuddy 会话级（sessions+session_usage）────────► **否决**（v4.2 新增）
  ↓ 无据
静默超时 ────────────────────────────────────► stalled（仅「疑似」，非结论）
```

**否决层的语义必须精确，否则会用错**：WorkBuddy 子 agent 是**同进程内**运行、
共享**同一条 session 记录**，`sessions` 里没有 per-subagent 行。所以它
**只能否决、不能断言** —— 它证明的是「这条会话在活动」，而不是「第 3 号子 agent 活着」。
正确用法：会话确在活动时，**不得**因单 agent 静默判其停滞。这恰好治好了
ROADMAP 遗留问题③（240s 误报）。真正的 per-agent 判据仍由 zcode 层提供，**两层互补**。

### 11.5 已知取舍

- **契约内联的代价**：每份派发 prompt 多 2–10 KB（取决于是否 `--section` 裁剪）。
  换来的是确定性——不依赖宿主实现、不依赖子 agent 自觉。这个交换是划算的。
- **原生层是会话级的**：无法回答 per-agent 存活性。要真正的 agent 级判据，
  仍需宿主暴露子 agent 进程号（见 ROADMAP 遗留问题①，**仍未根治**）。
- **两个 token 口径并存**：自建是字节估算，`native.usage` 是真实值。
  目前**未做统一**，只在文档里标注来源。并排显示时必须显式区分，否则会被当成同一个数。

## 主要外部参考

| 来源 | 关键数字 |
|---|---|
| [Anthropic · multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) | 15× tokens；+90.2% 研究评测；编码并行度低 |
| [Anthropic · Agent Teams](https://code.claude.com/docs/en/agent-teams)（2026-02） | 3–5 teammates；禁嵌套；顺序/同文件工作回单会话 |
| [Cognition · Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents) | 隐含决策冲突；单线程线性 agent |
| [Cognition · What's Actually Working](https://cognition.com/blog/multi-agents-working)（2026-04） | 零共享上下文评审 ~2 bug/PR；反对并行写手 |
| [LangChain · Benchmarking](https://www.langchain.com/blog/benchmarking-multi-agent-architectures) | swarm>supervisor；中继层是损失点 |
| [Google · Scaling Agent Systems](https://arxiv.org/abs/2512.08296) | 顺序任务多智能体 −39~70%；可并行 +80.9%；87% 选对架构 |
| [Dochkina · Drop the Hierarchy](https://arxiv.org/abs/2603.28990) | 自组织胜预指派角色 +14%；涌现层级 ≤2 |
| [等预算研究](https://arxiv.org/abs/2604.02460) | 同预算下单 agent 不输多智能体 |
| [MAST 失败分类](https://arxiv.org/abs/2503.13657) | 14 失败模式；SDLC 角色扮演框架失败率 41–86.7% |
| [AgentPrune](https://arxiv.org/abs/2410.02506) | 通信冗余 28–73% 可裁剪 |
