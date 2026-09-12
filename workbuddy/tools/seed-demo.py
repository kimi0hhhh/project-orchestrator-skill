# -*- coding: utf-8 -*-
"""一键造 demo 项目：给看板灌三个真实编排现场，用于验收与演示。

    先起服务：python runtime/board.py wmi
    再造数：  python tools/seed-demo.py

造完的项目落在 runtime/projects/，用完可删：
    python runtime/cli.py projects
    # 或直接删 runtime/projects/<id> 与 projects.json 里的对应条目

三个 demo 覆盖的机制：双线并行 + 草稿检查点增量评审（demo-pipeline）、
S5 测试前置 + 终验阻塞（demo-app）、C1 增量快车道 + 星形参谋（demo-harness）。
脚本幂等：同名项目先删后建，可反复跑。

注意：直连回环必须绕开企业代理（本机 HTTP_PROXY 会把 127.0.0.1 也送去代理，
返回 502），所以下面用 ProxyHandler({}) 的 opener。
"""
import json
import sys
import urllib.request

PORT = int(open(r"~/.workbuddy/skills/project-orchestrator/runtime/.port").read().strip())
BASE = f"http://127.0.0.1:{PORT}"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 绕开企业代理，直连回环

FAILS = []
N = 0


def post(path, **payload):
    global N
    N += 1
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(BASE + path, data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with OPENER.open(req, timeout=8) as r:
            out = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        FAILS.append((path, str(e)[:110]))
        return {}
    if out.get("error"):
        FAILS.append((path, str(out["error"])[:110]))
    return out


def make_project(pid, name, brief, stage_state, goal, blockers, nxt, models):
    post("/api/projects", action="delete", id=pid)          # 幂等：先删旧
    post("/api/projects", id=pid, name=name, brief=brief)
    for st, status, pct, note in stage_state:
        post("/api/plan", project=pid, stage=st, status=status, progress=pct, note=note)
    post("/api/plan", project=pid, meta=1, title=name, goal=goal,
         blockers=blockers, next=nxt)
    for a, m in models:
        post("/api/settings/model", project=pid, agent=a, model=m)


# ══════════════════════════════════════════════════════════════════════
# ① 基金监控 v3.1 · 行情适配层 —— S3 开发中，前后端双线并行
# ══════════════════════════════════════════════════════════════════════
P1 = "demo-pipeline"
make_project(
    P1, "基金监控 v3.1 · 行情适配层",
    "把行情数据源抽象成 provider 适配层：腾讯实时为主，东财/天天基金降级，统一估值口径。",
    [("S0", "done", 100, "立项：v3.1 范围钉死为「行情层解耦 + 实时估值口径统一」"),
     ("S1", "done", 100, "需求：22 只持仓 + 6 类板块的估值口径梳理完毕"),
     ("S2", "done", 100, "架构：provider 抽象 + 09-api-contract.md 冻结（含 4 类错误码）"),
     ("S3", "working", 52, "开发：后端 provider 适配器与前端卡片双线并行"),
     ("S4", "working", 30, "集成：dev-lead 已介入草稿完成检查点（增量评审，不等全完工）"),
     ("S5", "working", 20, "测试前置：17-test-plan 已起草（只依赖契约，不等实现）"),
     ("S6", "pending", 0, "终验"),
     ("S7", "pending", 0, "交付")],
    "v3.1 行情适配层：一处取数，六类板块共用一套估值口径",
    "东财 F10DataApi 已返 HTML，降级路径需实测兜底",
    "等前后端草稿完成检查点 → dev-lead 集成裁定 → 18-test-report",
    [("product-manager", "reasoning"), ("architect", "reasoning"),
     ("backend-dev", "default"), ("frontend-dev", "default"),
     ("qa", "default"), ("dev-lead", "reasoning")])

post("/api/spawn", project=P1, agent="orchestrator", pid=41000, model="default",
     task_id="demo-pipeline/S3", task_title="编排：S3 双线并行")
post("/api/progress", project=P1, agent="orchestrator", pct=52, phase="S3",
     step="S3 双线并行中，等两个草稿检查点")

post("/api/spawn", project=P1, agent="product-manager", pid=41001, model="default",
     task_id="demo-pipeline/S1", task_title="需求收敛")
post("/api/finish", project=P1, agent="product-manager",
     step="PRD v3.1 已交付（22 只持仓口径核对完毕）",
     artifact="docs/00-charter/02-prd.md",
     artifact_summary="v3.1 PRD：行情层解耦 + 估值口径统一")

post("/api/spawn", project=P1, agent="architect", pid=41002, model="default",
     task_id="demo-pipeline/S2", task_title="provider 抽象与契约")
post("/api/finish", project=P1, agent="architect",
     step="09-api-contract.md 冻结，含 4 类错误码",
     artifact="docs/00-charter/09-api-contract.md",
     artifact_summary="provider 接口契约（冻结版）")
post("/api/message", project=P1, **{"from": "architect", "to": "dev-lead",
     "body": "契约已冻结。注意 seg[3] 是当前价、seg[4] 是昨收——估值口径必须用 (3-4)/4，别用涨跌幅字段。",
     "artifact": "docs/00-charter/09-api-contract.md", "type": "artifact"})

post("/api/spawn", project=P1, agent="backend-dev", pid=41003, model="default",
     task_id="demo-pipeline/S3", task_title="provider 适配层实现")
post("/api/progress", project=P1, agent="backend-dev", pct=65, phase="S3", context_messages=38,
     task_id="demo-pipeline/T-0302", task_title="东财降级路径兜底",
     step="腾讯实时 provider 已通；东财降级路径返 HTML，需 Content-Type 嗅探后兜底")
post("/api/heartbeat", project=P1, agent="backend-dev",
     step="长跑：批量拉 22 只持仓估值（qt.gtimg.cn 混合批量）")
post("/api/task", project=P1, id="demo-pipeline/T-0302", title="东财降级路径兜底",
     agent="backend-dev", phase="S3", status="working", progress=65)
post("/api/message", project=P1, **{"from": "backend-dev", "to": "frontend-dev",
     "body": "字段名我按契约锁死了：price / prev_close / est_nav。你那边直接接，别自己再算一遍，否则误差来源分不清。"})
post("/api/message", project=P1, **{"from": "backend-dev", "to": "orchestrator",
     "body": "刚才静默 300s 是在跑 22 只的批量拉取，人没死。"})
post("/api/interrupt/clear", project=P1, agent="backend-dev",
     note="实测客户端会话仍在活动（workbuddy-session:working），静默系长批量拉取所致，撤销中断判定")
post("/api/memory", project=P1, agent="backend-dev", section="坑位记录",
     text="东财 F10DataApi 现返 HTML，必须 Content-Type 嗅探后再解析，否则静默返回空数据。")

post("/api/spawn", project=P1, agent="frontend-dev", pid=41004, model="default",
     task_id="demo-pipeline/S3", task_title="实时估值卡片重构")
post("/api/progress", project=P1, agent="frontend-dev", pct=40, phase="S3", context_messages=21,
     step="卡片骨架已出（v0 可渲染），已在草稿完成检查点上报 dev-lead")
post("/api/message", project=P1, **{"from": "frontend-dev", "to": "dev-lead",
     "body": "草稿完成检查点到了：估值卡片 v0 已可渲染，请来增量评审，别等后端全完工。"})

post("/api/spawn", project=P1, agent="dev-lead", pid=41005, model="default",
     task_id="demo-pipeline/S4", task_title="增量评审 + 集成裁定")
post("/api/progress", project=P1, agent="dev-lead", pct=30, phase="S4",
     step="已对前端草稿检查点完成第一轮增量评审")
post("/api/message", project=P1, **{"from": "dev-lead", "to": "backend-dev", "type": "reject",
     "body": "返工 1 处：降级路径必须抛 ProviderDegraded，不能 return None——否则前端分辨不出「没数据」和「源挂了」。"})

post("/api/spawn", project=P1, agent="qa", pid=41006, model="default",
     task_id="demo-pipeline/S5", task_title="17-test-plan 前置起草")
post("/api/progress", project=P1, agent="qa", pct=20, phase="S5",
     step="17-test-plan 起草中——用例只依赖契约、不依赖实现")

post("/api/note", project=P1, body="估值误差要对齐养基宝口径，差 0.01% 也要查清是哪一层引入的。",
     to="orchestrator", priority="urgent")


# ══════════════════════════════════════════════════════════════════════
# ② 演示应用事件台账 v1 收尾 —— S5 测试 + S6 终验阻塞
# ══════════════════════════════════════════════════════════════════════
P2 = "demo-app"
make_project(
    P2, "演示应用事件台账 v1 收尾",
    "v1 上线前三件套：T+3/T+15 补 placebo、影子盘、接入产品壳。事件台账为 P0 补强首项。",
    [("S0", "done", 100, "立项：v1 已定稿，进入上线前收尾"),
     ("S1", "done", 100, "需求：三件套 + 事件台账 P0 清单确认"),
     ("S2", "done", 100, "架构：台账 schema 与 event_engine 对接方式已定"),
     ("S3", "done", 100, "开发：event_engine 已接入 H=3 + abstention"),
     ("S4", "done", 100, "集成：诚实 stacked hit rate 跑通"),
     ("S5", "working", 70, "测试：17-test-plan 已前置产出；18-test-report 执行中，placebo 用例排队"),
     ("S6", "blocked", 35, "终验：卡在 T+15 placebo 数据未回"),
     ("S7", "pending", 0, "交付：影子盘上线")],
    "演示应用 v1 从研发态推进到可观察态",
    "绿徽 60% 门控仍全灰，需 ≥300 日新闻流填充",
    "T+15 placebo → S6 终验 → 影子盘",
    [("product-manager", "reasoning"), ("qa", "reasoning"), ("dev-lead", "reasoning"),
     ("architect", "default"), ("backend-dev", "default")])

post("/api/spawn", project=P2, agent="orchestrator", pid=42000, model="default",
     task_id="demo-app/S5", task_title="编排：S5 执行与终验准备")
post("/api/progress", project=P2, agent="orchestrator", pct=58, phase="S5",
     step="S5 执行中，S6 终验阻塞待解")

post("/api/spawn", project=P2, agent="architect", pid=42001, model="default",
     task_id="demo-app/S2", task_title="事件台账 schema")
post("/api/finish", project=P2, agent="architect",
     step="台账 schema 定稿（六态枚举复用，胜率口径与信号体系一致）",
     artifact="docs/event-ledger-schema.md",
     artifact_summary="事件台账 schema：六态枚举 + 胜率口径")

post("/api/spawn", project=P2, agent="qa", pid=42002, model="default",
     task_id="demo-app/S5", task_title="17-test-plan + 18-test-report")
post("/api/progress", project=P2, agent="qa", pct=70, phase="S5", context_messages=44,
     task_id="demo-app/T-0511", task_title="T+3 / T+15 补 placebo 检验",
     step="17-test-plan 已前置交付；18-test-report 执行中，placebo 用例排队")
post("/api/task", project=P2, id="demo-app/T-0511", title="T+3 / T+15 补 placebo 检验",
     agent="qa", phase="S5", status="working", progress=70)
post("/api/message", project=P2, **{"from": "qa", "to": "dev-lead",
     "body": "T+3 placebo 结果：打乱标签后命中率回落到 51.2%，说明 56.0% 不是过拟合。T+15 待跑。"})
post("/api/message", project=P2, **{"from": "qa", "to": "orchestrator",
     "body": "17-test-plan 是按契约写的、不依赖实现——这就是测试前置的意义：S3 还在改的时候用例已冻结。"})
post("/api/memory", project=P2, agent="qa", section="口径纪律",
     text="命中率报告必须给 placebo 对照值；只报超额、不报对照的做法一律视为不可复现。")

post("/api/spawn", project=P2, agent="dev-lead", pid=42003, model="default",
     task_id="demo-app/S6", task_title="终验裁定")
post("/api/progress", project=P2, agent="dev-lead", pct=35, phase="S6",
     step="复核 frozen holdout 60 天禁调参纪律执行情况")
post("/api/blocked", project=P2, agent="dev-lead", step="等 T+15 placebo 数据，暂无法终验")

post("/api/note", project=P2, body="placebo 必须跑完才允许进影子盘，不许跳步。",
     to="orchestrator", priority="urgent")


# ══════════════════════════════════════════════════════════════════════
# ③ DeepSeek Harness 一键部署包 —— S1 需求 + 星形参谋会
# ══════════════════════════════════════════════════════════════════════
P3 = "demo-harness"
make_project(
    P3, "DeepSeek Harness 一键部署包",
    "面向非技术人群的下载即用安装包：内嵌运行时 + 桌面端可视化 UI，渠道走闲鱼。",
    [("S0", "done", 100, "立项：可行性已过，确定「下载安装 + 可视化 UI」形态"),
     ("S1", "working", 60, "需求：MVP 边界收敛中（环境方案待定）"),
     ("S2", "working", 15, "架构：星形参谋会已启动，主笔未落笔（等一轮挑刺）"),
     ("S3", "pending", 0, "开发"),
     ("S4", "pending", 0, "集成"),
     ("S5", "pending", 0, "测试"),
     ("S6", "pending", 0, "终验"),
     ("S7", "pending", 0, "交付：闲鱼渠道上架")],
    "非技术用户双击即用，成本可控、可复现",
    "环境方案未定（内嵌运行时 vs 引导安装）；闲鱼渠道合规口径未确认",
    "星形参谋会定 MVP 边界 → 转 C1 增量快车道进 S2",
    [("product-manager", "reasoning"), ("architect", "reasoning")])

post("/api/spawn", project=P3, agent="orchestrator", pid=43000, model="default",
     task_id="demo-harness/S1", task_title="编排：MVP 边界收敛")
post("/api/progress", project=P3, agent="orchestrator", pct=60, phase="S1",
     step="S1 需求收敛中；已判为 C1 增量，不走 S1–S7 全流程")

post("/api/spawn", project=P3, agent="product-manager", pid=43001, model="default",
     task_id="demo-harness/S1", task_title="MVP 边界与成本口径")
post("/api/progress", project=P3, agent="product-manager", pct=60, phase="S1", context_messages=33,
     task_id="demo-harness/T-0107", task_title="成本口径调研（运行时体积 / 打包方式）",
     step="MVP 边界收敛中：先做单文件安装包，自动更新推后")
post("/api/task", project=P3, id="demo-harness/T-0107", title="成本口径调研（运行时体积 / 打包方式）",
     agent="product-manager", phase="S1", status="working", progress=60)
post("/api/message", project=P3, **{"from": "product-manager", "to": "orchestrator",
     "body": "建议按 C1 增量走：不回炉 S1–S7 全流程，只派架构师补环境方案一节，其余端不受影响。"})
post("/api/message", project=P3, **{"from": "orchestrator", "to": "architect", "type": "directive",
     "body": "启动星形参谋会：你作唯一主笔出环境方案，另请两只只读参谋挑刺（不写工件、不担门禁、互不对话）。"})

post("/api/spawn", project=P3, agent="architect", pid=43002, model="default",
     task_id="demo-harness/S2", task_title="环境方案（参谋会主笔）")
post("/api/blocked", project=P3, agent="architect", step="等参谋第一轮挑刺结果，暂不落笔")
post("/api/memory", project=P3, agent="product-manager", section="渠道备忘",
     text="闲鱼对「软件安装包」类目无明确禁售，但描述里不能出现「破解 / 外挂」类词。")

post("/api/note", project=P3, body="环境方案出来后先给我一页纸结论，别直接开写文档。",
     to="orchestrator")


# ══════════════════════════════════════════════════════════════════════
print("=" * 60)
print(f"造数完成：{N} 次 API 调用，失败 {len(FAILS)} 次")
print("=" * 60)
for path, msg in FAILS:
    print(f"  [FAIL] {path}  {msg}")

with OPENER.open(BASE + "/api/projects", timeout=5) as r:
    print("\n项目库：")
    print(json.dumps(json.loads(r.read().decode("utf-8")), ensure_ascii=False, indent=2))

sys.exit(1 if FAILS else 0)
