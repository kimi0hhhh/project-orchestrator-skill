# OpenCode 版 · project-orchestrator v4.1

> 平台无关协议（`universal/`，tag v4.1）的 **OpenCode 实现**。`metadata.version = 4.1`、`target: opencode`。
> 本目录是已安装实例的快照快照源；更新协议时按 `universal/PORTING.md` 重新移植，再回填本目录。

## 结构（对应 .opencode/ 内的安装位置）

| 本目录 | 安装到 .opencode/ | 说明 |
|---|---|---|
| `skills/project-orchestrator/SKILL.md` | `skills/project-orchestrator/SKILL.md` | 编排协议本体（skill 入口） |
| `agents/*.md`（含 orchestrator.md） | `agents/` | 7 份角色契约（6 角色 + 主 Agent） |
| `commands/*.md` | `commands/` | /takeover /dispatch /board /gate /status 五个命令 |
| `protocols/*.md` | `protocols/` | gate-rules / handoff-schema / revision-loop / capability-map / role-pool 索引 |

## 与其他版本的关系

- 上游：`../universal/`（协议）← `../agents/`（ZCode 源契约）；本版移植了 v4.1 的 14 条机制
  （S5 测试前置、变更分诊 C0–C2、派发 pre-flight、心跳纪律、星形参谋等）；
- 工具白名单/派发原语按 OpenCode 的 `task` 工具与 `mode: subagent`、`permission` 写法落地；
- 未入库资产：`role-pool/` 的 279 个第三方 persona 文件（License 未确认，不入库；本地按需安装）
  与 `state/` 运行数据（不入库）。
