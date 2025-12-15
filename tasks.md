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
4) Review/Critique agent: ship MVP (intake → structural → detailed → prioritize → redline suggestions → QA → summary).

Review Agent MVP checklist (intake → process → output):
- [ ] Intake schema enforced: doc_type, objective, audience, guidelines/style, jurisdiction, constraints, text/sections, research_trace_id?, research_summary? (API + UI).
- [ ] Conflict check before review; surface conflict_check in response.
- [ ] Structural review: detect missing/duplicated sections and flow issues; return structural_findings with severity.
- [ ] Detailed review: categorize issues (accuracy/legal, clarity/style, consistency/refs/defs, formatting), with severity and location/section.
- [ ] Prioritization: apply 80/20; ranked issue list with suggested fix approach.
- [ ] Revision suggestions: redline-style suggestions per issue/section; use TODO when info missing; no silent edits.
- [ ] QA pass: final checks on revised text; residual risks/assumptions noted.
- [ ] Outputs: critique summary per category, issues with severity and fixes, redline suggestions, QA notes, residual risks, trace_id/status.
- [ ] Streaming & traceability: `/review/run` + `/review/run/stream` emit start/update/done/error; include trace_id/user_id/firm_id; persist for resume.
- [ ] Frontend: review form (doc_type, objective, audience, guidelines, constraints, text/sections, research trace), stream display (findings/issues/suggestions/risks), resume by trace_id, health dot.
- [ ] Docs/DX: workflow and endpoints documented; smoke stub for review added to scripts; basic API test.

Implementation route:
- Backend: add review graph nodes (ingest → conflict_check → structural_review → detailed_review → prioritize → revision_suggestions → qa_pass → summary); schemas for ReviewRequest/ReviewResponse; endpoints `/review/run`, `/review/{trace_id}`, `/review/run/stream`; persistence table; health endpoint.
- Frontend: add review client, form, stream/resume UI, and health wiring in sidebar.
- DX/tests: smoke script stub hitting `/review/run`; lightweight API test with stubbed runner; update docs/agent_workflow.md.

Next tasks for “Intake schema enforced”:
1) Backend schema & endpoints: add ReviewRequest/Response models covering doc_type/objective/audience/guidelines/jurisdiction/constraints/text/sections/research_trace_id/research_summary; add `/review/run`, `/review/{trace_id}`, `/review/run/stream`, and persistence table with health probe.
2) Review graph ingest: add review graph ingest node to normalize intake, classify, run conflict_check, and pass structured text/sections onward (structural/detailed nodes can initially be stubs).
3) Frontend intake UI: add review client + dashboard form for all intake fields (doc_type, objective, audience, guidelines, constraints, text/sections, research trace/summary) with resume by trace_id and health indicator.
