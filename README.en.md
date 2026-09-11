# Project Orchestrator Skill · Multi-Agent Orchestration Mode

🇨🇳 中文版：[README.md](README.md)

**One-liner**: Turn one LLM agent into a *project owner* that orchestrates 6 single-accountability role sub-agents (PM / Architect / Frontend / Backend / Dev Lead / QA) through an S0–S7 stage pipeline — single writer, one-layer orchestration, read-only advisors, and gates that never leak.

## What it is

A **skill + role contracts** package for coding agents (ZCode, OpenCode family). Once loaded, the main agent stops coding by itself and behaves like a project owner:

- **Never does the work itself** — code, docs and decisions are dispatched to 6 role sub-agents; the main agent only dispatches, reviews, gates and communicates;
- **Enforced pipeline** — S0 kickoff → S1 requirements → S2 architecture (the API contract is the single law for both ends) → S3 dev (front/back in parallel) → S4 integration → S5 test → S6 acceptance → S7 delivery (three signatures required);
- **Gates never leak** — every stage ends with PASS / CONCERN / FAIL; CONCERN items must be logged;
- **Observable** — ships a runtime board (live browser view: stage progress, agent cards, token ledger, defect triage, timeline).

This repo also carries two evidence-backed upgrades:

1. **Star advisor pattern** — one accountable writer + read-only advisors that challenge a draft for exactly one round. Blind-judged PRD score 21 → 22.5; end-to-end product quality +13%;
2. **Dynamic staffing (triage L0–L2)** — classify tasks by *volume × decomposability* before dispatch. Simple tasks get one agent; advisor groups only pay off on complex ones (multi-agent costs ~15× tokens).

## Quick start

```bash
bash install.sh        # Windows: .\install.ps1
```

Then in a ZCode session say: 「启动主 Agent」 / "take over the project" — the orchestrator boots its board, reads `docs/PROJECT_BRIEF.md` and reports status, next step, and what needs your decision.

Full usage: [docs/USAGE.md](docs/USAGE.md) (Chinese) · Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Benchmark summary

Same-task PRD, 3 conditions × 2 runs, blind-judged (30-pt scale):

| Condition | Tokens/run | Score | Verdict |
|---|---|---|---|
| Single agent baseline | 21k | 21.0 | optimal for simple tasks |
| Skill invocation only | 32k | 17.25 | **negative return** |
| This framework (advisor + revision) | 122k | **22.5** | gains concentrate on metric rigor & edge cases |

End-to-end mini-product: this pipeline **35/40** vs sequential single-role **31/40** (+13%, at 2.2× cost). Full data: [docs/EVIDENCE.md](docs/EVIDENCE.md).

## Good fit / poor fit

✅ Full feature or small-product delivery where the whole artifact chain (PRD → contract → code → tests) matters; cost/metric-sensitive requirements.
❌ One-line fixes, throwaway scripts, small patches — a single agent is faster.

## Roadmap

- [x] v4.0 ZCode edition
- [ ] OpenCode edition
- [ ] Platform-neutral universal edition + adapter layer

See [docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE). Third-party skills and research: [docs/CREDITS.md](docs/CREDITS.md).
