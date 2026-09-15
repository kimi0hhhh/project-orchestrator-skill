<!-- OpenCode 版：由 tools/build_opencode.py 生成 -->

# 能力地图（Capability Map）· v4.1

> 谁该用哪个外部能力、以什么纪律用。**工件契约与门禁规则永远优先于任何外部 skill 的模板。**
> 外部能力清单（2026-09-11 安装，随包携带）：mattpocock/skills、phuryn/pm-skills、
> agency-agents（**279** 个专家 agent，索引见 `role-pool.md`）、codebase-memory MCP
> （15 个代码图工具）、i-have-adhd（输出风格）。**随包 skill 共 94 个**。
> 注意：skill 与子 agent 定义都在**会话启动时加载**，新装/新改的要新开会话才生效。
<!-- orch:keep -->
> 两个客户端口径的差异：ZCode 用 `Skill` 工具 + `subagent_type`；OpenCode 用 `skill` 工具
> （小写）+ `task` 工具（agent 名 = 文件名）。路径 `.zcode/`（ZCode）与 `.opencode/`（OpenCode）同构。
<!-- orch:keep-end -->

---

## 0. 三条总纪律（违反即产生"双份真相"）

1. **工件结构优先**：本体系的 `handoff-schema.md`（工件注册表 + 四块正文 + 回传信号）与
   `gate-rules.md` 是交付契约。外部 skill 只提供**方法、检查项、话术**，**不得改变交付物的
   结构与门禁判据**。例：pm-skills 的 `create-prd` 是 8 段模板，我们仍按 `02-prd` 的
   「四要素 + 不做清单 ≥5 条」产出；skill 里的提问清单只用来**补全**内容。
2. **交互式 skill 降级为自检清单**：外部 skill 里凡是要"问用户"的流程，子 agent **无法执行**
   （子 agent 只与主 Agent 对话，不直接接触用户）→ 改成① 自检清单，或 ② 把问题 `say` 给主 Agent
   由其决定是否打断用户（受铁律 5 的四种打断场景约束）。
3. **结构性代码问题先查图**：谁调用谁、模块边界、影响面、入口在哪 —— 优先用 codebase-memory
   MCP 的 `get_architecture` / `search_graph` / `trace_path` / `get_code_snippet`，不要
   逐文件 grep+read（官方基准：省 10~120 倍 token）。文本字面搜索（找字符串、配置、
   非代码文件）仍用 grep。**首次用前先 `list_projects` 看目标仓库是否已索引**，
   未索引则 `index_repository`。

---

## 1. 主 Agent（orchestrator）

| 能力 | 用在哪 | 纪律 |
|---|---|---|
| `grill-me` / `grilling`（mattpocock） | **S0 立项**：把含糊的 Brief 逼问清楚（正是"Brief 缺核心信息"场景，属铁律 5 允许的打断） | 只在 S0 与需求重大变更时用；问题分批问，别一次抛 20 个 |
| `to-spec` / `to-tickets` | S0→S1 之间：把对话/ Brief 转成需求骨架或工单 | 产出**交给 PM 当输入**，不替代 `01-requirements` |
| `wayfinder` | 超大项目（超过单会话容量）时把工作拆成"决策票"作为作战地图 | 与 `.opencode/state/board.md` + `runtime/projects/<pid>/plan.json` 对齐，别另起一套 |
| `handoff`（mattpocock） | 会话交接：把当前上下文压缩成交接文档 | 用于「跨会话接管」，与唤醒流程配合 |
| `retro`（pm-skills/pm-execution） | **S7 迭代回顾**（对应 `docs/retro.md` 四问） | 用它的问法，产出仍落 `docs/retro.md` |
| `stakeholder-map`（pm-skills） | 干系人多、需要判断"该找谁拍板"时 | 只在真的多方时用 |
| `i-have-adhd`（i-have-adhd） | **给你（用户）写汇报**时切换输出风格：先给下一步动作、多步编号、具体时间估计 | 用户显式要求才用；不要用在工件正文里 |
| `summarize-meeting`（pm-skills） | 用户贴了会议记录/长对话，要提炼成输入 | 提炼结果进 Brief 或工件，别单独漂流 |

