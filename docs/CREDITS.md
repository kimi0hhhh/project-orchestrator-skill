# 引用与致谢 / CREDITS

## 1. 引用的开源 Skill（运行时按需点名调用，不随本仓库分发）

本框架的角色契约里为每个角色预置了"推荐 skill 清单"，派发时由主 Agent 点名激活。这些 skill 来自独立的开源 skill 集，**本仓库不打包、不修改它们**，只声明引用关系：

**产品/测试类（pm-skills 集）**：
- `create-prd` — PRD 方法论（S1 产品经理点名）
- `prioritization-frameworks` / `pre-mortem` / `retro` / `user-stories` / `interview-script` / `user-personas` — 需求挖掘与优先级（S1/S6）
- `test-scenarios` — 测试场景方法论（S5 QA 点名，实测对用例结构有直接提升）
- `dummy-dataset` / `sql-queries` — 造数与数据验证（S5）

**编码类（Matt Pocock 开源 skill 集，经 setup-matt-pocock-skills 安装）**：
- `codebase-design` / `domain-modeling` — 架构师（S2）
- `tdd` / `implement` — 后端（S3）
- `prototype` — 前端（S3）
- `code-review`（双轴评审）/ `triage` — 开发组长（S4）
- `diagnosing-bugs` / `resolving-merge-conflicts` — 开发排障
- `research` / `grill-with-docs` — 会签挑刺与调研

> 若你安装的 skill 集不同，只需在角色契约的"推荐 skill"行里换成你自己的等价 skill 名——框架只依赖"派发时点名激活"这个机制，不依赖具体 skill。

## 2. 平台与运行时

- **ZCode**（本版本的目标平台）——skill 机制、Agent 工具、子 agent 契约加载；
- **OpenCode** —— 运行时看板的早期同源实现（runtime 曾由 OpenCode 版构建脚本生成），OpenCode 版 skill 在路线图中；
- 运行时看板依赖：Python 标准库（http.server / sqlite3 / threading），无第三方运行时依赖。

## 3. 研究与工程文章（设计依据，完整清单见 DESIGN.md）

- Anthropic Engineering — *How we built our multi-agent research system*；*Effective context engineering for AI agents*；*Building a C compiler with a team of parallel Claudes*；Agent Teams 文档
- Cognition — *Don't Build Multi-Agents*（Walden Yan）；*Multi-Agents: What's Actually Working*（2026-04）
- LangChain — *Benchmarking multi-agent architectures*；*How and when to build multi-agent systems*；*Choosing the Right Multi-Agent Architecture*（2026-01）
- Google Research — *Towards a Science of Scaling Agent Systems*（arXiv:2512.08296）
- Dochkina — *Drop the Hierarchy and Roles*（arXiv:2603.28990）
- Tran & Kiela — 等预算对照（arXiv:2604.02460）
- MAST — *Why Do Multi-Agent LLM Systems Fail?*（arXiv:2503.13657）
- AgentPrune — *Cut the Crap*（arXiv:2410.02506）
- METR — *Time Horizon* 系列测量

## 4. 实验方法致谢

盲评方法（评审者不知道产出条件分组）与等预算对照的必要性，分别受启发于机器学习标准评测实践与 HAL（Holistic Agent Leaderboard，arXiv:2510.11977）的成本匹配评测主张。
