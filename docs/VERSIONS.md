# 版本家族 · 各实现说明与差异点 / VERSIONS

> 一个协议，四个实现。**协议版本**（当前 v4.1）定义"判什么"；**平台实现版本**定义"怎么跑"。
> 平台实现版本号必须等于所依据的协议版本（WorkBuddy 4.2 是例外：架构方向修正，见下）。

## 一张表看差异

| 维度 | ZCode 版（根目录） | OpenCode 版（`opencode/`） | WorkBuddy 版（`workbuddy/`） | 通用版（`universal/`） |
|---|---|---|---|---|
| **定位** | 先行实现，协议的最完整参考 | 第二实现，task 工具体系 | 深度适配，原生能力优先 | 平台无关母版，移植的源 |
| **实现版本** | v4.1 | v4.1 | **v4.2**（架构方向修正） | v4.1 |
| **派发原语** | `Agent` 工具，`subagent_type` = 角色名 | `task` 工具，`mode: subagent` | `Agent` 工具，`subagent_type: general-purpose` | 由 `platform-config.md` 定义（8 项原语盘点） |
| **单层编排堵死** | 契约 frontmatter `tools` 白名单（结构性） | 契约 `permission: task: deny`（结构性） | 派发 prompt 禁令 + 验收抽查（提示词层） | 三档：A 白名单 / B 提示词 / C 单人多帽 |
| **角色契约** | 6 份（`agents/*.md`，装到 `~/.zcode/agents/`） | 7 份（6 角色 + `orchestrator.md` 主契约，装到 `.opencode/agents/`） | 7 份（`00-orchestrator` + `01~06`，随 install 铺进工作区 `.workbuddy/agents/`） | 6 份平台无关契约（`tools/build_universal.py` 从 ZCode 源构建） |
| **入口/命令** | 唤醒语触发 SKILL（启动主 Agent / 接管项目…） | 5 个斜杠命令：`/takeover` `/dispatch` `/board` `/gate` `/status` | 唤醒语 + `ORCHESTRATOR.md` 操作台 + `ALL-IN-ONE.md` 单文件版 | 由宿主工具决定 |
| **看板/运行时** | 全量：看板 UI + 看门狗 + 账本（`runtime/`，标准库零依赖） | 同源 runtime（独立维护） | 适配层 `lib/contract.py` 对接 WorkBuddy 原生台账 | 按档位：原语 4+5 支持则装，否则降级 markdown 看板 |
| **原生能力复用** | — | — | **是（v4.2 核心变化）**：teams/任务列表/变更台账/产物台账/审计流水用 WorkBuddy 原生，自建只保留看板 UI、门禁留痕、角色契约 | — |
| **协议文件形态** | 规则内联在 SKILL.md | `protocols/` 5 文件（含 capability-map） | `protocols/` 3 文件 + role-pool 池 | `universal/protocols/` 3 文件 + platform-config |
| **安装** | `install.sh` → `~/.zcode/{skills,agents}` | 拷入 `.opencode/`（agents/commands/protocols/skills） | `install.sh <工作区>` → `.workbuddy/` | `universal/install.sh <工作区>` → `.orchestrator/` |
| **移植凭证** | — | 14 条机制逐条移植（v4.1） | `SYNC-RECEIPT-v4.1.md` / `-v4.2.md` 两份回执 | PORTING.md §四验证清单 |

## 选哪个

- **你用 ZCode** → 根目录版，开箱即装，协议最完整；
- **你用 OpenCode** → `opencode/`，task 体系原生落地，斜杠命令操作；
- **你用 WorkBuddy** → `workbuddy/`，且注意 v4.2 起任务/台账走 WorkBuddy 原生，不要重复开看板记账；
- **你用其他工具 / 想给自家工具做适配** → 从 `universal/` 开始，按 `PORTING.md` 盘点 8 项原语、定 A/B/C 档、填 `platform-config.md`。

## 版本号语义

- `universal/` 与根目录 SKILL.md 的 `version` = **协议版本**，与 git tag（v4.1）一一对应；
- 各平台目录的 `metadata.version` = 该实现所依据的**协议版本**（不独立小步走号）；
- 例外：WorkBuddy 4.2 —— 它在协议 4.1 基础上做了**实现架构的方向修正**（复刻 → 原生优先），
  版本号 +1 以标记这次修正；其协议判定标准与 v4.1 完全一致。
- 修改协议（铁律/门禁/工件编号）→ 升协议版本 + 打 tag + 各平台移植后同步版本号；
  只改某平台实现 → 只动该平台目录，协议版本不变。

## 共享与分叉边界

- **共享（改一处全家族生效）**：铁律、阶段状态机、工件编号、门禁标准、参谋会/分诊/快车道机制、runtime（Python 标准库）；
- **平台自治（各目录自己维护）**：派发原语写法、工具白名单、命令/入口、安装路径、原生能力对接、降级标注；
- **同步纪律**：协议变更先落根目录 + universal/，各平台目录在回执文档里记录移植差异后再升版本号——
  三个分叉曾漂移到互不认识（OpenCode 一度没有参谋机制），这套纪律就是为它立的。
