# Project Orchestrator · 多 Agent 协作开发框架

> 版本 `4.2` · 目标宿主 **WorkBuddy** · 上游协议源 [kimi0hhhh/project-orchestrator-skill](https://github.com/kimi0hhhh/project-orchestrator-skill) tag `v4.1`（协议母版见 universal/，ZCode 版为先行实现）
>
> v4.2 是**针对 WorkBuddy 的深度适配层**，不是上游版本的复刻：凡 WorkBuddy 原生已有的能力
> 一律下沉复用，自建只保留原生没有的部分（阶段状态机 / 门禁 / 变更分诊 / 参谋机制 / 角色契约）。

**一句话**：一套可安装的**多智能体交付框架**——「项目负责人 + 6 单责角色 + 按需参谋 + 阶段门禁」的编排协议，配 S0–S7 标准交付流程、实时可视化作战看板、全程可追溯的 token/事件账本。主 Agent 不下场干活，只做派发、验收、放行；单写手、单层编排、只读参谋、门禁不放水。

> 把需求说清楚、回答几个简短的追问，一段时间后回来，一个完整的产品项目已经躺在电脑里：PRD、接口契约、可运行代码、测试报告，还有一间记录六个 agent 如何协作的作战室。**代价**是它比你亲自下场显著更慢、更烧 token —— 见文末「诚实地说说优缺点」。

---

## 这是什么（四层）

不是提示词合集，是一份可安装的**协作开发框架**，四层各司其职：

| 层 | 内容 | 落点 |
|---|---|---|
| **协议** | 单写手、单层编排、只读参谋、门禁不放水——每条有 2025–2026 研究依据 | `SKILL.md` |
| **流程** | 6 份角色契约 + S0–S7 阶段状态机 + 参谋会回路 + 变更分诊（C0–C2 / L0–L2） | `.workbuddy/agents/`、`ORCHESTRATOR.md` |
| **可视化** | 实时作战看板：阶段进度、agent 卡片、协作消息流、作战地图 | `runtime/`（随 install 安装） |
| **追溯** | token 账本、事件总线、门禁留痕、retro 四问 | `runtime/lib/`、`.workbuddy/state/` |

框架加载后主 Agent 像项目负责人一样工作：

- **只派发、只验收**：写代码、写文档、做决策全部派发给 6 个单责角色（产品经理 / 架构师 / 前端 / 后端 / 开发组长 / 测试），每个工件只有一个写手；
- **流程强制**：S0 立项 → S1 需求 → S2 架构（接口契约 = 前后端唯一法律）→ S3 开发（文件隔离可并行）→ S4 集成 → S5 测试 → S6 终验 → S7 交付（三签缺一不交付）；
- **每阶段一道门禁**：PASS / CONCERN / FAIL 判定，CONCERN 必须登记未决项；
- **v4.1 两个提速机制**：**关键路径重叠**（S5 测试计划前置 + S4 增量评审）与
  **变更分诊 C0–C2**（小改动按比例付费，不必跑全流程）；
- **两个进阶机制（研究依据支撑）**：**星形参谋**——只读参谋一轮挑刺（generator–verifier 形态）；
  **动态编制 L0–L2**——简单任务不加人，不把多智能体 15× token 的成本烧在简单任务上。
- **v4.2 深度适配 WorkBuddy（原生优先）**：凡是 WorkBuddy 已经做了的，本体系**不再重复造轮子**——
  变更台账 / 产物台账 / 审计流水 / 真实 token 用量 / 会话存活 / 执行 trace 全部**读原生**；
  自建运行时退到**编排语义层**（门禁、阶段、放行、退回原因）。
  角色契约因为 WorkBuddy **没有**注入机制，改为**由主 Agent 内联进派发 prompt**
  （`cli.py dispatch` 一条命令生成 + 机械校验必填项）。
  详见 SKILL.md「WorkBuddy 原生能力映射」与 `docs/DESIGN.md` §11。

框架与平台解耦：换一个宿主工具，换的是适配层，不是框架。

## 快速开始

```bash
# 1. 移植到目标工作区（不覆盖同名文件）
bash "~/.workbuddy/skills/project-orchestrator/install.sh" <工作区绝对路径>
# Windows 也可用 install.cmd

# 2. 在会话里说任意一句唤醒语：
#    「启动主 Agent」/「接管项目」/「按 ORCHESTRATOR 继续」/「多 agent 协作开发」
# 3. 主 Agent 走唤醒流程：读 ORCHESTRATOR.md → 起看板 → 汇报当前阶段/谁在跑/下一步/待拍板项
# 4. 填 docs/PROJECT_BRIEF.md（产品输入书），放手让它跑
```

参考填充示例：`docs/PROJECT_BRIEF.md`

## 角色一览

| # | 角色 | 干什么 | 关键产出 |
|---|---|---|---|
| 00 | **主 Agent** | 派发、验收、分诊、升级裁决、范围裁剪 | 不产出文档，产出"跑完流程的产品" |
| 01 | **产品经理** | 需求挖掘、PRD、UI 设计，**终验实操** | 01-requirements / 02-prd / 03-ui-design |
| 02 | **架构师** | 功能架构、开发架构、前后端架构、**接口契约** | 05~09 / 10-arch-review（PM 会签） |
| 03 | **前端** | 产品壳 + 接口需求清单 | 11-frontend-code / 12-interface-request |
| 04 | **后端** | 核心业务逻辑 + 接口实现 | 13-backend-code / 14-api-impl-report |
| 05 | **开发组长** | 方向纠偏、代码评审、**缺陷分流**、构建 | 15-code-review / 16-build |
| 06 | **测试** | 用例设计与执行、缺陷单 | 17-test-plan / 18-report / 04-defects |

详细契约：`.workbuddy/agents/*.md`（由 install 移植进工作区）

## 三份协议（体系的地基）

| 协议 | 作用 |
|---|---|
| `handoff-schema.md` | 工件统一文件头 + 四块正文结构 + 回传信号格式 |
| `gate-rules.md` | 每个工件的 PASS / CONCERN / FAIL 判定条件与红线 |
| `revision-loop.md` | **缺陷分流表**（最关键）+ 返工轮次与升级规则 |

## 站在谁的肩膀上

这套框架的设计不是拍脑袋，是两股开源力量的收敛：**开源 skill 集**（方法论直接进角色契约）与 **2025–2026 多智能体研究**（每条写清：核心发现 → 我们采纳了什么 / 在哪里持保留意见）。

### 开源 skill 引用

角色契约为每个角色预置"推荐 skill 清单"，派发时由主 Agent 点名激活。框架**不打包、不修改**这些 skill，只声明引用与兼容——换你自己的等价 skill 也能跑。
本机实际安装位置：`~/.zcode/skills/`（WorkBuddy 桌面端兼容的 skill 根目录），下列名字已逐个实查存在：

| skill 集 | 引用的 skill | 服务的角色 |
|---|---|---|
| **pm-skills** | `create-prd` · `prioritization-frameworks` · `pre-mortem` · `retro` · `user-stories` · `interview-script` · `user-personas` · `test-scenarios` · `dummy-dataset` · `sql-queries` | 产品经理（S1/S6）· 测试（S5） |
| **Matt Pocock skill 集**（经 `setup-matt-pocock-skills` 安装） | `codebase-design` · `domain-modeling` · `tdd` · `implement` · `prototype` · `code-review` · `triage` · `diagnosing-bugs` · `resolving-merge-conflicts` · `research` · `grill-with-docs` | 架构师（S2）· 前后端（S3）· 开发组长（S4）· 会签调研 |

契约里列了但本机没装的 skill，**退化为契约自带方法论**，不阻塞派发。
致谢这两个开源集的作者——本框架的角色方法论大量站在它们肩膀上。

### 研究依据

| 来源 | 核心发现 | 我们的取舍 |
|---|---|---|
| [Anthropic · How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) | 多智能体约 **15× token**；编码任务真正可并行的部分远低于研究 | 采纳：默认不并行，仅 S3 文件隔离的前后端并行；派发前先分诊（L0–L2） |
| [Anthropic · Agent Teams](https://code.claude.com/docs/en/agent-teams)（2026-02） | 3–5 teammates、禁嵌套、顺序/同文件工作回单会话 | 采纳：单层编排用契约 `tools` 白名单结构堵死，不靠提示词自觉 |
| [Cognition · Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents) | 并行写手交换的是彼此看不见的**隐含决策**，合并即冲突 | 采纳：每个工件单写手。修正：不退回单线程——用门禁 + 只读参谋保留多视角 |
| [Cognition · Multi-Agents: What's Actually Working](https://cognition.com/blog/multi-agents-working)（2026-04） | 生产中真正有效的是**零共享上下文的干净评审 agent** | 采纳：参谋互不对话、不写工件、不担门禁——"只读参谋"正是此形态 |
| [LangChain · Benchmarking multi-agent architectures](https://www.langchain.com/blog/benchmarking-multi-agent-architectures) | supervisor 中继层是主要损失点，修复交接后 +50% | 采纳：只允许一层编排，主 Agent 中继时引用原文不改写 |
| [Google · Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296) | 顺序任务上多智能体全线 **−39~70%**；可并行 +80.9% | 采纳：架构契约阶段（S0–S2）绝不并行；分诊拿不准就降档 |
| [Dochkina · Drop the Hierarchy](https://arxiv.org/abs/2603.28990) | 预指派职级人设是负资产（自组织 +14%） | 采纳：参谋 prompt 只给"视角 + 挑战格式"，不写"首席/总监"剧本 |
| [等预算对照研究](https://arxiv.org/abs/2604.02460) | 不锁 token 预算的对照，测到的是算力不是架构 | 采纳：复现指南强制等预算 |
| [MAST 失败分类](https://arxiv.org/abs/2503.13657) | 7 个 SOTA 多智能体系统（含 MetaGPT/ChatDev 等 SDLC 框架）整体失败率 **41–86.7%** | 回应：承认本框架形似 SDLC 角色扮演，靠门禁判定、工件编号、契约↔代码对齐抽查与之切割 |

一句话总结这九条的公共结论：**多智能体的失败几乎都发生在"写"的环节**——
所以这套框架把并行限制在文件隔离的 S3，把"写"之外的一切（评审、挑战、观察）都做成只读。

## 五条铁律

违反任何一条，整套框架失效：

1. 主 Agent 不下场干活——你一动手就没人验收了；
2. 不并行派发会写同一工件的 agent——读可并行，写/合并永不；
3. 门禁不放水——CONCERN 登记未决项，不用"差不多"换进度；
4. 每个子 agent 只看它该看的文件（**精确到节**）；
5. 只在四种情况打断用户，其余一律自行推进。

## 可视化看板

不开文件，浏览器里直接看多 agent 怎么协作——阶段、卡片、消息流、token 账本全程可见：

```bash
python runtime/board.py open      # 本机手动：起服务并自动打开浏览器
python runtime/board.py wmi       # 主 Agent 在会话里用这个（受限沙箱下 detached 活不过调用）
python runtime/board.py status    # 只检查，不起
python runtime/board.py stop      # 停止
```

- **指挥台**：阶段 / 完成度 / 待处理指令，一键打开作战地图；
- **子 agent 卡片**：状态、进度、模型**三口径**（配置 / 声明 / 实际）、静默计时、中断性质分级；
- **协作消息流**：交付/进度实时置顶，工件点击即看；
- **Token 账本**：按角色消耗条形图。

**别让用户双击 `runtime/ui/index.html` 本地打开**（`file://` 下没有后端，页面永远是死的）。

## 开发验证（简述）

框架经过多轮真实项目开发验证（对照实验 + 端到端双流水线 + 两个真实产品全流程）：
参谋机制在草稿期拦下过真实设计缺陷（如"无后端产品却写留存率北极星"），
门禁拦截与返修回路按设计工作。

**诚实边界**：自建对照实验规模有限（**n=2、非等预算**），**只作方向性参考，
不作为权威结论**——设计正确性主要建立在上一节的研究依据之上。
已知遗留问题见 `docs/ROADMAP.md`。

## 诚实地说说优缺点

**优点（开发验证，方向性证据）**

1. **能独立落地整个产品**：从需求→PRD→契约→可运行代码→测试全链路工件一次交付到位；
2. **产品质量护栏有效**：参谋在草稿期拦下过真实设计缺陷，门禁与缺陷定性分流按设计工作；
3. **过程可观察**：看板实时呈现阶段/卡片/消息流/token 账本，多 agent 交互不再是黑盒。

**代价（这是设计代价，不是 bug）**

1. **显著更慢**：多轮派发 + 门禁 + 返修，端到端时间显著长于单 agent 直接干；
2. **token 消耗大**：参谋组、返修轮、看板轮询都在烧 token。

**什么任务不该用它**：决策链单一、切不开的任务；只想要补丁不想要工件链；
token/时间预算紧到装不下返修轮。命中任一条，请用单角色直接干——分诊 L0 存在的意义就是把这条规则写进框架。
工作量不到一天的改动走**变更分诊快车道**（C0 轻改 = 1 次派发 + 1 行门禁记录；
C1 小需求仅在契约变更时会签），不必也不该跑全流程。

## 目录

```
SKILL.md                 框架本体（编排协议 + 流程纪律）
ORCHESTRATOR.md          主编排手册（阶段状态机 + 派发命令 + 分诊）
AGENTS.md                子 agent 开工必读
ALL-IN-ONE.md            单文件全量版（给不支持读多文件的工具用）
USAGE.md                 给其他 AI 工具接入用
SYNC-RECEIPT-v4.1.md     v4.1 上游机制移植回执
SYNC-RECEIPT-v4.2.md     v4.2 WorkBuddy 深度适配回执（原生映射 + 验证记录）
agents/                  7 份角色契约  → .workbuddy/agents/
protocols/               3 份协作协议  → .workbuddy/protocols/
templates/state/         状态模板      → .workbuddy/state/
runtime/                 协作运行时（看板/账本/看门狗）→ runtime/
  └── lib/contract.py    ★ 契约内联派发（v4.2 新增：内联 + pre-flight 代码校验）
tools/
├── build-all-in-one.py  重生成单文件版（改完分散文件必须重跑）
└── probe-host.py        ★ 宿主机能力探测（换宿主/升级后先跑它再谈适配）
docs/
├── PROJECT_BRIEF.md     产品输入书模板      ← 会铺进工作区
├── examples/            填充示例（本地资产，不入库）   ← 会铺进工作区
├── ROADMAP.md           路线图 + 已知遗留问题 + 差异裁决
├── DESIGN.md            设计决策与依据（研究引用 / 星形参谋 / L0–L2）
├── CREDITS.md           开源 skill 引用关系与替换方式
├── 00-charter/          S1 需求产物
├── 01-architecture/     S2 架构产物（含接口契约）
├── 02-frontend/         S3a 前端
├── 03-backend/          S3b 后端
├── 04-integration/      S4 集成与构建
├── 05-qa/               S5 测试
└── 06-acceptance/       S6 终验
install.sh / install.cmd
```