**agency-agents 外援**（临时专项，不进固定角色）：需要独立视角时按需派发，例如
`reality-checker`（打脸检查）、`accessibility-auditor`（可访问性）、
`security-architect` / `application-security-engineer`（安全）。
派发前先确认 slug 在 `role-pool.md` 里存在（索引里没有的不要凭记忆编）。

---

## 2. 产品经理（product-manager）

**pm-skills 基本就是为这个角色写的**（68 个里绝大多数命中 PM 生命周期），但按纪律 1 用"方法"：

| 阶段 | 可用 | 说明 |
|---|---|---|
| S1 需求 | `interview-script`、`summarize-interview`、`user-personas`、`user-segmentation`、`sentiment-analysis` | 用来**设计提问与提炼**，产物仍写进 `01-requirements` 四段式 |
| S1 PRD | `prioritization-frameworks`（RICE/ICE/Kano/MoSCoW）、`pre-mortem`（风险老虎/纸老虎）、`wwas`、`job-stories`、`user-stories` | 提供**分析框架**；PRD 结构照我们的四要素 + 不做清单 |
| S1 UI | （pm-skills 无 UI 设计）→ 用我们自己的 `03-ui-design` 四态要求 | — |
| S6 终验 | `test-scenarios`（从用户故事推场景）、`metrics-dashboard`（定指标） | 终验走查清单可引用 |

**禁**：`create-prd` 的 8 段模板**不得**替代 `02-prd` 结构（否则 G-PM-02 直接 FAIL）。

---

## 3. 架构师（architect）

mattpocock 的工程 skill 与这个角色最契合的一组：

| 能力 | 用在哪 |
|---|---|
| `codebase-design` | 定模块边界/接口深度（"deep module"词汇表）→ `07/08-*-arch` 的模块划分 |
| `domain-modeling` | 统一术语表 + ADR → 直接对应 `09-api-contract` 的字段术语与 `10-arch-review` 的决策记录 |
| `research` | 技术选型要"高可信一手来源"时（带出处落盘）→ 写进 `06-system-arch` 的选型理由 |
| `grill-with-docs` | **会签挑刺**：把它的逼问清单当"PM 会签问题库"（纪律 2：不直接问用户） |
| `improve-codebase-architecture` | 接手存量代码库时扫"可深化点" → `10-arch-review` 的架构债清单 |
| `resolving-merge-conflicts` | 契约变更引发冲突时的处理流程 |
| **codebase-memory MCP** | `get_architecture`（架构速览）、`search_graph`（找符号与调用链）、`trace_path`（影响面）→ **S2 开工前先查图再写文档**；`manage_adr` 管理 ADR |

**注意**：mattpocock 那套默认 JS/TS 仓库 + GitHub/Linear 工单，我们的项目可能是 Python、无工单系统
→ 取其**方法**，弃其**工具假设**；`setup-matt-pocock-skills` 不需要跑（它配置的是工单跟踪器）。

---

## 4. 前端开发 / 后端开发（frontend-dev / backend-dev）

| 能力 | 用在哪 |
|---|---|
| `tdd` | 先写测试再实现（红-绿-重构），适合有明确契约字段的功能 |
| `implement` | 有 spec/工单时的实现流程 |
| `prototype` | 设计不确定时先做一次性原型验证（**不进交付物**） |
| `diagnosing-bugs` | 诊断循环：先复现再改，禁止瞎猜 |
| `resolving-merge-conflicts` | 冲突处理 |
| **codebase-memory MCP** | 改代码前 `trace_path` 看影响面；找符号用 `search_graph`；看具体实现用 `get_code_snippet`；改完用 `detect_changes` 自查 |

**纪律**：这些 skill 都产出代码/测试，**不得**让它们改写我们工件的结构；`prototype` 的产物
必须放临时目录并在报告里声明"非交付物"。

---

## 5. 开发组长（dev-lead）

