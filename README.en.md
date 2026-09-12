# Project Orchestrator · A Multi-Agent Collaboration Dev Framework

![Project Orchestrator framework banner](docs/assets/banner.svg)

![version](https://img.shields.io/badge/version-v4.1-green) ![stage](https://img.shields.io/badge/status-beta-blue) ![python](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white) ![platform](https://img.shields.io/badge/platform-ZCode%20%7C%20OpenCode-orange) ![license](https://img.shields.io/badge/license-MIT-red) ![evidence](https://img.shields.io/badge/dev_validated-2%20real%20products-8A2BE2)

**One-liner**: An installable **multi-agent delivery framework** — *one project owner + 6 single-accountability roles + on-demand advisors + stage gates* — the main agent never touches the work itself; it dispatches, reviews, and gates. Single writer, one-layer orchestration, read-only advisors, no gate-keeping shortcuts. This is **not a tool-specific trick**: it is designed for any agent dev tool with sub-agent dispatch. **ZCode and OpenCode are the first two implementations** (this repo ships the ZCode edition first). Delivery is gated — no promise of one-shot perfection.

> State your requirements, answer a few short follow-up questions, and hours later a complete product project is sitting on your machine: a PRD, an API contract, runnable code, a test report — plus a war room recording how six agents worked together. Fair warning: it is markedly slower than doing it yourself — see "An honest look" at the end for the itemized bill.

> 🇨🇳 中文版: [README.md](README.md)

---

## What it is

Not a prompt pack — an installable **collaboration dev framework** in four layers: protocol (rules + research grounding), pipeline (6 role contracts + S0–S7), live board (runtime), and ledgers (tokens/events/gates). Once loaded, the main agent behaves like a project owner:

- **Dispatches and reviews only** — code, docs and decisions go to 6 single-accountability roles (PM / Architect / Frontend / Backend / Dev Lead / QA); every artifact has exactly one writer;
- **Enforced pipeline** — S0 kickoff → S1 requirements → S2 architecture (the API contract is the single law) → S3 dev (file-isolated parallelism) → S4 integration → S5 test → S6 acceptance → S7 delivery (three signatures required);
- **A gate at every stage** — PASS / CONCERN / FAIL; CONCERN items must be logged;
- **Two research-backed mechanisms** — the **star advisor pattern** (read-only advisors challenge a draft for one round) and **dynamic staffing L0–L2** (simple tasks get one agent, so the ~15× token cost of multi-agent — measured on research tasks — never burns on work that doesn't need it).

The framework is platform-decoupled: swap the host tool, swap the adapter — not the framework. The ZCode edition is shipped; the OpenCode edition reuses the same contracts and stage definitions verbatim.

## Quick start

```bash
# 1. Install (ZCode — one of the first two implementations)
bash install.sh        # Windows PowerShell: .\install.ps1

# 2. In a ZCode session, say any wake phrase:
#    "launch the main agent" / "take over the project" / "continue per ORCHESTRATOR"
# 3. The orchestrator boots: reads ORCHESTRATOR.md, starts the board, reports
#    current stage / who is running / next step / pending decisions
# 4. Fill in docs/PROJECT_BRIEF.md and let it run
```

Full usage: [docs/USAGE.md](docs/USAGE.md) (docs are currently Chinese-only)

## Pipeline & topology

![S0-S7 delivery pipeline](docs/assets/pipeline.svg)

![Role topology](docs/assets/topology.svg)

Each stage: one accountable role, numbered artifacts, one gate. Details: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Standing on shoulders

This framework converges two lines of open-source work: **open skill sets** (methodology wired directly into role contracts) and **2025–2026 multi-agent research** (each row: core finding → what we adopted / where we took a measured position).

### Open-source skills referenced

Role contracts carry a per-role "recommended skills" list; the main agent invokes them by name at dispatch time. The framework **does not bundle or modify** these skills — swap in your own equivalents and it still runs:

| Skill set | Skills referenced | Serving roles |
|---|---|---|
| [pm-skills](https://github.com/) | create-prd · prioritization-frameworks · pre-mortem · retro · user-stories · interview-script · user-personas · test-scenarios · dummy-dataset · sql-queries | PM (S1/S6) · QA (S5) |
| [Matt Pocock's skill set](https://github.com/mattpocock/skills) (via setup-matt-pocock-skills) | codebase-design · domain-modeling · tdd · implement · prototype · code-review · triage · diagnosing-bugs · resolving-merge-conflicts · research · grill-with-docs | Architect (S2) · FE/BE (S3) · Dev Lead (S4) · co-sign research |

Full reference map and swap instructions: [docs/CREDITS.md](docs/CREDITS.md). Credits to the authors of both sets — this framework's role methodology stands on their shoulders.

### Research grounding

| Source | Core finding | Our take |
|---|---|---|
| [Anthropic · How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) | Multi-agent costs ~**15× tokens** (measured on research tasks); coding parallelizes far less than research | Adopted: no parallelism by default; only file-isolated front/back in S3; triage before dispatch |
| [Anthropic · Agent Teams](https://code.claude.com/docs/en/agent-teams) (2026-02) | 3–5 teammates, no nesting, sequential/same-file work goes back to one session | Adopted: one-layer orchestration enforced structurally via contract `tools` allowlist, not prompt discipline |
| [Cognition · Don't Build Multi-Agents](https://cognition.com/blog/dont-build-multi-agents) | Parallel writers exchange **implicit decisions** neither can see; merging = conflict | Adopted: one writer per artifact. Diverged: we don't retreat to a single thread — gates + read-only advisors keep the multi-view |
| [Cognition · What's Actually Working](https://cognition.com/blog/multi-agents-working) (2026-04) | What actually works in production: clean reviewers with **zero shared context** | Adopted: advisors never talk to each other, never write, never gate — exactly this shape |
| [LangChain · Benchmarking multi-agent architectures](https://www.langchain.com/blog/benchmarking-multi-agent-architectures) | The supervisor relay layer is the main loss point (+50% after fixing handoffs) | Adopted: exactly one orchestration layer; the main agent relays by quoting, not paraphrasing |
| [Google · Towards a Science of Scaling Agent Systems](https://arxiv.org/abs/2512.08296) | On sequential tasks multi-agent loses **−39~70%** across the board | Adopted: architecture/contract stages (S0–S2) never parallelize; when unsure, triage downgrades |
| [Dochkina · Drop the Hierarchy](https://arxiv.org/abs/2603.28990) | Pre-assigned seniority personas are a liability (self-organizing +14%) | Adopted: advisor prompts carry a *perspective + challenge format*, never a "chief/director" script |
| [Equal-budget study](https://arxiv.org/abs/2604.02460) | Without token-matched controls you measure compute, not architecture | Adopted: reproduction guide mandates equal budgets |
| [MAST failure taxonomy](https://arxiv.org/abs/2503.13657) | 7 SOTA multi-agent systems (incl. SDLC frameworks like MetaGPT/ChatDev) fail at **41–86.7%** overall | Response: we admit the resemblance to SDLC role-play; gates, numbered artifacts and contract↔code alignment checks are what cut against those failure modes |

One sentence sums up all nine: **multi-agent failures cluster around "writing"** — so this framework confines parallelism to file-isolated S3, and makes everything else (review, challenge, observation) read-only.

## Five iron rules

Break any one and the protocol voids itself:

1. The main agent never does the work — if it does, nobody reviews;
2. Never parallel-dispatch agents writing the same artifact — reads parallelize, writes never;
3. Gates never leak — CONCERN items get logged, "close enough" never trades for progress;
4. Every sub-agent sees only the files it needs;
5. Interrupt the user only for four defined situations; otherwise push forward autonomously.

## Board: a war room that grows with the project

Watch the multi-agent interaction live in the browser — stages, cards, message stream, token ledger:

![Board main view](docs/assets/board-main.png)

- **Console**: stage / completion / pending decisions; opens the battle map in one click;
- **Agent cards**: status, progress, model triple-reporting, silence timer, resume with memory;
- **Message stream**: deliveries and progress pinned live, artifacts viewable on click;
- **Token ledger**: per-role consumption bars, real values read from session logs.

![Battle map overlay](docs/assets/board-plan.png)

How it works: [docs/BOARD.md](docs/BOARD.md) (screenshots use demo data).

## Development validation (brief)

The framework has been validated through multiple real development runs (controlled comparisons + an end-to-end dual pipeline + two real products shipped through the full pipeline): advisors caught genuine design flaws at draft time (e.g. a "retention north-star metric" for a backend-less product), and gates/defect-triage worked as designed. The self-run controlled experiments are small (n=2, not budget-matched) and serve as **directional hints only, not authoritative evidence** — correctness claims rest primarily on the research grounding above. Data and methods: [docs/EVIDENCE.md](docs/EVIDENCE.md).

## An honest look

**Strengths (development-validated, directional)**

1. **Delivers a whole product autonomously**: given a clear brief plus a few clarifying answers, it lands the full chain — requirements → PRD → contract → runnable code → tests (two real products shipped through the full pipeline);
2. **Effective quality guards**: advisors caught regulatory-grade red lines at draft time (e.g. a "retention north-star metric" for a backend-less product); gates and defect triage worked as designed;
3. **Observable process**: the board shows stages, cards, message flow and the token ledger live — multi-agent work stops being a black box.

**Costs (design trade-offs, not bugs)**

1. **Markedly slower**: multiple dispatch rounds, gates and revisions make end-to-end time significantly longer than a single agent just doing it;
2. **Token-hungry**: advisor groups, revision rounds and board polling all burn tokens — estimated at several times a single-agent baseline.

**When not to use it**: tasks with a single decision chain that won't decompose; when you want a patch, not an artifact chain; when your token/time budget cannot absorb a revision round. Hit any of these and use a single agent — triage L0 exists precisely to write this rule into the framework. Changes under a day of work go through the **change-triage fast lane** (C0 light edit = 1 dispatch + 1 gate-log line; C1 small feature only co-signs when the contract changes) — no need, and no right, to run the full pipeline.

## Repository layout

```
├── SKILL.md            # Protocol core (installs to ~/.zcode/skills/project-orchestrator/)
├── agents/             # 6 role contracts (install to ~/.zcode/agents/)
├── docs/
│   ├── BOARD.md          # Visual board (screenshots + how it works)
│   ├── USAGE.md          # Detailed usage (install/wake/dispatch/board/acceptance)
│   ├── ARCHITECTURE.md   # Architecture
│   ├── DESIGN.md         # Design decisions (research citations)
│   ├── EVIDENCE.md       # Experiments: probes, demos, controlled runs
│   ├── SECURITY.md / CREDITS.md / ROADMAP.md
│   └── assets/           # Diagrams and board screenshots
├── install.sh / install.ps1
├── DESCRIPTION.md        # GitHub repo description
└── LICENSE
```

## Roadmap

> Changelog: v4.0 (ZCode edition, one of the first two implementations, this repo) shipped.

- [ ] OpenCode edition (the second; shared contracts & stage definitions)
- [ ] Platform-neutral protocol + adapter layer

See [docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE). Third-party skills and research: [docs/CREDITS.md](docs/CREDITS.md). Leakage-audited; see [docs/SECURITY.md](docs/SECURITY.md).
