# 数据隔离与隐私声明 / Data isolation & privacy

本仓库面向开源发布，作者与贡献者在提交前按下表自查。**发现泄漏请提 issue，我们会立即处理并轮换相关凭据。**

This repository is intended for public release. Every commit is screened against the checklist below. If you find any leakage, please open an issue immediately.

## 已执行的隔离措施 / What we did

| 检查项 | 结果 |
|---|---|
| 机器路径 / 用户名（`C:\Users\<name>` 等） | ✅ 全文扫描，无残留 |
| API key / token / 凭据 | ✅ 仓库不存储任何凭据；配置示例一律 `<providerId>/<modelId>` 占位符 |
| 私有供应商信息（供应商 UUID / 名称 / baseURL） | ✅ 已脱敏为占位符；模型路由文档仅描述机制，不引用真实供应商 |
| 私有项目名 / 业务数据 | ✅ 实验与示例全部使用虚构任务（购物车、番茄钟、习惯打卡） |
| 邮箱 / 电话 | ✅ 无 |
| 实验数据 | ✅ 仅保留 token 数与评分，无账号关联信息 |

## 提交者须知 / For contributors

1. **模型路由示例**：`agents/frontend-dev.md` 里的 `model: "<providerId>/<modelId>"` 是占位符——请勿把你自己的供应商 id/key 提交进来；
2. **运行时数据不入库**：`.gitignore` 已排除 `runtime/projects/*/state.json`、`ledger.jsonl`、`.port`、`.server.pid`、日志（若你把 runtime 放进 fork）；
3. **git 身份**：公开仓库的提交历史含作者名与邮箱。建议用 provider 的 noreply 地址或单独的开源身份（`git config user.email`）；
4. **实验复现**：按 EVIDENCE.md §7 复现时产生的工件（草稿/评分/日志）请勿直接提交，先脱敏。

## 泄漏应急 / If leakage happens

轮换凭据 → 从历史中彻底移除（`git filter-repo`）→ force push → 在 SECURITY.md 记录事件。
