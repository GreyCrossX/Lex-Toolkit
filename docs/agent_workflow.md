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
- Drafting agent (MVP): intake (doc_type/objective/audience/tone/language/context/facts/constraints/requirements/research trace/summary) → structured drafting stub that returns draft text, sections, risks, assumptions, open questions. Endpoints `/draft/run`, `/draft/run/stream`, `/draft/{trace_id}`, health `/draft/health`; UI streams + resume + health dot.
- Review/Critique agent (MVP): intake (doc_type/objective/audience/guidelines/jurisdiction/constraints/text/sections/research trace/summary) → normalize → classify → fact extraction → conflict_check → structural_review → detailed_review → prioritize_issues → revision_suggestions → qa_pass → summarize_review. Endpoints `/review/run`, `/review/run/stream`, `/review/{trace_id}`, health `/review/health`; UI streams updates (findings/issues/suggestions/risks/conflict), resume by trace, health dot.
- Auth/guardrails: CSRF on refresh, RS256 + JWKS, login/refresh rate limits, all run/stream endpoints log with trace/user/firm. Conflict hits surface to UI for both research and review.
- Synthetic evals: research synthetic eval stub available offline; drafting/review smoke stubs live in `scripts/smoke_api.sh`.

## Tool workflows (intake → process → output)
- **Research**: normalize_intake → classify_matter → jurisdiction_and_area_classifier → fact_extractor → conflict_check → issue_generator → research_plan_builder → run_next_search_step (loop) → synthesize_briefing (IRAC/strategy/next_steps).
- **Summary**: normalize_intake → classify_matter → fact_extractor → synthesize_briefing (summary-focused).
- **Drafting**: intake validation → normalize_intake → classify_matter → fact_extractor → issue_generator → synthesize_briefing → drafting stub (draft + sections + risks + assumptions + open questions). Stream/persist/resume supported.
- **Review**: intake validation → normalize_intake → classify_matter → fact_extractor → conflict_check → structural_review (severity + location/section) → detailed_review (categorized issues with severity/location) → prioritize_issues (80/20 weighting) → revision_suggestions (redline-style) → qa_pass → summarize_review. Stream/persist/resume supported.

## Synthetic evals
- Scenarios live in `apps/agent/research_graph.py` (`SYNTHETIC_EVAL_SCENARIOS`) with helper `run_synthetic_eval(runner)`; pass a stubbed runner in tests to avoid network/tool calls.
- Conflict lookup: conflict_check now queries vector hits on opposing parties (distance threshold 0.3, top 3) and enriches with web lookup links.
- Research run/stream responses persist and return a `conflict_check` block so the UI can surface conflicts and runs can be resumed/audited.
- Streaming/resume: `/research/run/stream` emits start/update/done/error and persists snapshots on start and each update. Frontend falls back to polling and non-stream run on errors. Errors include `trace_id` for support.
- Smoke/eval: `scripts/smoke_api.sh` now runs an offline-safe synthetic eval stub; useful for CI without network or tools.
- Keepalive: streaming emits periodic `keepalive` events to keep proxies from timing out during long searches.

## Drafting agent intake (schema-first)
- Endpoint `/draft` accepts: `doc_type`, `objective`, `audience`, `tone`, `language`, `context`, `facts[]`, `requirements[{label,value}]`, `research_trace_id?`, `research_summary?`, `constraints[]`.
- Output: `draft` (text) + `sections[]`, `assumptions`, `open_questions`, `risks`. This schema drives the drafting UI (doc type selector, requirements list, research trace picker).

## Review agent intake (schema-first)
- Endpoint `/review` accepts: `doc_type`, `objective`, `audience`, `guidelines`, `jurisdiction`, `constraints[]`, `text`, `sections[{title,content}]`, `research_trace_id?`, `research_summary?`.
- Output: `structural_findings[]` (severity/location), `issues[]` (categorized, severity, location, priority), `suggestions[]` (redline-style), `qa_notes[]`, `residual_risks[]`, `summary`, `conflict_check`, `trace_id/status`. Streaming + persistence mirror the research/draft flows.
