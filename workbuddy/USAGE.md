# 多 Agent 协作开发框架 · 给其他 AI 工具使用

一套「主 Agent 派发 + 子 Agent 交付工件 + 门禁验收」的多 Agent 协作开发框架。
7 个角色、3 份协议、19 个工件，全部通过**文件**交接，不靠上下文记忆——任何一环都能换人重跑。

框架四层：**协议** + **流程** + **可视化看板** + **追溯账本**。

版本：v4.1（WorkBuddy 版）｜ 打包：2026-09-12

---

## 目录里有什么

```
project-orchestrator/
├── SKILL.md              skill 入口（支持 skills 机制的工具直接读它）
├── ORCHESTRATOR.md       主编排手册：阶段状态机 + 可直接复制的派发命令模板 + 变更分诊
├── README.md             框架说明（四层 / 7 角色 / 研究依据 / 开源 skill 引用）
├── ALL-IN-ONE.md         ★ 单文件全量版：所有规则合成一个 md，直接粘贴
├── AGENTS.md             给 Codex / Cursor 等「读 AGENTS.md」的工具的入口
├── USAGE.md              本文件
├── SYNC-RECEIPT-v4.1.md  v4.1 移植回执（变更清单 + 差异裁决记录 + 验证记录）
├── tools/                 build-all-in-one.py（改完分散文件后重生成 ALL-IN-ONE.md）
├── agents/               7 个角色契约（00-orchestrator … 06-qa）
├── protocols/            3 份协议
│   ├── handoff-schema.md   工件文件头 + 四块正文结构 + 回传信号格式
│   ├── gate-rules.md       每个工件 PASS / CONCERN / FAIL 判定条件
│   └── revision-loop.md    缺陷分流表 + 返工轮次与升级规则
├── runtime/              看板运行时（Python 3 标准库，零依赖）
│   ├── cli.py              子 agent 上报与状态查询命令行
│   ├── server.py / board.py / daemon.py / start.cmd / serve.cmd
│   ├── lib/store.py        状态存储 + 消息总线 + 看门狗（存活判定在 watchdogs 段）
│   └── ui/index.html       实时看板前端（1.2 秒轮询）
├── docs/
│   ├── PROJECT_BRIEF.md   ★ 产品输入书模板（整套流程的唯一入口）
│   ├── ROADMAP.md         路线图 + 已知遗留问题 + v4.1 同步回执与差异裁决
│   ├── DESIGN.md          设计决策与依据（研究引用、星形参谋、动态编制 L0–L2）
│   ├── CREDITS.md         开源 skill 引用关系与替换方式
│   └── examples/          （本地示例，随安装环境提供）
├── templates/state/       空看板：board.md / open-issues.md / gate-log.md
└── install.cmd / install.sh   一键把模板铺进目标工作区（含移植完整性自检）
```

> 根目录的 `USAGE.md` / `ALL-IN-ONE.md` / `SYNC-RECEIPT-v4.1.md` **不会被 install 铺进工作区**
> （只铺 `ORCHESTRATOR.md` `README.md` `SKILL.md` `AGENTS.md` 四份）；
> `docs/` 整目录会铺，其中 `PROJECT_BRIEF.md` 与 `examples/` 是给项目用的，其余是框架自身的元文档。

---

## 三种接入方式（按目标工具选一个）

### 方式 A：工具支持 Skills（WorkBuddy / CodeBuddy / Claude Code）

把整个 `project-orchestrator` 目录复制到该工具的 skills 目录，改名 `project-orchestrator`：

