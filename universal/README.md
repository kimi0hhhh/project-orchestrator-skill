# Universal · 平台无关版（多 Agent 协作开发框架）

给**任何**具备（或可模拟）子代理派发能力的 agent 工具用的一版：协议、契约、协议文件、模板全部平台无关，平台细节收敛在一份待填的 `platform-config.md` 里。

## 目录

```
universal/
├── SKILL.md              # 协议本体（平台无关；含 A/B/C 三档能力档位定义）
├── platform-config.md    # 平台适配配置（移植时填：8 项原语 + 档位 + 命令模板）
├── PORTING.md            # 移植指南：原语映射表、定档规则、验证清单、自举提示词
├── agents/               # 6 份平台无关角色契约（由 tools/build_universal.py 从源契约生成）
├── protocols/            # gate-rules / handoff-schema / revision-loop
├── templates/            # PROJECT_BRIEF 产品输入书模板
└── install.sh            # 工作区安装脚本（bash install.sh <工作区>，不覆盖已有文件）
```

## 快速开始

```bash
bash universal/install.sh <你的项目工作区>
# 然后填两份文件：
#   .orchestrator/platform-config.md   ← 平台能力盘点（8 项原语 + 档位）
#   docs/PROJECT_BRIEF.md              ← 产品输入书
# 再把 SKILL.md 的唤醒规则加载进你的工具（或按 PORTING.md §五 的自举提示词让 agent 自己完成移植）
```

## 能力档位

| 档 | 要求 | 形态 |
|---|---|---|
| **A** | 子代理派发 + 工具白名单 | 完整形态：单层编排结构性堵死，看板/账本/看门狗全量 |
| **B** | 子代理派发，无白名单 | 同 A，一层编排降级为提示词强制 + 验收抽查 |
| **C** | 无子代理派发 | 单人多帽：依次戴 6 顶角色帽，工件与门禁不变 |

三档的铁律、门禁标准、工件编号、追溯留痕完全一致——**降级只动实现，不动标准**；所有降级必须显式标注，禁止静默省略。

## 设计要点

- **协议与平台解耦**：`SKILL.md` 里没有任何平台专有名词，派发原语/工具限制/上报命令全部指向 `platform-config.md`；
- **契约自动构建**：`agents/` 由 `tools/build_universal.py` 从 ZCode 源契约生成——改内容改源文件，重建即可，多平台契约不同步的老问题在构建层解决；
- **runtime 共享**：主仓库 `runtime/` 是纯 Python 标准库实现（零第三方依赖），天然平台无关，原语 4+5 支持即装，不支持则降级为 markdown 看板 + 文件账本（账本与门禁留痕是追溯底线，不可再砍）。

移植细节、原语映射表与自举提示词见 **[PORTING.md](PORTING.md)**。
