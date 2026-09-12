# 进度看板

> 文件化看板，与任务面板同步。主 Agent 每阶段更新一次。

## 阶段

| 阶段 | 负责 Agent | 状态 | 产出 |
|---|---|---|---|
| S0 立项 | user | ⬜ 待办 | PROJECT_BRIEF.md |
| S1 需求 | product-manager | ⬜ 待办 | 01-requirements / 02-prd / 03-ui-design / 04-wireframe |
| S2 架构 | architect + PM 会签 | ⬜ 待办 | 05~09 + 10-arch-review |
| S3 开发 | frontend ‖ backend | ⬜ 待办 | 前端壳 / 后端逻辑 / 契约实现 |
| S4 集成 | dev-lead | ⬜ 待办 | 15-code-review / build |
| S5 测试 | qa | ⬜ 待办 | 17-test-plan / 18-report / 04-defects |
| S6 终验 | product-manager | ⬜ 待办 | 19-pm-acceptance |
| S7 交付 | orchestrator | ⬜ 待办 | 交付说明 + 遗留清单 |

状态图例：⬜ 待办 · 🔵 进行中 · ✅ 通过门禁 · ⚠️ CONCERN 有条件放行 · ❌ 退回重做

## 返工计数

| 模块 | 累计返工轮次 | 上限 | 备注 |
|---|---|---|---|
| — | 0 | 3（超限主 Agent 裁定重写或砍需求） | |
