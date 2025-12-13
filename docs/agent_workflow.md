# Agent Workflow (Research / Case Lifecycle)

Source of truth for how agents should reason through a matter. Each tool should adapt the same phases to its task.

## Phase 1 — Intake & Diagnostics (Gatekeeper)
- **Intake Agent:** extract the story (facts) and the goal (client objectives) into a `ClientMatter` shape (client, opposing party, incident date, desired outcome).
- **Conflict Check:** query firm data for opposing party; if conflict is found, stop and reject.

## Phase 2 — Fact Investigation & Theory
- **Discovery/Fact Agent:** detect missing facts and ask clarifying questions until minimum viable facts are gathered.
- **Issue Spotter:** translate facts into legal issues/tags (e.g., “They fired me because I'm pregnant.” → Wrongful termination; statutes: Title VII/FMLA).

## Phase 3 — Research & Strategy (IRAC loop)
- **Research Agent:** find rules (statutes/cases) using tools (RAG, browser, external APIs) mapped to issues.
- **Strategy Synthesizer:** apply rules to facts; produce a concise strategy memo with strengths/risks and a recommendation.

## Phase 4 — Execution (Drafting)
- **Drafter Agent:** generate the work product (complaint, contract, demand letter, memo) using the strategy memo + client matter.

## Phase 5 — Review & QA
- **Review/Critique Agent:** simulate senior-partner review; critique drafts against objectives and strategy. If quality < threshold, loop back to drafting with specific feedback; else hand off to human-in-the-loop.

## Current implementation notes
- Research graph nodes: intake → qualification → jurisdiction/area → facts → conflict check → issue spotting → research plan → search loop → briefing. Briefing is formatted by phase/IRAC with strategy and next steps.
- Auth/guardrails: CSRF on refresh, RS256 + JWKS, login/refresh rate limits, research run/stream logging with trace/user/firm.
- Gaps to fill next: stream resilience/resume + frontend surfacing of conflict hits, CI target for synthetic evals, and per-tool UI polish.

## Tool workflows (intake → process → output)
- **Research**: normalize_intake → classify_matter → jurisdiction_and_area_classifier → fact_extractor → conflict_check → issue_generator → research_plan_builder → run_next_search_step (loop) → synthesize_briefing (IRAC/strategy/next_steps).
- **Summary**: normalize_intake → classify_matter → fact_extractor → synthesize_briefing (summary-focused).
- **Drafting**: normalize_intake → classify_matter → fact_extractor → issue_generator → synthesize_briefing → (drafting agent not yet wired).
- **Review**: normalize_intake → classify_matter → fact_extractor → issue_generator → synthesize_briefing → (critique loop TBD).

## Synthetic evals
- Scenarios live in `apps/agent/research_graph.py` (`SYNTHETIC_EVAL_SCENARIOS`) with helper `run_synthetic_eval(runner)`; pass a stubbed runner in tests to avoid network/tool calls.
- Conflict lookup: conflict_check now queries vector hits on opposing parties (distance threshold 0.3, top 3) and enriches with web lookup links.
- Research run/stream responses persist and return a `conflict_check` block so the UI can surface conflicts and runs can be resumed/audited.
- Streaming/resume: `/research/run/stream` emits start/update/done/error and persists snapshots on start and each update. Frontend falls back to polling and non-stream run on errors. Errors include `trace_id` for support.
- Smoke/eval: `scripts/smoke_api.sh` now runs an offline-safe synthetic eval stub; useful for CI without network or tools.
- Keepalive: streaming emits periodic `keepalive` events to keep proxies from timing out during long searches.