| 工具 | 放哪 |
|---|---|
| WorkBuddy | `C:\Users\<你>\.workbuddy\skills\project-orchestrator\` |
| Claude Code | `<项目>/.claude/skills/project-orchestrator/` 或 `~/.claude/skills/` |
| CodeBuddy | 同 WorkBuddy 的 `~/.workbuddy/skills/` |

`SKILL.md` 的 frontmatter 已写好触发词（`启动主 Agent` / `接管项目` / `按 ORCHESTRATOR 继续` / `多 agent 协作开发` / `派发任务`），说出这些词即自动加载。

**注意**：SKILL.md 里的路径（`.workbuddy/agents/*.md`、`runtime/cli.py`）是**相对工作区根目录**的，
所以工作区里也要有这些文件 —— 用方式 C 的 `install.cmd` 铺一次即可。
**派发 prompt 里不要再引用本 skill 目录的绝对路径**（那是只读资产源），
否则子 agent 会读到与工作区不同步的版本。

### 方式 B：任何 AI 工具（通用，推荐先试这个）

1. 打开 `ALL-IN-ONE.md`，**整份复制**（约 60 KB，一次粘贴就行）
2. 贴进目标工具里作为：
   - Claude / ChatGPT：**Project Instructions** 或自定义指令
   - Cursor：`.cursorrules` 或 Rules for AI
   - Codex / Gemini CLI：贴到 `AGENTS.md`（本目录也提供了一份精简入口）
   - 网页版对话：第一轮直接贴进去当开场白
3. 然后说：「按 ORCHESTRATOR 继续，先做 S0 立项」

`ALL-IN-ONE.md` 是自洽的——它把 SKILL.md、ORCHESTRATOR.md、7 份角色契约、3 份协议全合在一起，
不依赖其他文件。代价是子 Agent 无法单独只读自己那份契约（方式 A 更省 token）。

### 方式 C：铺进一个工作区（配合看板用）

```bat
:: Windows，在目标工作区根目录执行
C:\Users\<你>\Desktop\project-orchestrator\install.cmd C:\path\to\workspace
```

```bash
# bash
bash ~/Desktop/project-orchestrator/install.sh /path/to/workspace
```

会做这些事（**不覆盖已存在的同名文件**）：

| 复制到 | 目标位置 |
|---|---|
| `agents/` | `<工作区>/.workbuddy/agents/` |
| `protocols/` | `<工作区>/.workbuddy/protocols/` |
| `templates/state/` | `<工作区>/.workbuddy/state/` |
| `runtime/` | `<工作区>/runtime/` |
| `ORCHESTRATOR.md` `README.md` `SKILL.md` `AGENTS.md` | `<工作区>/` 根目录 |
| `docs/` | `<工作区>/docs/` |

---

## 跑起来（5 分钟）

1. **填输入书**：编辑 `<工作区>/docs/PROJECT_BRIEF.md`，必填四项
   （背景 / 目标用户 / 核心问题 / 失败定义）→ 缺任一，入口门禁 G-IN-00 判 FAIL
2. **起看板**（可选，但强烈建议）：
   ```bash
   python runtime/board.py open      # 本机手动：起服务 + 自动开浏览器
   python runtime/board.py wmi       # 主 Agent 在会话里：受限沙箱下 detached 活不过调用
   ```
   浏览器开 `http://127.0.0.1:8777`（端口以 `runtime/.port` 为准，占用了会自动顺延）
3. **告诉主 Agent**：「按 ORCHESTRATOR.md 跑 S1」

之后主 Agent 会自己校验 Brief → 派发 → 验收 → 推进。

---

## 换工具时要注意的三件事

1. **Agent 工具必须支持「派发子 agent」**。这套框架的价值全在角色分离上；
   工具只能单线程对话时，仍可用文件交接 + 门禁，但要靠你手动切角色
   （把 `agents/01-product-manager.md` 这类契约的内容贴给对话，让它按那份契约产出文件）。
2. **子 agent 要能执行命令行**（Python 3 + 标准库即可，无第三方依赖），否则看板用不了。
   看板是可选件，没它也跑得通流程，只是失去实时性与静默看门狗。
3. **路径分隔符**：所有文档用正斜杠 `/`，Windows 下同样可用。

---

## 体系的三条铁律（换工具也别丢）

1. **主 Agent 不下场干活** —— 不写代码、不写产品文档。你一动手就没人验收了。
2. **工件通过文件交接，不靠上下文记忆** —— 这样任何一环都能被替换、被打回、被重跑。
3. **门禁不放水** —— CONCERN 就登记未决项，不用「差不多」换进度。

## v4.1 的四条新增纪律（换工具后最容易丢）

1. **派发前 pre-flight**：被引用文件逐个实查已落盘非空 / 「允许读」精确到节 /
   绝对路径且父目录存在 / 上报要求与完成判据写全。**缺一不派。**
2. **心跳纪律三条**：①开工即报（`--pct 5`，在读任何文档之前）②>90 秒的长命令先 heartbeat
   ③>10 分钟无 progress 补 heartbeat。看门狗**无法区分「深思」与「挂死」**。
3. **变更分诊 C0–C2**：上线后的增量改动先分诊。C0 轻改 = 1 次派发 + 1 行门禁记录
   （`C0 fast-pass`）；C1 仅契约变更时才走 PM×架构师会签；C2 才走完整 S1–S7。
   **判不准按 C1 走。**
4. **动态编制 L0–L2**：派发前按「工作量 × 可分解性」分诊，**简单任务不加人**。
   **复杂 ≠ 可拆**（顺序耦合工件加人有害）。星形参谋只用于高价值工件：
   主笔唯一 + 2–3 只只读参谋一轮挑刺 + 主笔一次返修，参谋**不写工件、不担门禁、互不对话**。

## v4.2 的两条新增纪律（WorkBuddy 深度适配）

1. **契约内联，别让子 agent 自读契约。** WorkBuddy **不会**把角色契约注入子 agent 的系统提示
   （上游 ZCode 版靠 frontmatter，WorkBuddy 没有这机制；`plugins/*/agents/*.md` 可作
   `subagent_type`，但那是**应用启动时注册**的，会话内写入不生效）。
   现在用一条命令生成带契约的派发 prompt：

   ```bash
   python runtime/cli.py dispatch --agent architect \
     --task "为 X 设计 Y" \
     --artifact "<产出物绝对路径>" \
     --allowed-read "02-prd.md §3,§5" \
     --criteria "<完成判据>" --task-id "<项目>/S2"
   ```

   `--section <标题前缀>` 可按节裁剪（实测 10.1 KB → 2.4 KB）；加 `--check` 只做校验。
   `python runtime/cli.py contracts` 列角色与契约文件。
   **它同时把 pre-flight 的必填项校验机械化了**——缺项就 exit 1 并列出缺项。

2. **临时任务双写：原生 + 自建。** 每开一个阶段任务，除自建记录外还要 `TaskCreate` 一条，
   推进时 `TaskUpdate`。**原生的给用户看**（WorkBuddy 任务区，不必开看板），
   **自建的给编排用**（带门禁/阶段/放行语义）。原生的没有门禁字段，自建的没有宿主 UI。
   不要试图把门禁结论塞进原生 `description`。

3. **别重复造轮子 —— 先查原生。** 想让编排做某件事之前，先确认 WorkBuddy 是不是已经在做了：

   | WorkBuddy 已自动落盘 | 路径 |
   |---|---|
   | 文件变更台账 | `~/.workbuddy/changes-index/<会话id>.json` |
   | 产物台账 | `~/.workbuddy/artifact-index/<会话id>.json` |
   | 审计流水 | `~/.workbuddy/audit-log/YYYY-MM-DD.jsonl` |
   | 真实 token 用量 / 逐请求 credits | `~/.workbuddy/workbuddy.db` → `session_usage` |
   | 会话存活 / 模型 / 思考档 | `~/.workbuddy/workbuddy.db` → `sessions` |
   | 执行 trace | `~/.workbuddy/traces/<port>/trace_*.json` |

   看板 `/api/state` 的 `native` 块已把这几样暴露出来。**唯一的例外是角色契约**——
   上面没有，所以契约必须自建 + 内联（见第 1 条）。

## 一个最容易犯的错

**把需求缺陷当 bug 派给开发。** 缺陷必须先定性再派发：

| 症状 | 给谁 |
|---|---|
| 做错了 | 开发（前端/后端） |
| 做对了但不该这么定义 | 产品经理 |
| 做对了但结构撑不住 | 架构师 |
| 两边都没错，是话说岔了 | 架构师改契约 |

## 已知坑（移植时最容易踩）

### 坑 1 · 240s 静默看门狗

跑长命令（>90 秒）前，子 agent **必须先发一条 heartbeat**，否则静默看门狗（默认 240s）
会把它自动判成「中断」。这是设计上的必然，不是 bug。

```bash
python runtime/cli.py heartbeat --agent <id> --step "长跑中：拉 41 只 ETF 日线" --project <pid>
```

**v4.2 进一步缓解（机制层）**：静默判定**之前**先查 WorkBuddy 原生会话级证据
（`~/.workbuddy/workbuddy.db` 的 `sessions.status='working'` + `session_usage.updated_at`，
实测每秒级更新）。命中就**直接续约，绝不判停滞**。所以现在误报率大幅下降。

**仍然成立的部分**：原生层是**会话级**的（子 agent 同进程共享同一条会话记录），
它只能**否决**"你以为的静默"，不能证明"某个子 agent 活着"。所以心跳纪律**不要丢**——
尤其是单 agent 已经真的挂掉时，只有心跳和 per-agent 判据能分辨。

排查时**先看 `lease_source`**：`client-db:*` / `client-session-log` /
`workbuddy-session:working` 分别代表证据来自哪一层。

### 坑 2 · 企业代理拦回环（本机实测，最坑的一个）

有企业代理的环境里会设 `HTTP_PROXY` / `HTTPS_PROXY`。urllib 默认会**把 `127.0.0.1` 的请求
也送去代理**，代理对回环返回 `502 Bad Gateway` —— 于是所有上报命令全部失败，
报错却是「服务未启动？」，而服务其实活得好好的。

**v4.1 已修**：`cli.py` 用 `ProxyHandler({})` 对回环直连，不受代理影响。
如果你在别处自己写脚本调看板 API，记得手动绕开代理：

```python
import urllib.request
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
```

### 坑 3 · 服务被父 shell 带走（有两层，第二层最隐蔽）

**第一层：别用普通后台任务启动服务**（`cmd &` / `start /b` 之类）—— 那是父 shell 的子进程，
**父 shell 一结束服务就跟着死**，表现是「看板莫名其妙又打不开了」。
本机手动启动用脱离终端的方式：`python runtime/board.py open`（内部用
`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`）。

**第二层（2026-09-12 实测，主 Agent 必看）：受限沙箱会回收整棵进程树。**
主 Agent 在 WorkBuddy 会话里通过 Bash 工具起服务时，**连 `DETACHED_PROCESS` 都不管用**：

| 现象 | 证据 |
|---|---|
| 同一次调用内 `curl` 通 | `daemon.py 8777` 打印成功，紧接的 curl 返回 200 |
| **下一次调用立刻连不上** | `URLError(ConnectionRefusedError(10061))` |
| 日志里毫无异常 | `server.log` 只有三行正常启动信息，**没有 traceback**（所以不是崩溃） |
| 同机对照 | 用户手动启动的其它服务连续存活 3 小时以上 |

根因：宿主在每次工具调用结束时关闭作业对象，**整棵树一起回收**，detached 子进程也在其中。

**解法：`python runtime/board.py wmi`** —— 走 WMI `Win32_Process.Create`，
新进程的父进程是 `WmiPrvSE.exe`，位于调用者的作业对象之外，因此不受回收。
已在跑则自动跳过，不会重复绑定端口。（实跑验证：起完跨多次调用持续存活。）

**看板打不开时的排查顺序**：①先确认服务进程还活着（最常见真因）→ ②查事件总线是否真没数据
（`wc -l runtime/projects/<pid>/bus/events.jsonl`）→ ③判「活着没上报」还是「已死」
（三重取证：文件活动 / 计算进程 / 日志字节数）→ ④确认用户看的是 `http://127.0.0.1:<端口>`
而不是双击本地 HTML（`file://` 下没有后端，页面永远是死的）。

### 坑 4 · 移植机制不覆盖同名文件

`install.sh` / `install.cmd` 都是**不覆盖**语义（`cp -n` / `robocopy /XC /XN /XO`）。
升级已有工作区时，需先移除旧文件再铺，或者手动对照替换 —— 否则你会以为"升级了"，
实际跑的还是旧版。装完看 install 输出末尾的**移植完整性自检**（19 项 + cli.py --help）。
