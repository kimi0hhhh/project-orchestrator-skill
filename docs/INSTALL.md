# 安装指南 / INSTALL · 四个实现

> 先选对包：**用 ZCode → 根目录版**；**OpenCode → `opencode/`**；**WorkBuddy → `workbuddy/`**；
> **其他工具 → `universal/`**。差异对照见 [VERSIONS.md](VERSIONS.md)。
> 四个平台的包都在 [Releases](https://github.com/kimi0hhhh/project-orchestrator-skill/releases) 可直接下载。

---

## 1. ZCode 版（推荐入口）

```bash
# 方式一：从 Release 下载
unzip project-orchestrator-zcode-v4.1.zip
cd project-orchestrator && bash install.sh      # Windows: .\install.ps1

# 方式二：从仓库直接装
git clone https://github.com/kimi0hhhh/project-orchestrator-skill.git
cd project-orchestrator-skill && bash install.sh
```

装的是什么：SKILL.md → `~/.zcode/skills/project-orchestrator/`；6 份角色契约 → `~/.zcode/agents/`；
看板 runtime → `~/.zcode/skills/project-orchestrator/runtime/`。

**开跑**：重启 ZCode 会话（角色清单启动时加载）→ 说「启动主 Agent」→ 填 `docs/PROJECT_BRIEF.md` → 放手。
看板：`python runtime/daemon.py 8788`，浏览器开 `http://127.0.0.1:8788`（端口以 `runtime/.port` 为准）。

## 2. OpenCode 版

```bash
unzip project-orchestrator-opencode-v4.1.zip
# 把解压出的 opencode/ 下各目录拷进你的 .opencode/：
#   agents/  →  .opencode/agents/
#   commands/ → .opencode/commands/
#   protocols/ → .opencode/protocols/
#   skills/project-orchestrator/SKILL.md → .opencode/skills/project-orchestrator/SKILL.md
```

**开跑**：`/takeover <项目名>`；斜杠命令 `/dispatch` `/board` `/gate` `/status`。
角色契约走 `mode: subagent` + `permission: task: deny`（单层编排结构性堵死）。

## 3. WorkBuddy 版（v4.2 · 深度适配）

```bash
unzip project-orchestrator-workbuddy-v4.2.zip
cd workbuddy
bash install.sh <工作区绝对路径>          # Windows: install.cmd
# 铺进工作区：.workbuddy/{agents,protocols,state} + runtime/ + docs/
```

**开跑**：工作区会话里说「启动主 Agent」。注意 v4.2 是**原生优先**：任务列表、
变更台账、产物台账、审计流水直接用 WorkBuddy 原生能力（teams/tasks/changes-index 等），
自建看板只补原生没有的部分——**不要重复开两套记账**。
不支持多文件加载的工具用 `ALL-IN-ONE.md` 单文件版。

## 4. 通用版（任何其他 agent 工具）

```bash
unzip project-orchestrator-universal-v4.1.zip
bash universal/install.sh <你的项目工作区>     # 铺进 <工作区>/.orchestrator/
```

然后两条路：

- **手动**：填 `.orchestrator/platform-config.md`（8 项原语盘点 + A/B/C 档位），
  按 `universal/PORTING.md` §四验证清单走一遍最小流程；
- **让 agent 自己干**：把 `universal/PORTING.md` §五的自举提示词发给你的工具会话，
  它会盘点自身能力、定档、填配置、跑验证，输出移植回执。

## 通用前置

| 项 | 要求 |
|---|---|
| Python | 3.10+（仅看板 runtime 需要；纯协议使用不需要） |
| 子代理派发 | 决定档位：有 → A/B；无 → C 档单人多帽 |
| 文件读写 | 必需（工件交接是框架的骨架） |

## 升级

协议版本以 git tag 为准（当前 v4.1）。升级 = 重新下载对应 Release 包覆盖安装
（install 脚本不覆盖工作区已有文件），或 `git pull` 后重跑 install.sh。
各平台实现的差异与版本语义见 [VERSIONS.md](VERSIONS.md)。
