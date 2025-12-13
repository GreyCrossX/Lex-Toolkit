# Next Steps Plan (based on Linear)

Context: Chunking/embeddings/pgvector are done (GRE-22/23/24/25/26). Search + QA APIs are live, and the dashboard now hits `/search` + `/qa` with filters/pagination. Upload runs through Celery and is working. Auth is live (access + rotated refresh tokens) on the backend; frontend wiring is pending. Summary endpoints are live. Research agent scaffold (LangGraph) added with structured outputs + tool registry (pgvector_inspector, web_browser).

## Proposed order of execution (current)
- Summaries (GRE-31/32/33/53/34): DONE — `/summary/document` + `/summary/multi` with citations + streaming; frontend wired with dropzone.
- Ingestion hardening (GRE-52/30): keep `/upload` + `/ingestion/{doc_type}` routes, add specialized parsers (jurisprudence/contract/policy) and richer metadata as we add new doc types.
- Docs/QA/infra (GRE-48/49/50/44/45/46/47): API docs + test plan + e2e smoke, plus Dockerfiles/env coverage to match compose.
- Agent/Toolbox reshape: tools menu mapped to daily lawyer flows (research, summary, drafting, communication, upload/organize, review, transcribe, compliance, tasks); backend stubs under `/tools/*` and health pings for summary/tools.
- Research agent: LangGraph graph in `apps/agent/research_graph.py` (intake → qualify → classify → facts → issues → plan → search loop → briefing) with structured outputs and tenant-aware tools (`pgvector_inspector`, `web_browser`).

## Immediate next steps (actionable)
1) Extend ingestion (GRE-52/30): doc_type selectors + chunking/timeouts landed; add richer parsers/metadata for jurisprudence/contract/policy and keep Celery worker routing tight.
2) Auth frontend wiring: DONE — `/api/auth/*` proxy handlers with HttpOnly refresh cookie, CSRF double-submit token on refresh, access token in memory, dashboard middleware guard, and authFetch 401 retry. Follow-ups (new Linear items): key rotation (RS256+KID), stricter rate limits, and audit logging.
3) Research agent hardening: swap Pydantic v2 validators/ConfigDict, add observability/tracing around nodes + tool calls, add few-shot prompts, and build synthetic evals for structured outputs/citations.
4) Update docs + QA (GRE-48/49/50): refresh API docs to include auth/refresh, research agent/tooling summary, and formalize test plan (incl. auth flows and agent smoke).
5) Close infra gaps (GRE-44/45/46/47): ensure `.env.example` is accurate, add Dockerfiles for api/web, and a runbook for compose + migrations/pgvector init.
