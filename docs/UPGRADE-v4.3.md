# 升级指南 v4.3（ZCode 版）

> 适用：已安装 project-orchestrator（v4.0~v4.2 任意版本）的环境。
> 全程只覆盖 5 个代码文件 + 2 个角色契约，**不触碰任何项目数据**（runtime/projects/ 原样保留）。

## 本次变更（v4.1 → v4.3）

- **耗时账单**（新）：`/api/timetrack` 端点 + 看板「耗时账单」面板（墙钟/Σ工时/并行系数 + 阶段·Agent·任务三层累计 + 甘特时间线）+ `cli.py time` 终端账单。数学正确性经 11 项已知答案断言验证。
- **派发管家**（新）：`runtime/dispatch.py` —— `prepare`（预检拒发 + 角色记忆自动回读 + 任务书落盘 `--prompt-file`）与 `close`（工件验收 + gate-log 建议行）。任务书中 cli 默认写**绝对路径**（防多副本上报分流）。
- **纪律入 SKILL**（v4.2/v4.3）：真并行派发、会签/返修 2 轮上限、上报税瘦身（进度按任务时长定）、验证规模上限、记忆卫生。
- **角色契约**：frontend-dev 占位符修复（原样存在会导致每次派前端必报 `Model provider is not configured`）；新增轻模型角色 `backend-fast`（钉 deepseek-v4.1-flash，机械性后端任务用）。
- **实测收益**：同任务同协议对照实验，3 路并行 vs 串行 **墙钟 -56%**（324s vs 745s），质量门禁两臂全绿零返工。

## 手动升级步骤

1. 备份并覆盖 5 个文件（对每个已部署的 runtime 副本执行）：
   - `runtime/server.py`、`runtime/lib/store.py`、`runtime/ui/index.html`、`runtime/cli.py` ← 用新版覆盖
   - `runtime/dispatch.py` ← 新增文件
2. 角色契约（`~/.zcode/agents/`）：修复 `frontend-dev.md` 占位符、复制 `backend-fast.md`。
3. 重启所有 daemon：`python runtime/daemon.py <port> stop` 后再启动；若当年是直接 `server.py <port>` 起的，先 `netstat -ano | findstr :<port>` 找 PID 再 `taskkill /PID <pid> /F`。
4. 验收（全过才算完成）：
   - `curl http://127.0.0.1:<port>/api/timetrack` 返回含 `wall_s` 的 JSON
   - 看板页面源码含 `time-block`
   - `python runtime/cli.py time` 出账单
   - `python runtime/dispatch.py prepare --help` 含 `--prompt-file` / `--cli-path`
   - `grep "^model:" ~/.zcode/agents/frontend-dev.md` 无占位符
5. 回滚：用备份覆盖回 3 个覆盖文件、删除 dispatch.py 即可（角色契约同理）。

## 给别人的升级提示词（整段复制发给对方的 ZCode 会话即可）

```text
请把我本地的 project-orchestrator skill（ZCode 版）升级到 v4.3 并完成验收，全程不动 runtime/projects/ 下的项目数据：

1. 定位：找到 skill 源仓库（含 SKILL.md / runtime/ / agents/ 的目录，git 仓库
   https://github.com/kimi0hhhh/project-orchestrator-skill）；再 netstat -ano | findstr ":87" 
   与 ":88" 找出所有正在运行的看板 daemon 及其所属 runtime 副本。
2. 源仓库先 git pull 拿到 v4.3（冲突时以远端 main 为准）。
3. 对每个 runtime 副本执行：把 runtime/server.py、runtime/lib/store.py、
   runtime/ui/index.html 先备份到 runtime/_backup_v4.3/，再用源仓库同名文件覆盖；
   并把源仓库的 runtime/dispatch.py、runtime/cli.py 一并复制过去
   （升级后 cli.py 必须有 time 子命令、dispatch.py 必须存在）。
4. 角色契约（~/.zcode/agents/）：若 frontend-dev.md 的 frontmatter 存在
   model: "<providerId>/<modelId>" 占位符就整行注释掉（不改会导致每次派前端必报
   Model provider is not configured）；再把源仓库 agents/backend-fast.md 复制进去。
5. 重启每个副本的 daemon：python runtime/daemon.py <port> stop 后重新启动；
   无法 stop 的（无 pid 记录）用 netstat 找 PID 后 taskkill /F 再用 daemon.py 拉起。
6. 验收（逐项执行并汇报，全过才算完成）：
   a. curl -s --noproxy '*' http://127.0.0.1:<port>/api/timetrack 返回含 wall_s 的 JSON；
   b. curl -s --noproxy '*' http://127.0.0.1:<port>/ | grep -c time-block ≥ 1；
   c. python runtime/cli.py time 能输出账单；
   d. python runtime/dispatch.py prepare --help 含 --prompt-file 与 --cli-path；
   e. grep "^model:" ~/.zcode/agents/frontend-dev.md 输出不含 <providerId>。
7. 最后汇报：升级了哪些副本、六项验收各自结果、备份与回滚方式。
   任何一项验收不过就停下来报告，不要自行变通。
```
