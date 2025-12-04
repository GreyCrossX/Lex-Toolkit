# Linear sync notes (Research agent + toolbox)

Use this to update Linear issues without re-deriving the context.

## Research Agent v1 (new issue)
- Added LangGraph research graph (`apps/agent/research_graph.py`) with structured nodes (intake → qualify → classify → facts → issues → plan → search loop → briefing) and status constants.
- Shared tool registry with `pgvector_inspector` (tenant-aware, filters, fallback) and `web_browser` (allowlist/timeouts), exposed via `get_tools()`.
- LLM client centralized in `apps/agent/llm.py` (OpenAI chat + structured output). Env: `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_EMBED_MODEL`.
- Minimal pytest coverage: `tests/test_research_graph.py` for query builder and tool integration.
- Next steps: migrate to Pydantic v2 validators/ConfigDict, add observability/tracing, add few-shot prompts and synthetic evals.

## Docs/Contracts Sync (new issue)
- Update `ARCHITECTURE.md` to reflect research graph/tooling and tool menu.
- Update root `README.md` (agent directory description) and `apps/agent/README.md` (usage, env vars, tools).
- `next_steps_plan.md` now includes summary DONE, agent scaffold, and toolbox reshape; keep it in sync.
- Pending: API docs mention `/tools/*` health, summary endpoints, and agent/tooling notes; add when convenient.

## Tech Debt / Follow-ups (new issue)
- Pydantic v2 migration: replace deprecated validators/config classes in tools + research graph.
- Observability: trace/log each node/tool call (redacting PII); add metrics for LLM/tool latency.
- Evaluation: add few-shot prompts + synthetic evals for structured outputs and citation quality; add more pytest coverage.
- Frontend alignment: per-tool views and health badges (already discussed), plus streaming UX polish.