| 能力 | 用在哪 |
|---|---|
| `code-review`（mattpocock，双轴） | **正好对应 G-DL-01 的两个检查轴**：Standards（代码规范）+ Spec（对齐 PRD/契约）；它并行跑两份评审的做法可借鉴 | 
| `triage` | 缺陷/议题分流状态机（对应 `revision-loop.md` 的缺陷分流表） |
| `pre-mortem`（pm-skills） | 集成前预演"哪里会炸" |
| `retro`（pm-skills） | 每轮返工的复盘 |
| **codebase-memory MCP** | `check_index_coverage`（评审覆盖面）、`detect_changes`（本轮改动清单）、`get_architecture`（结构是否撑得住） |

**纪律**：`code-review` 的输出格式（双轴报告）**不得**替代 `15-code-review.md` 的结构
（方向偏差六项 + BLOCK/SHOULD/NIT 严重度）。

---

## 6. 测试（qa）

| 能力 | 用在哪 |
|---|---|
| `test-scenarios`（pm-skills） | 从用户故事推测试场景 → `17-test-plan` 的用例骨架（仍要补"正常/边界/异常"三件套） |
| `sql-queries` / `dummy-dataset`（pm-skills） | 造测试数据、写校验查询（数值类功能的口径校验） |
| `diagnosing-bugs`（mattpocock） | 缺陷单必填「根因」——用它的诊断循环定位，不写"疑似" |
| **codebase-memory MCP** | `detect_changes`（本轮改了哪些代码 → 定回归范围）、`check_index_coverage`（覆盖盲区） |

---

## 7. 专项外援：角色池（agency-agents，279 个）

**定位**：7 个固定角色只覆盖"产品交付流水线"。当任务需要**流水线之外的专业能力**
（可访问性审计、安全威胁建模、增长实验、领域知识、特定技术栈…）时，主 Agent 从角色池选人。

**索引**：`.opencode/protocols/role-pool.md`（279 个角色，按 18 个团队归组，每条 = slug + 角色名 + 一句话）。
人设正文在 `.opencode/role-pool/<slug>.md`。

**主 Agent 选人流程**：
1. `grep -i <关键词> .opencode/protocols/role-pool.md`（例：`grep -i accessib` / `grep -i secur`）
2. 命中后 `read .opencode/role-pool/<slug>.md`，判断是否真匹配任务
3. 按下面纪律派发，并在派发 prompt 里写明「产出交给谁吸收」

**三条纪律**（与 role-pool.md 头部一致）：
1. **外援不承担门禁** —— PASS/CONCERN/FAIL 只由体系内固定角色判；外援产物是**输入/建议**，
   由对应固定角色吸收进工件后才算数。
2. **两条派发路径**（优先第 1 条，不依赖会话加载）：
   - **推荐**：task 工具的 `general` 子 agent，把该角色人设的**关键段落**贴进 prompt，
     并叠加本体系纪律（`handoff-schema.md` §4 回传信号、`cli.py` 上报、`runtime/**` 禁改）；
   - 备选：新会话里角色已加载时，直接 该 slug 作为 task 的 `agent` 名。
3. **范围与预算** —— 外援计入并行 ≤3；**同一任务最多派 1 个外援**；不得为"顺便看看"派外援。
   角色池最大的风险不是不够用，而是**让范围悄悄膨胀**。

**常见搭配**（示意，不是白名单）：终验/评审 → `reality-checker` / `accessibility-auditor` /
`ui-finish-gate-reviewer`；安全 → `security-architect` / `application-security-engineer` /
`penetration-tester`；
性能 → `performance-benchmarker`；技术写作 → `technical-writer`；测试自动化 → `test-automation-engineer`。

> 索引是**快照**，随上游更新需重建。OpenCode 包已**随包携带全部 279 个角色人设**
> （`.opencode/role-pool/*.md`），不再依赖本机 `.opencode/role-pool/` 是否存在；
> `ALL-IN-ONE.md` 仍**不含**角色池正文（只放索引说明），避免单文件膨胀到不可用。

## 7.5 框架自身的结构债（v4.4 登记，**知道就好，别顺手改**）

> 这三条都是「同一事实源两处实现」的实例——正是 `handoff-schema.md` §2.3
> 「引用优先于复制，粘贴即产生双份真相，返工时必漏改」要防的事，只不过发生在**框架自己身上**。

