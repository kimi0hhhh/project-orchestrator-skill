# OpenCode 版 · project-orchestrator v4.4

> 平台无关协议（`universal/`）的 **OpenCode 实现**。`metadata.version = 4.4`、`target: opencode`。
> 本目录是已安装实例的快照源；更新协议时按 `universal/PORTING.md` 重新移植，再回填本目录。

## 结构（对应安装位置）

| 本目录 | 安装到 | 说明 |
|---|---|---|
| `skills/project-orchestrator/SKILL.md` | `.opencode/skills/project-orchestrator/SKILL.md` | 编排协议本体（skill 入口） |
| `agents/*.md`（含 `orchestrator.md`） | `.opencode/agents/` | 8 份角色契约（7 角色 + 主 Agent） |
| `commands/*.md` | `.opencode/commands/` | `/takeover` `/dispatch` `/board` `/gate` `/status` |
| `protocols/*.md` | `.opencode/protocols/` | gate-rules / handoff-schema / revision-loop / capability-map / role-pool 索引 |
| **`scoring/`** | **`<工作区>/scoring/`** | **v4.4 新增**：评分尺（积木分 + 项目分 + 红绿验证 + UI 点击冒烟） |
| **`runtime/`** | **`<工作区>/runtime/`** | **v4.4 新增**：runtime 的**增量覆盖层**（只含本版改动的文件，见下） |

> ⚠ `scoring/` 与 `runtime/` 落在**工作区根**，不在 `.opencode/` 内 —— 与 `SKILL.md` /
> `gate-rules.md` 里 `python scoring/ruler.py`、`python runtime/board.py` 的写法是同一个相对根。

### `runtime/` 是增量覆盖层，不是完整 runtime

本目录只放**本版改动过**的 6 个文件（`board.py` / `cli.py` / `daemon.py` / `server.py` /
`dispatch.py` / `archive.py`）。完整 runtime 在仓库根 `runtime/`（ZCode 源，共享）。
安装时把这 6 个覆盖到工作区 `runtime/` 即可，**其余文件不要动**。

## 与其他版本的关系

- 上游：`../universal/`（协议）← `../agents/`（ZCode 源契约）
- v4.4 含**协议级变更**（门禁 `G-QA-02` 加运行时点击红线、新增工件 `20-closeout`、
  `S7` 就绪清单加第 5/6 项）。按 `docs/VERSIONS.md` 的同步纪律，另三个实现
  （ZCode / WorkBuddy / 通用版）**待移植**；移植完成后应统一协议版本号。
- 未入库资产：`role-pool/` 的 279 个第三方 persona 文件（License 未确认，不入库；本地按需安装）
  与 `state/` 运行数据（不入库）。

## 本版（v4.4）验证清单

```bash
python scoring/ruler.py                     # 积木分：8 块静态检查
python scoring/verify_redgreen.py           # 红绿验证：3 条检查注入缺陷后必须变红
python scoring/ui_smoke.py --selftest       # UI 冒烟自检：注入 PM-D1 必须变红
python scoring/ui_smoke.py                  # 真开浏览器逐页点一遍（需 Chrome/Edge）
python runtime/board.py check --port 8777   # 端口被占时必须 exit 2 并报出占用者
python runtime/cli.py projects              # 对着别的服务跑时必须 exit 2 拒写
```

升级步骤与逐项验收见 `docs/UPGRADE-v4.4-opencode.md`。
