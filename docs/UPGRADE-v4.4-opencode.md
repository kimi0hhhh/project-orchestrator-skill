# 升级指南 v4.4（OpenCode 版）

> 适用：已安装 **OpenCode 版** project-orchestrator（v4.1 ~ v4.3 任意版本）的环境。
> **本文只覆盖 `opencode/` 实现。** ZCode / WorkBuddy / 通用版未同步本版变更（见文末「待移植」）。
> 全程不触碰 `runtime/projects/` 下的项目数据。

## 一句话

v4.4 **不新增能力**，只做两件事：**让已有的东西被真正执行**，**让赔过的坑变成机器每次都会查的**。

## 本次变更

### 一、新增 · 评分尺（`scoring/`，6 个文件）

框架此前只能回答「合格吗」，回答不了「**我的检查方法好不好**」。

| 文件 | 作用 |
|---|---|
| `ruler.py` | **积木分**：8 块静态检查（E01 接口穷举 / E02 字段穷举 / E03 路径可解析 / B01 未定义标识符 / B02 金额格式化 / X01 静默吞异常 / G01 None 除零 / G02 json 兜底） |
| `project_score.py` | **项目分**：做完了吗 / 说的是真话吗 / 能用吗（三条线，**不合成加权总分**） |
| `ui_smoke.py` | **UI 点击冒烟（运行时）**：Chrome headless 逐页真点，断言零 JS 报错 |
| `defects.json` | 题库：该项目真实发生过的缺陷（已知根因 = 已知答案） |
| `verify_redgreen.py` | 红绿验证：注入已知缺陷，断言检查变红 |
| `README.md` | 维护纪律 + 4 条踩坑记录 |

**设计原则（三条）**：分数由脚本算、不由子 agent 自填；没有红过的检查等于没写过；
检查要认假阳性（干净代码上报红时先修检查）。

### 二、新增 · 看板端口纪律 + 服务身份守卫

修复三处硬伤：

1. **`cli.py` 在 `.port` 丢失时回退写死的 8777** —— 若 8777 上恰是**另一个工作区**的服务，
   子 agent 的 `spawn/progress/say/remember/finish` 会被**静默写进别人的看板**。
   现在删掉兜底并加 **fail-closed 身份守卫**：认不出归属就拒写（exit 2）。
2. **`daemon.py` 回退 8777 撞上别人的服务** → 误报「已在运行」，什么都不启动，还把人指错地方。
   现在三层身份判定（问服务 `/api/whoami` → 问进程命令行 → 问项目名），认不出按「被占」处理。
3. **四处端口约定**（8778/8777/8790/8790）→ 收敛到 `.port` 单源；**端口由用户指定**，
   脚本不自动分配，被占时明确报出占用者，**不偷偷换端口**。

`daemon.py` 从 149 行降为 37 行兼容层（转发 `board.py`），消掉重复实现。

### 三、新增 · 交付与收尾闭环

- **`20-closeout` 欠账台账**注册为一等工件（`handoff-schema` §3）。
- **`gate-rules` S7 就绪清单加第 5、6 项**：欠账台账已落盘 / `retro` 第 1 问必须带**漏网数**。
- **`runtime/archive.py`**：交付包归档命令（带走 bus/plan/ledger/memory + 状态文件），
  并带「事件流 0 行」告警。

> 起因：FundLens 终验判 NOK 后 S7 从未执行，4 条未交付 + 4 条部分交付全部断在项目边界上，
> 没有任何机制把它们带进下一轮。**项目可以烂尾，欠账不能凭空消失。**

### 四、修复 · 路径漂移

协议与契约里 14 处引用 `docs/`，而实际目录是 `04_工程文档/` → 唤醒流程第一步必失败、
`dispatch` pre-flight 必拒绝出 prompt。已全部更正，并新增 `E03` 积木**机器监控复发**。

### 五、挂载 · 把已有的东西接进流程

