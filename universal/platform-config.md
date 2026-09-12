# platform-config.md · 平台适配配置（移植时生成本文件）

> 本文件是通用版协议与具体平台之间的**唯一接口**。`SKILL.md` 里所有平台相关动作
> （派发、工具限制、上报、看板启动）都指向这里定义的原语。移植时由 PORTING.md
> 阶段 0 的盘点结果填写；未填写的字段 = 该能力未配置，对应功能按档位降级。

```yaml
tool_name: "{{TOOL_NAME}}"        # 平台名，如 zcode / opencode / claude-code / your-tool
tier: "A"                          # A=完整 / B=无工具白名单 / C=单人多帽（定义见 SKILL.md §0）

# ── 原语 1：子代理派发 ──────────────────────────────
dispatch:
  mechanism: ""                    # 派发方式描述，如 "Agent 工具, subagent_type=<role>" 或 "task 工具" 或 "无（C 档）"
  role_as_system_prompt: true      # 角色契约能否作为子代理的系统提示注入；false 则在派发 prompt 头部贴契约全文
  concurrency_limit: 3             # 同时 working 的子代理上限

# ── 原语 2：单层编排堵死 ────────────────────────────
one_layer:
  method: "tools-allowlist"        # tools-allowlist（结构性）| prompt-only（提示词强制，B 档）| n/a（C 档）
  detail: ""                       # 如 "契约 frontmatter tools 不含派发工具" 或 "派发 prompt 重申禁令 + 验收抽查"

# ── 原语 3：文件与路径 ──────────────────────────────
files:
  workspace_layout: ""             # 工件/状态在本平台的目录布局，如 ".orchestrator/{agents,protocols,state}"
  read_context: ""                 # 控制子代理「允许读」清单的机制，如 tools 白名单 / 派发 prompt 列举

# ── 原语 4+5：上报与心跳 ────────────────────────────
reporting:
  channel: "runtime-cli"           # runtime-cli（python runtime/cli.py）| file-append（直接写 state/*.jsonl）| none
  command_template: "python runtime/cli.py {action} --project {pid} ..."   # 平台抄改
  progress_min_times: 3            # 每次派发最少进度上报次数
  heartbeat_rule: ">90s 命令先心跳；>10min 无进度补心跳"

# ── 原语 6：看门狗（可选）────────────────────────────
watchdog:
  enabled: true                    # 无定时巡检能力设 false，降级为主 Agent 验收时核对
  silence_seconds: 240
  note: "疑似停滞 ≠ 死亡：重派前必须先查工作区文件活动"

# ── 原语 7：看板（可选）─────────────────────────────
board:
  enabled: true                    # 无常驻服务能力设 false，保留 state/board.md 手写/派生看板
  launch: "python runtime/daemon.py 8788"
  ui: "http://127.0.0.1:8788"

# ── 原语 8：提示注入与 skill ─────────────────────────
prompting:
  skill_invocation: ""             # 平台的 skill 点名机制；无则填 "契约内联方法论"
  recommended_skills: true         # 是否保留各契约「推荐 skill」清单
```

## 填写规则

1. 每个字段填**平台实际能力**，不填理想能力——后续所有降级判断以本文件为准；
2. `tier` 由 PORTING.md §二 的判定规则得出，改档位必须重跑移植验证；
3. 本文件是**真相源**：平台升级后能力变化，先改这里，再同步 SKILL.md 的档位注记；
4. C 档（单人多帽）仍必须填本文件——dispatch.mechanism 填 "无（C 档）"，
   one_layer.method 填 "n/a"，reporting 保留（主 Agent 自报）。
