# 同步回执 · v4.1 移植

> 对象：WorkBuddy 版 `project-orchestrator`（`~/.workbuddy/skills/project-orchestrator/`）
> 对照源：[kimi0hhhh/project-orchestrator-skill](https://github.com/kimi0hhhh/project-orchestrator-skill) tag **v4.1**（ZCode 版先行实现）
> 执行日期：2026-09-12 ｜ 方式：**逐项移植**（不是文件替换），落点 = `.workbuddy/` 体系 + `install.sh` 移植链路

---

## 一、逐项移植结果（14 项）

| # | 项 | 状态 | 落点 |
|---|---|---|---|
| 1 | S5 测试前置（S2 契约 PASS 后 qa 起草 17，与 S3 并行，≤3 预算） | **已移植** | SKILL.md「关键路径重叠」①、ORCHESTRATOR.md §2.5① + S5 节、`agents/06-qa.md` 定位与工作方法§1、`agents/03/04` 新增 S5 前置义务 |
| 2 | S4 增量评审（草稿完成检查点先介入，最后只做集成裁定与 15/16 定稿） | **已移植** | SKILL.md「关键路径重叠」②、ORCHESTRATOR.md §2.5② + S4 节、`agents/05-dev-lead.md` 三大职责前言、`agents/03/04` 草稿完成检查点上报义务 |
| 3 | 变更分诊 C0–C2（新章节） | **已移植** | SKILL.md 新增「变更分诊：不是每次改动都走全流程」整节、ORCHESTRATOR.md 新增 §2.6 + §6 门禁记录格式、`agents/00/01/02/05` 各自专节 |
| 4 | 派发 pre-flight checklist（4 条，缺一不派） | **已移植** | SKILL.md「派发前 pre-flight checklist」表格 + 「派发前的三条固定动作」、ORCHESTRATOR.md §3 头部 |
| 5 | 心跳纪律（`--pct 5` 开工即报 / >90s 先 heartbeat / >10min 补 heartbeat） | **已移植** | SKILL.md「心跳纪律」整节、ORCHESTRATOR.md §3 铁律块、`AGENTS.md` 上报纪律、**7 份契约全部新增 v4.1 加固条目** |
| 6 | 星形参谋机制 + 动态编制 L0–L2 | **已移植** | SKILL.md 两个独立整节；源：上游 `docs/ARCHITECTURE.md` §3.5 + `docs/DESIGN.md` §5–§6（回路图、纪律、依据、反模式清单沉淀到本仓 `docs/DESIGN.md` §5–§6）；ORCHESTRATOR.md §4 并行规则；`agents/00/01/02` 参谋主笔/挑刺双方边界 |
| 7 | 删除/修正 SKILL.md「角色契约路径（`.workbuddy/agents/0X-*.md`）」行 | **已移植（有差异）** | 见「二、差异裁决记录 D-1」。SKILL.md 通用清单位改为「契约已由移植机制铺进工作区，不需引用资产源路径」；ORCHESTRATOR.md §3 加「契约路径说明」；`USAGE.md` 两处 `0X-*` 占位改为真实文件名 |
| 8 | `runtime/lib/store.py` 看门狗 v3.17–v3.19 移植 | **已移植** | 见「二、差异裁决记录 D-2」。store.py + server.py + cli.py 三文件联动 |
| 9 | 已知遗留问题写入 `docs/ROADMAP.md`（本次不修） | **已移植** | `docs/ROADMAP.md`「已知遗留问题（本次不修）」3 条 |
| 10 | SKILL.md / README.md / AGENTS.md 定位升级为「多 Agent 协作开发框架」+ 四层 | **已移植** | 三份文件均新增「这是什么（四层）」表；`ORCHESTRATOR.md` 标题与导语同步 |
| 11 | 新增「开源 skill 引用」节 | **已移植** | SKILL.md + README.md 各一节；引用关系与替换方式沉淀为 `docs/CREDITS.md` |
| 12 | 自建实验数据降权为「开发验证（简述）」 | **已移植** | SKILL.md + README.md 各一节，明确 n=2、非等预算、**仅方向性参考**；设计正确性指向研究依据表 |
| 13 | ALL-IN-ONE.md 与分散文件同步重生成 | **已移植** | 136,710 bytes / 2,459 行；新增 `tools/build-all-in-one.py` 使重生成可复现（改完分散文件后跑一次即可） |
| 14 | `metadata.version` = `"4.1"` + install.sh 临时工作区验证 | **已移植** | SKILL.md frontmatter 新增 `metadata` 块（`version: "4.1"` / `target: workbuddy` / `source`）；install.sh / install.cmd 新增 19 项**移植完整性自检** + `cli.py --help` 检查；临时工作区实跑见「三、验证记录」 |

无「不适用」项。

---

## 二、差异裁决记录

### D-1 · 「角色契约路径」行改为「修正」而非「删除」（有差异待裁决）

| | 做法 | 理由 |
|---|---|---|
| 上游 v4.1 | **删除**派发模板中的契约路径行（契约由宿主作子 agent 系统提示，无需自查文件） | ZCode 把 `agents/<name>.md` 作为子 agent 的 frontmatter 定义 |
| 本版 | **修正**保留：删掉 SKILL.md 通用清单里的 `0X-*` 占位行，但 ORCHESTRATOR.md 阶段模板仍要求子 agent 先读契约 | WorkBuddy 侧子 agent 以 `generic-purpose` 派发，**契约不会作为系统提示自动注入**，不读契约就丢了角色方法论 |

**裁决点**：若你希望完全对齐上游（即认为 WorkBuddy 将来会支持以角色名直接派发），
则回退为纯删除；当前实现按「修正」保留，**已被 `USAGE.md` 与 SKILL.md 的说明覆盖**，不影响流程正确性。

### D-2 · store.py 不同源，移植范围收窄（有差异待裁决）

本地 `runtime/lib/store.py` 与上游 v4.1 **不同源且较旧**（上游 81.8 KB / 本地 48.4 KB）。
本次只移植「看门狗 v3.17–v3.19 演进」，**以下上游 delta 未移植**：

| 上游 delta | 未移植理由 | 现状（本地既有行为，未回退） |
|---|---|---|
| 拆出 `runtime/lib/usage.py`（真实用量适配层，ZCode/OpenCode 双后端） | 属 token 账本演进，不在本次三项之列；本地 `token_summary` 是**字节估算**口径，换口径属破坏性变更 | 看板 token 仍为估算值（带"估算"标识） |
| `registry()` 模板回退 `_template_fallbacks()` / `normalize_model()` / `_MODEL_ALIAS` | 属模型账本加固 | 老项目 registry 缺字段时仍走本地 `load_json(TEMPLATE)` 回退 |
| `set_plan_stage()` 的 `_default_stage()` 自动建阶段 | 属规划表加固 | 更新未知阶段仍返回 `{"error": "未知阶段"}` |
| `zcode_session_tokens()` / `actual_cost_usd()` | 依赖价格表 `raw_per_1m` 字段，本地价格表没有；且属 token 账本 | 未提供真实成本核算 |

**接口兼容性结论：本次移植未破坏任何既有接口。** 新增项全部是可选项或新增项：

- `cli.py`：`spawn` 新增**可选** `--zcode-agent`；新增子命令 `actual-model` / `model-report`
- `server.py`：新增 `GET /api/model/main`、`POST /api/model/report`、`POST /api/model/actual`
- `store.py`：新增 9 个函数；`watchdog()` **签名与返回值语义不变**；`snapshot()` 只**新增**字段

**两处本版补全（上游的漏，均向后兼容）**：

1. **上游 `cli.py spawn` 会发 `zcode_agent` 字段，但 `server.py /api/spawn` 未接收它** ——
   导致会话 id 只能在事后通过 `actual-model` 登记，看门狗的 DB 判据在首次派发后一段时间内读不到会话。
   本版在 `/api/spawn`（含 resume 分支）补上接收并落盘。
2. **`cli.py` 未绕过代理访问回环** —— 有 `HTTP_PROXY` 的环境里，urllib 会把
   `127.0.0.1` 请求也送去代理，代理对回环返回 `502 Bad Gateway`，
   **所有上报命令全部失败**却报成「服务未启动？」（本机实测复现）。
   上游 v4.1 的 SKILL.md 明说「`cli.py` 内置了直连回环，不受代理影响」，但上游 `cli.py` 代码里没有这一步——
   本版按上游**文档承诺**补上 `ProxyHandler({})`。这是本次唯一修改既有函数行为的改动，
   方向是**修 bug**（原行为在代理环境下必然失败），不涉及数据口径。

### D-3 · 有意收窄到「不改既有行为」

以下上游做法本次**刻意未采用**，避免回归：

- 未替换本地 `ui/index.html`（本地 UI 已深度定制 104.6 KB，上游 181.2 KB；UI 误读是这个项目最敏感的一类回归）；
  新字段（`interrupt_kind` / `liveness` / `zcode_agent` / `actual_model`）已进 `/api/state`，
  UI 需要时可自行取用，**本次不动前端**。
- 未合并 `runtime/store.py`（44.4 KB，历史遗留重复副本）与 `runtime/lib/store.py`（68.1 KB，实际被 `server.py` 加载）。
  已登记进 `ROADMAP.md` 后续计划（先确认无外部引用再删）。

---

## 三、验证记录

### 3.1 install.sh 移植链路（临时工作区实跑）

```
目标：<临时目录>
  [ok] .workbuddy/agents   [ok] .workbuddy/protocols   [ok] .workbuddy/state
  [ok] runtime             [ok] docs
  已复制: ORCHESTRATOR.md / README.md / SKILL.md / AGENTS.md
--- 移植完整性自检 --- 19/19 [ok]
  契约×7 + 协议×3 + state×3 + runtime×5（cli/server/daemon/lib-store/registry）+ ORCHESTRATOR
  [ok] cli.py --help 可用
```

四类文件齐（契约 / 协议 / state / runtime），`cli.py --help` 可用，退出码 0。

### 3.2 看门狗 v3.17–v3.19 三条路径（用真实客户端 DB 实测）

| 路径 | 造景 | 实测结果 |
|---|---|---|
| **v3.17 DB 判据 → 活着续约** | 会话 id 指向一个**进行中/刚完成**的回合，派发时间早于末回合 | `lease_source='client-db:turn-completed'`，`status→done`，`progress→100` ✓ |
| **v3.17 防误收口守卫** | 会话末回合的 `completed_at` **早于**本次 `spawned_at` | `lease_source='client-db:awaiting-new-turn'`，**只续约不收口** ✓（这正是防「刚派发就被收口」的那道锁） |
| **v3.19 措辞分级 · dead** | `pid=999999`（不存在）+ 静默 3600s | `interrupt_kind='dead'`，理由「进程 999999 已消失，且静默 3600 秒」 ✓ |
| **v3.19 措辞分级 · stalled** | 无 pid、无会话证据 + 静默 3600s | `interrupt_kind='stalled'`，理由「**疑似停滞**：静默 3600 秒且无会话证据（非结论，可续跑）」 ✓ |
| 静默窗口只统计服务运行期 | 既有实现（`age_seconds(..., since_epoch=SERVER_START)`） | **本已具备**，本次保留并补注释 ✓ |
| 兜底降级 | 空 id / 不存在的会话 / 断言失败 | 分别返回 `(None,'',None)` / 空 facts / `None`，**不抛异常** ✓ |

`watchdog()` 新增 `refreshed`（v3.16.8 续约落盘）与 `autoclosed`（v3.17 自动收口）两个落盘分支，
事件总线实测产出 `kind="auto_close"` 事件。

### 3.3 模型三口径链路

```
cli.py actual-model --agent architect --zcode-agent agent_8991fded-… 
  → {"ok": true, "actual_model": "deepseek-v4.1-flash", "actual_effort": "high",
     "source": "client-db:model_usage(sess_subagent_agent_8991fded-…)"}
cli.py model-report --agent architect --model "Deepseek-V4.1-Flash"
  → {"ok": true, "reported_model": "Deepseek-V4.1-Flash", "reported_at": "2026-09-12 13:32:01"}
```

四个口径已分离：`registry.model`（配置）/ `state.model`（派发声明）/ `reported_model`（自报）/
`actual_model`（硬证据）。

### 3.4 接口兼容 + 看板

- `/api/state`：**新增** `zcode_agent` / `reported_model` / `actual_model` / `actual_effort` /
  `interrupt_kind` / `liveness` / `lease_source`；**既有字段全部保留**
  （`model` / `model_id` / `next_model` / `pid` / `silence_seconds` / `rounds` / `status` 实测未丢）
- `/api/plan` `/api/registry` `/api/model/main` `/api/projects` 全部 200
- 全量上报链 `new → spawn → progress → heartbeat → say → finish` 全部 `{"ok": true}`
- 看板静态页 HTTP 200 / 94,600 bytes
- `python -m py_compile lib/store.py server.py cli.py daemon.py board.py` → OK

### 3.5 环境侧观察（非代码问题，已记入文档）

临时工作区里用 `daemon.py` 起的服务，在**父 shell 结束后被带走**（实测两个端口 8799 / 8801 均死）。
这正是 SKILL.md/USAGE.md 已记录的「别用普通后台任务启动服务」现象；已在 `USAGE.md`「已知坑 3」补全
排查顺序。另把「企业代理拦回环」补为「已知坑 2」，附 `ProxyHandler({})` 自建脚本样例。

---

## 四、可选后续（本次未做，等你拍板）

1. `protocols/gate-rules.md` 增补 C0/C1 的**单点复查**判定条件（本次按你的指定只落在 SKILL + ORCHESTRATOR）。
2. 合并/清理 `runtime/store.py` 重复副本。
3. 把上游 `usage.py` 适配层移植进来，让 token 账本从「字节估算」切到「客户端 DB 真实值」
   （需先补价格表 `raw_per_1m`，并同步 `_calc_cost` 口径 —— **破坏性变更，必须裁决**）。
