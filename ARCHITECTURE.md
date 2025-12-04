# Architecture & Scope Map

Source of truth for what we’re building, where it lives, and what’s done vs TBD. Mirrors the product/module outline.

## Platform Overview
- Multi-tenant, browser-based legal toolkit (MX law firms) oriented around daily lawyer workflows: Research, Summary, Drafting, Communication, Upload/Organize, Review/Redlines, Transcribe, Compliance Check, Tasks/Reminders.
- Tech: Next.js (TS) frontend, FastAPI backend, Postgres + pgvector, S3-compatible storage, hosted LLMs first (OpenAI/Anthropic), HF models for embeddings/NER. JWT auth with refresh-cookie rotation (backend enforced), RBAC planned. Cross-cutting: tenant scoping (firm_id), audit/logs, citations, Spanish/English UI.

## Current Modules & Status
- Research: LangGraph agent scaffold live in `apps/agent/research_graph.py` with structured outputs per node, tenant-aware pgvector inspector + web browser tools, and fallback-safe prompts. Backend still exposes `/search` + `/qa`; frontend chat mode with filters drawer.
- Summary: `/summary/document` + `/summary/multi` with citations; streaming NDJSON supported. Frontend summary mode with dropzone.
- Upload/Organize: `/upload` + `/ingestion/{doc_type}` with Redis/Celery worker; status polling. Frontend dropzone with progress.
- Drafting/Communication/Review/Transcribe/Compliance/Tasks: placeholders wired with stub endpoints under `/tools/*` (draft, comms/email, review/contract, transcribe, compliance/check, tasks CRUD) to align frontend menu; real logic TBD.

## Planned Tool-Specific Behaviors (LangGraph-ready)
- ResearchState: messages, intake, qualification, jurisdiction_hypotheses, chosen_jurisdictions, area_of_law, facts, issues, research_plan (loop), queries, briefing, status/error; uses shared tools (`pgvector_inspector`, `web_browser`).
- SummaryState: messages, text/doc_ids, top_k, max_tokens, summary, citations.
- DraftingState: messages, template_id, facts, tone, clauses, draft.
- CommunicationState: messages, intent (email/note/whatsapp), audience, tone, content.
- UploadState: messages, file_refs, doc_type, tags, matter_id, job_id, progress, status.
- ReviewState: messages, contract_text, playbook_id, findings, suggestions.
- TranscribeState: messages, audio_ref, transcript, summary, action_items.
- ComplianceState: messages, policy_id, text/doc_refs, findings, recommendations.
- TasksState: messages, task, tasks list.

## Infra & Ops
- Docker: root `docker-compose.yml` orchestrates pgvector, Redis, api, Celery worker, placeholder web. `.env.example` carries Postgres defaults.
- Data: `data/` for normalized/chunks/embeddings exports; not versioned here.
- Agent: LangGraph space (`apps/agent/`), with research graph + shared tool registry.

## Decisions & Open Items
- Embeddings: current DB dim 1536 (`text-embedding-3-small`). If moving to 3072, adjust init SQL and recreate volume or reduce dims.
- Tenant scoping: add firm_id/tenant to `legal_chunks` and future tables; enforce in APIs.
- Auth: backend enforces JWT + refresh rotation; frontend still needs HttpOnly flow and 401 retry. Pending: CSRF for refresh, key rotation (RS256+KID), RBAC, audit/logging.
- Observability: add Sentry/basic request logging.
- Frontend palette: background `#0d141f`, surface `#111a2c`, card `#16233a`, border `#1f2f4a`, contrast `#0a0f18`, foreground `#e8edf6`, muted `#a3b7d4`, accent `#d7b46a` (strong `#b58f3a`), success `#46c2ae`, danger `#f27c7c`. Fonts: Playfair Display (headings), Source Sans 3 (body).