| 挂什么 | 挂到哪 |
|---|---|
| 尺子 | `SKILL.md` `## 验收` 加「判定前先跑」；`S7` 加 `project_score` |
| `ui_smoke` | `G-QA-02` 加红线（exit 2 → FAIL；无浏览器 → CONCERN，**不许静默跳过**） |
| 积木记账 | `dispatch.py close --blocks "R,C,D"` → 写进 gate-log 建议行 |
| 端口纪律 | `SKILL.md` 唤醒流程 + `/board` + `/takeover` 三条路径 |

**为什么单列这一节**：框架最深的病不是缺东西，是**写了没挂载点**——
`reality-checker` 写在能力地图里 0 次派发；18 条加固里 14 条从没被验证过。

### 六、实测

| 项 | 结果 |
|---|---|
| 积木分（静态） | 检查通过 6/8；题库覆盖 **7/8**（5 条确认修复 / 2 条检出仍在） |
| 红绿验证 | 3 条静态检查全部「变红 ✔ 有牙」 |
| UI 点击冒烟 | 718 次点击 / 7 页 / 22 个菜单按钮全点到 / 0 报错 |
| UI 冒烟自检 | 干净绿 + 注入 PM-D1 变红（`Uncaught ReferenceError: openEdit is not defined`） |
| 耗时 | 静态 0.3 秒；UI 冒烟 6.8 秒；**全部 0 token**（脚本不调模型） |

## 手动升级步骤

1. **同步 `opencode/` 子树**（7 个 agents + 5 个 commands + 5 个 protocols + SKILL.md
   → `.opencode/` 对应位置；`backend-fast.md` 为本版补入）。
2. **新增 `scoring/`**：把 `opencode/scoring/` 整个拷到**工作区根**（与 `runtime/` 同级）。
3. **覆盖 runtime**：把 `opencode/runtime/` 下 6 个文件覆盖到工作区 `runtime/`
   （`board.py` `cli.py` `daemon.py` `server.py` `dispatch.py` `archive.py`）。
   **其余 runtime 文件不要动**（完整 runtime 在仓库根 `runtime/`）。
4. **重启看板**：`python runtime/board.py stop` → `python runtime/board.py open --port <端口>`。
   **端口由用户指定**，被占时脚本 exit 2 会报出占用者，换一个再试。
5. 旧的 `daemon.py <port>` 写法仍可用（转发到 `board.py`），但**不要再直接调它**。

## 验收（全过才算完成）

```bash
python scoring/ruler.py                     # exit 0；输出「检查通过 n/8」
python scoring/verify_redgreen.py           # exit 0；3 条都显示「变红 ✔ 检查有牙」
python scoring/ui_smoke.py --selftest       # exit 0；干净绿 + 注入红  ← 需 Chrome/Edge
python scoring/ui_smoke.py                  # exit 0；打印点击次数与证据夹具覆盖率
python runtime/board.py check --port 8777   # 若该端口被别的工作区占用 → exit 2 且打印占用者
python runtime/cli.py projects              # 对本工作区看板 exit 0；对别人的服务 exit 2 拒写
python runtime/archive.py --pid <项目id>     # 生成归档目录 + RESTORE.md
```

**任一项不过就停下来报告，不要自行变通。**

## 回滚

- `scoring/` 整目录删除即可（无副作用，不被 runtime 依赖）。
- runtime 6 个文件用升级前备份覆盖；`daemon.py` 恢复旧版即可回到「自带端口逻辑」的老行为。
- 角色契约用 git 历史版本覆盖。

## 待移植（按 `docs/VERSIONS.md` 的同步纪律）

本版含**协议级变更**，另三个实现尚未同步：

| 变更 | 需移植到 |
|---|---|
| 门禁 `G-QA-02` 加运行时点击红线 | ZCode / WorkBuddy / 通用版 |
| 新增工件 `20-closeout` + `S7` 就绪清单第 5/6 项 | 同上 |
| `scoring/` 评分尺（脚本平台无关，路径按各实现的安装根调整） | 同上 |

**移植完成后应统一协议版本号并打 tag。** 在各平台回执文档里记录移植差异之前，
不要声称四实现同版本。
