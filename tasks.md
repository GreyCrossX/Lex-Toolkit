# Task Tracker (Linear-sync)
Statuses shown as Local / Linear.

- GRE-21 Define initial data sources — Local: Done / Linear: Done.
- GRE-22 Build PDF/text ingestion pipeline — Local: Done (full corpus re-chunked, embeddings regenerated, loaded to pgvector) / Linear: Done.
- GRE-23 Implement chunking strategy — Local: Done / Linear: Done.
- GRE-24 Choose embedding model — Local: Done (`embedding_model_decision.md`) / Linear: Done.
- GRE-25 Embedding pipeline implementation — Local: Done (`services/data_pipeline/embed_chunks.py`) / Linear: Done.
- GRE-26 Set up vector database — Local: Done (pgvector via root compose, 1536-dim HNSW) / Linear: Done.
- GRE-27 Semantic search API — Local: Done (`apps/api` /search) / Linear: Done.
- GRE-28 Q&A API with citations — Local: Done (`apps/api` /qa uses OpenAI, returns citations) / Linear: Done.
- GRE-29 Search interface UI — Local: In review (dashboard search/QA form hits `/search` and `/qa`, filters/pagination/sorting + Vitest coverage; search mode now expects `results` payload from `/search`) / Linear: In Progress (was Todo).
- GRE-30 Upload document UI — Local: In progress (dashboard upload calls `/ingestion/{doc_type}`, doc_type selector, shows filename/status) / Linear: In Progress (was Todo).
- GRE-31 Define summarization templates — Local: Not started / Linear: Todo.
- GRE-32 Summarization API — Local: Not started / Linear: Todo.
- GRE-33 Multi-document summarizer — Local: Not started / Linear: Todo.
- GRE-34 Summary UI page — Local: In progress (dashboard summary UI calls `/summary`, renders citations, placeholder fallback) / Linear: In Progress (was Todo).
- GRE-51 Polish search UI — Local: Done (QA/search toggle, filters, pagination, distance sorting, Vitest; `/search` endpoint reflected in UI) / Linear: In Progress (was Backlog).
- GRE-52 Wire upload UI to ingestion — Local: Done (backend ingestion live with `/upload` + `/ingestion/{doc_type}`, status polling via `ingestion_jobs`, doc_type-specific chunking/metadata/timeouts) / Linear: In Progress (was Backlog).
- GRE-53 Connect summary UI to /summary — Local: In progress (frontend wired; needs backend responses and streaming support) / Linear: In Progress (was Backlog).
- Marketing shell (landing + pricing + login) — Local: Done (App Router, shared header, Spanish copy) / Linear: n/a.
- GRE-45/46/47 (Dockerize backend/frontend, dev DB), GRE-44 env vars — Local: Partially covered by root compose and `.env.example`, but not fully per issue scope / Linear: Backlog/Todo.
- GRE-50 End-to-end smoke test, GRE-49 test plan, GRE-48 API docs — Local: Not started / Linear: Backlog.
- Auth hardening & frontend cookie flow — Local: Done (login/register/refresh/logout/me wired with HttpOnly refresh cookies + CSRF double-submit token on refresh, dashboard middleware guard, authFetch 401 retry) with follow-up backlog for key rotation (RS256+KID), stricter rate limits, and audit logging / Linear: In Progress (RS256/JWKS + audit still pending).
- Dashboard UX: create per-tool views (chat input variations + tailored UI states) so each tool has a dedicated interaction model.

Next immediate actions (keep Local + Linear aligned):
1) Summarization: define templates + implement `/summary` (single/multi) so the dashboard UI can render real summaries/citations (GRE-31/32/33/53/34).
2) Ingestion hardening: doc_type selectors + chunking/metadata/timeouts added; extend specialized parsers per `doc_type` (jurisprudence/contract/policy) and richer metadata; keep timeouts small. Extend dashboard upload UX as needed (GRE-30/52).
3) Docs/QA/infra: finalize API docs + test plan + smoke test, and finish env/Docker coverage to match compose (GRE-48/49/50/44/45/46/47). Keep auth key-rotation/audit follow-ups tracked in Linear.
4) Drafting agent: ship MVP (intake → plan → draft → self-check) with schema-driven frontend/API.

Drafting Agent MVP checklist (intake → process → output):
- [x] Intake schema enforced end-to-end: doc_type, objective, audience, tone, language, context, facts[], requirements[{label,value}], constraints[], research_trace_id?, research_summary? (validated in API, wired in UI form).
- [x] Conflict check runs before drafting; blocks on hits and surfaces conflict_check in response.
- [x] Planning: template/section planner maps doc_type + requirements/constraints to sections/clauses; flags missing info/open questions.
- [x] Drafting: section-by-section generation honoring tone/constraints; inserts TODOs instead of fabricating when facts missing; can ground on research_trace briefing when provided.
- [x] Self-review: checklist for completeness (all planned sections), requirement coverage, risk flags, assumptions/open_questions surfaced; status/deliverables streamed to UI.
- [x] Streaming & traceability: `/draft/run` and `/draft/run/stream` emit start/update/done/error; traces include trace_id/user_id/firm_id; errors surface trace_id.
- [x] Frontend: drafting tool UI captures intake fields, shows plan/sections/risks/open questions, supports resume via trace_id.
- [x] Docs/DX: workflow documented (intake → plan → draft → review), endpoint(s) documented, and smoke/eval stub for drafting added to scripts.

Implementation route:
- Extend API schemas (done) and add drafting graph with nodes: normalize_intake → classify_matter → fact_extractor → conflict_check → issue_generator (light) → template_selector → section_planner → draft_builder → draft_reviewer. ✅ graph stubbed.
- Add `/draft/stream` (parallel to research stream) and persistence of drafts/runs; log with trace_id/user_id/firm_id. ✅ implemented.
- Frontend: add Drafting form (doc_type selector, objective, audience, tone, constraints, facts list, requirements list, research_trace picker) and render plan/sections/risks in the dashboard. ✅ done.
- Add docs entry in `docs/agent_workflow.md` and a smoke stub in `scripts/smoke_api.sh` for CI (offline-safe). ✅ done.
