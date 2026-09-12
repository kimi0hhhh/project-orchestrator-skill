# 引用与致谢 / CREDITS

> 框架**不打包、不修改**第三方 skill，只声明引用与兼容。换你自己的等价 skill 也能跑。

## 开源 skill 集

### pm-skills

| # | skill | 服务的角色 / 阶段 |
|---|---|---|
| 1 | `create-prd` | 产品经理（S1 第二步 PRD） |
| 2 | `user-stories` | 产品经理（S1 需求挖掘） |
| 3 | `interview-script` | 产品经理（S1 需求澄清） |
| 4 | `user-personas` | 产品经理（S1 目标用户） |
| 5 | `prioritization-frameworks` | 产品经理（S1 优先级 P0/P1/P2） |
| 6 | `pre-mortem` | 产品经理（S1 风险前置） |
| 7 | `retro` | 主 Agent（S7 迭代回顾四问） |
| 8 | `test-scenarios` | 测试（S5 用例设计）· 产品经理 |
| 9 | `dummy-dataset` | 测试（S5 假数据构造） |
| 10 | `sql-queries` | 测试 / 后端（数据校验） |

### Matt Pocock skill 集

经 `setup-matt-pocock-skills` 安装。

| # | skill | 服务的角色 / 阶段 |
|---|---|---|
| 1 | `codebase-design` | 架构师（S2 架构） |
| 2 | `domain-modeling` | 架构师（S2 领域建模） |
| 3 | `tdd` | 前端 / 后端（S3） |
| 4 | `implement` | 前端 / 后端（S3） |
| 5 | `prototype` | 前端（S3 快速验证）· 架构师 |
| 6 | `code-review` | 开发组长（S4 评审） |
| 7 | `triage` | 开发组长（S4 缺陷分流） |
| 8 | `diagnosing-bugs` | 前端 / 后端（S4 返修） |
| 9 | `resolving-merge-conflicts` | 开发组长（S4 集成） |
| 10 | `research` | 会签调研（PM × 架构师） |
| 11 | `grill-with-docs` | 会签调研（文档挑刺） |

## 安装位置与替换方式

本机实际安装位置：`~/.zcode/skills/`（WorkBuddy 桌面端兼容的 skill 根目录），
上列名字已逐个实查存在。派发时由主 Agent 点名激活（Skill 工具按名调用）。

替换方式：

1. **换等价 skill**：把对应角色契约「推荐 skill」节里的名字改成你的等价 skill 名即可，
   框架不校验名字——契约里列了但本机没装的，**退化为契约自带方法论**，不阻塞派发；
2. **关掉引用**：契约里删掉对应条目即可，方法论退回契约正文自带的部分；
3. **加新 skill**：在契约里追加名字，并在 `SKILL.md`「开源 skill 引用」节登记归属角色。

## 协议来源

编排协议与流程定义移植自
[kimi0hhhh/project-orchestrator-skill](https://github.com/kimi0hhhh/project-orchestrator-skill)
（tag `v4.1`，ZCode 版为先行实现）。本目录是其 **WorkBuddy 版**（移植落点为
`.workbuddy/` 体系 + `install.sh` 链路），协议语义保持一致，平台适配层不同。

## 研究致谢

设计依据的九项外部研究逐条列在 `DESIGN.md` 与 `README.md`「研究依据」表中。
致谢 pm-skills 与 Matt Pocock skill 集的作者——本框架的角色方法论大量站在它们肩膀上。

## 许可

引用关系与兼容声明随本框架发布；第三方 skill 的许可以其各自仓库为准。
