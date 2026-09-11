# 使用介绍 / USAGE

> 语言说明：本文正文为中文，每个大节末尾附 English TL;DR。Skill 本体（`SKILL.md`）是运行时的权威指令源，本文是它的展开讲解。

## 1. 安装 / Install

**前置**：ZCode（或 OpenCode，见 ROADMAP）已安装；`python 3.10+`（看板运行时用）；git（可选）。

```bash
# ZCode（当前版本）
bash install.sh          # 复制 SKILL.md → ~/.zcode/skills/project-orchestrator/
                         # 复制 agents/*.md → ~/.zcode/agents/

# Windows
powershell -File install.ps1
```

安装后**重启会话**（角色清单与会话启动时加载，见 DESIGN.md §模型路由）。

> English TL;DR: run `install.sh` (or `install.ps1` on Windows), then restart your agent session — role definitions load at session start.

## 2. 唤醒主 Agent / Wake the orchestrator

新会话里说任意一句：

- 「启动主 Agent」
- 「接管项目」
- 「按 ORCHESTRATOR 继续」
- 「多 agent 协作开发」

主 Agent 会执行固定唤醒流程：

1. 读工作区的 `ORCHESTRATOR.md`（阶段状态机与派发命令模板）
2. 读 `.zcode/state/board.md`（当前阶段与进度，自动生成）
3. 读 `docs/PROJECT_BRIEF.md`（产品输入书——**你需要填这个**）
4. 读 `.zcode/state/open-issues.md`（未决项）
5. 启动看板服务（`python runtime/daemon.py 8788`）并打开浏览器
6. 向你汇报四件事：**当前阶段 / 谁在跑谁待命 / 下一步打算 / 需要你拍板什么**

> English TL;DR: say any wake phrase; the orchestrator reads the workspace state files, boots the board on port 8788, and reports stage / running agents / next step / decisions needed. You fill `docs/PROJECT_BRIEF.md`.

## 3. 流程与工件 / Pipeline & artifacts

每个阶段由唯一角色交付编号工件，工件是验收的唯一对象：

| 阶段 | 角色 | 工件 |
|---|---|---|
| S0 立项 | 主 Agent | 00 PROJECT_BRIEF 确认 |
| S1 需求 | 产品经理 | 01-requirements（场景→痛点→需求→验收四段）· 02-prd · 03-ui-design（四态）· 04-ui-wireframe（可点击 HTML） |
| S2 架构 | 架构师 | 05~08 各层架构 · **09-api-contract（前后端唯一法律）** · 10-arch-review（与 PM 会签） |
| S3 开发 | 前端 + 后端（可并行） | 11-frontend-code · 12-interface-request · 13-backend-code · 14-api-impl-report |
| S4 集成 | 开发组长 | 15-code-review（BLOCK/SHOULD/NIT）· 16-build（可启动构建） |
| S5 测试 | 测试 | 17-test-plan（P0 正常/边界/异常各≥3）· 18-test-report · 缺陷单 |
| S6 终验 | 产品经理 | 19-pm-acceptance |
| S7 交付 | 三签 | dev-lead + qa + product-manager 三签齐才交付，另附 retro |

缺陷分流表（不是所有 bug 都给开发）：

| 症状 | 给谁 |
|---|---|
| 做错了 | 前端/后端 |
| 做对了但不该这么定义 | 产品经理 |
| 做对了但结构撑不住 | 架构师 |
| 两边都没错是话说岔了 | 架构师改契约 |

> English TL;DR: numbered artifacts per stage; the API contract (09) is the single source of truth; defects are triaged to the responsible role, not always to developers; S7 requires three signatures.

## 4. 派发与并行预算 / Dispatch rules

- 派发用 Agent 工具，`subagent_type` = 角色名；派发 prompt 必须含：允许读的文件清单（明确列举）、必须写的文件（绝对路径）、硬性约束、回传 ≤15 行；
- **同时 working 的子 Agent ≤ 3**；先收敛再派新；
- **单层编排**：角色契约的 tools 不含 Agent 工具，子 agent 不得再派孙 agent；
- 长命令（>90s）先发 heartbeat，否则 240s 静默看门狗会判中断；
- 动态编制（进阶，见 DESIGN.md §动态编制）：L0 单角色 / L1 主角色+1~2 只读参谋 / L2 主角色+3 参谋，按"工作量×可分解性"分诊，拿不准就降档。

> English TL;DR: dispatch via the Agent tool with explicit file allow-lists and deliverable paths; max 3 concurrent workers; one-layer only (sub-agents cannot spawn sub-agents); heartbeat for long commands; use triage levels L0–L2, when in doubt size down.

## 5. 看板 / Board

```bash
python runtime/daemon.py 8788        # 启动（已在跑则跳过）
python runtime/board.py open         # 起服务并打开浏览器
python runtime/cli.py projects       # 项目列表
python runtime/board_sync.py         # 重新生成 board.md
```

看板页（`http://127.0.0.1:8788`）包含：阶段流水线、agent 卡片（状态/进度/模型/静默计时/中断恢复按钮）、任务进度、消息流与时间线、token 账本（真实值优先读 ZCode 会话日志）、整体规划作战地图、工件查看器。

排障顺序（看板静默时）：服务进程存活 → `curl 127.0.0.1:8788/api/state` → 事件总线文件有无增长 → 区分"活着没上报"vs"已死"（文件活动 + 进程 + 日志字节三重取证）。

> English TL;DR: the board is a local web UI with live agent cards, token ledger and stage map; troubleshooting starts from the daemon process, then the API, then the event bus files.

## 6. 模型配置 / Models

- 子 agent 默认**继承主会话模型**；
- 按角色钉模型：角色契约 frontmatter 写 `model: "<providerId>/<modelId>"`——**必须带 provider 限定**，平 id 会被解析到默认供应商导致静默回落（这是实测踩过的坑，详见 DESIGN.md §模型路由）；
- 每角色推荐模型与降级链记在 `runtime/registry.json`；额度耗尽按链顺位降级并留痕，不得静默。

> English TL;DR: pin a role's model via frontmatter `model: "<providerId>/<modelId>"` — the provider prefix is mandatory, plain ids silently fall back to the session model. Fallback chains live in `runtime/registry.json`.

## 7. 验收与门禁 / Acceptance

收到子 agent 回传后：核对自验收信号 → 验证文件真实存在 → 按 `gate-rules` 逐条判 PASS/CONCERN/FAIL → 结果落盘 `.zcode/state/gate-log.md`。CONCERN 不堵流程但必须登记。S7 交付需三签。

## 8. 常见问题 / FAQ

- **看板打不开？** 别双击 `ui/index.html`（file:// 无后端），必须走 `http://127.0.0.1:<端口>`；Git Bash 下 curl 记得 `--noproxy '*'`。
- **改了角色契约没生效？** 会话启动时加载，重启会话。
- **子 agent 显示中断但它其实在干活？** 看门狗按静默判定，派发长任务前让它先发 heartbeat；误判可在看板点"撤销误判"。
