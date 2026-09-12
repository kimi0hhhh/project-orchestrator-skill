---
description: 派发一个子 agent（角色 + 任务）
agent: orchestrator
---
派发任务给角色：$1

任务内容：$2

派发前你必须先做完这几件事，再用 **task 工具**派发（缺一项子 agent 可拒收）：

1. 先跑 `python runtime/cli.py spawn --agent $1 --title "<阶段+任务>" --project <pid>`
   建任务节点 —— task 工具派发不经 runtime，不 spawn 看板就没节点。
2. 派发 prompt 必须含【目标】【产出物路径】【边界】+ task_id（三要素，缺一可拒收）。
3. **派发前 pre-flight 四查（v4.1，机械执行，缺一不派）**：
   ① 被引用文件逐个 `ls -la` 实查**已落盘且非空**（不凭记忆）；
   ② 【允许读】清单与子 agent 实际需要一致（多给=上下文过载，少给=拒收重来）；
   ③ 工件路径为**绝对路径**且父目录存在（必要时先 `mkdir -p`）；
   ④ 上报要求、`--project <id>`、完成判据逐条写全。
4. 必须列【允许读】清单：明确到文件，不给整个目录；统一加一份
   `.opencode/protocols/capability-map.md`。
5. 必须写明【完成后】：`cli.py finish --agent $1 --artifact <路径> --artifact-summary "一句话"`；
   产出多份时逐份 `say --type artifact`。
6. **派发后补登记会话证据（v4.1 OpenCode 适配）**：task 工具返回的 `task_id` 即子会话 id
   （`ses_...`），补一条 `python runtime/cli.py spawn --agent $1 --session-id <task_id>
   --session-only --project <pid>`（只登记证据，不动状态/进度）——看板据此归因真实 token
   与实际模型。
7. 必须要求**开工即报**：第一条 `progress` 在读任何文档之前发出
   （`--pct 5 --step "已启动，正在读 X"`），之后每个里程碑各报一次。
8. 必须要求长命令（>90 秒）先发 `cli.py heartbeat`，否则静默看门狗 240s 会判它中断；
   思考/写码 **>10 分钟无 progress** 时补 `heartbeat --note "在做什么"` 自证存活（v4.1）。
9. 写清【禁止】项，至少含：禁止修改 `runtime/**`；禁止再派孙 agent。
10. 增量改动（prompt 标注**「增量模式」**）：只改相关节/追加条目，**禁止重排或重写全文**；
    【允许读】精确到节；返修退回同一子 agent 续会话（v4.1 变更分诊）。

派发前先确认并行预算：当前 status=working 的子 agent 必须 **< 3** 个。
回传信号要求 ≤15 行。