| # | 债 | 现状 | 风险 | 处置 |
|---|---|---|---|---|
| 1 | **规则块 6 份副本** | v2/v3 加固块在 6 个角色契约里**逐字重复**（约 30 行 × 6） | 改一条规则要动 6 个文件，漏改一处就出现两套纪律 | 暂不重写（改动面大、收益不即时）。**改公共块前先 `grep` 全量确认副本数** |
| 2 | **生成器不在包里** | 每个契约页脚写「由 `tools/build_opencode.py` 从 ZCode 源契约生成」，但 `tools/` **不在交付包内** | 契约已成**手改孤本**，无法从源重建；重新构建会覆盖手改 | 要么补回 `tools/` 与 ZCode 源，要么**删掉页脚那句**（留着会误导，让人以为有源） |
| 3 | **两份框架（全局 + 工作区）** | `~/.config/opencode/` 与工作区 `.opencode/` 各一份 agents/commands/protocols | 在**别的目录**开 opencode 用的是全局那份；只改工作区等于没改 | **改完工作区必须同步全局**（2026-09-15 已同步 19 个文件，备份在 `~/.config/opencode/backup-before-v4.4-sync-*`） |

**自查命令**（改完框架后跑一遍，确认两份没分叉）：

```bash
# 全局与工作区的差异清单（应为空）
diff <(cd ~/.config/opencode && find agents commands protocols -name '*.md' | sort) \
     <(cd .opencode && find agents commands protocols -name '*.md' | sort)
```

---

## 8. 客户端差异与待验证项

**路径与工具名映射**（两版同构，勿混用）：

<!-- orch:keep -->
| 概念 | ZCode | OpenCode |
|---|---|---|
| 状态目录 | `.zcode/` | `.opencode/` |
| 派发工具 | `Agent` 工具 + `subagent_type: <角色id>` | `task` 工具，agent 名 = 文件名 |
| 调 skill | `Skill` 工具 | `skill` 工具（小写） |
| 嵌套派发防护 | 契约 frontmatter `tools` 不含 `Agent` | `permission.task: deny`（每角色）+ `subagent_depth: 1` |
| 模型绑定 | frontmatter `model`（客户端选择器控制生效） | frontmatter `model: provider/model-id` |
| 真实 token 源 | `turn_usage` | `session` 表（`runtime/lib/usage.py` 自适应） |
| 会话证据登记 | `spawn --zcode-agent <agent_xxx>` | `spawn --session-id <ses_xxx>`（同一参数别名；= task 工具返回的 task_id） |
<!-- orch:keep-end -->

> **为什么必须登记会话 id（v4.1 OpenCode 适配）**：OpenCode 所有 task 派发的子会话在
> `session` 表里 `agent` 列都记成 `general`，父会话链里也不含角色名——**不登记就无法把
> 真实 token / 实际模型归因到角色**。登记后 `usage.sessions()` 按 id 精确匹配；
> 未登记时看板退化为「工作区真实总量」（不按角色假归因）。

**待验证项（下个会话可实验）**：

- **子 agent 预置 skill 字段**：ZCode 的 agent 定义解析器接受 `skills:`（与 `tools` 同族），
  但**语义未验证**（可能是"预加载"、也可能是"限定可用"）。在没验证前，本能力地图走
  "契约正文引用"的路子（100% 生效）。OpenCode 侧对应的是 `skill` 工具的
  `permission.skill` 配置，同样建议先用正文引用。
- **`disable-model-invocation`**：作者声明"仅用户可触发"的 skill（`grill-me` / `grilling` /
  `i-have-adhd`）在支持 skill 工具的客户端里，agent 也可能主动调用 —— 用它们前先想清楚
  是否该由用户触发（`i-have-adhd` 只在用户明确要求时用）。
- **名单膨胀**：279 agent + 94 skill 会拉长名单（每条描述都进上下文）。
  嫌吵就**裁剪随包目录**：删掉 `.opencode/skills/<不需要的名字>/` 或
  `.opencode/role-pool/`（角色池是文档库，删了不影响主流程，只是外援没了人设正文）。
  注意 `role-pool.md` 索引里对应的行也应一并删，否则会指向不存在的文件。
