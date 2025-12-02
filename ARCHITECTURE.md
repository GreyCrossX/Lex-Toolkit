# Architecture & Scope Map

Source of truth for what we’re building, where it lives, and what’s done vs TBD. Mirrors the product/module outline.

## 0) Platform Overview (MVP)
- Multi-tenant, browser-based legal toolkit (MX law firms): Search/Q&A, Summaries, Drafting, Case Builder, Contract Analyzer, Personalization, Predictive.
- Tech: Next.js (TS) frontend, FastAPI backend, Postgres + pgvector, S3-compatible storage, hosted LLMs first (OpenAI/Anthropic), HF models for embeddings/NER. JWT auth, RBAC, TLS.
- Cross-cutting: tenant scoping (firm_id), audit logs, data lineage (citations), error monitoring (Sentry), Spanish/English UI.

## 1) Module: Search + Retrieval (current focus)
- Goal: fast, cited search/Q&A over public law + firm docs.
- Pipeline (services/data_pipeline):
  - Chunking/tokenization: `build_chunks.py`, `legal_chunker.py`, `tokenize_chunks.py` (validated; GRE-23 done). Chunk IDs include section + de-dupe suffix to guarantee uniqueness.
  - Embeddings: `embed_chunks.py` with OpenAI/local backends, JSONL export (GRE-24/25 done). Full corpus embedded with OpenAI `text-embedding-3-small` (1536 dims).
- Vector store:
  - pgvector via root `docker-compose.yml` + init SQL `infra/docker/init/001_enable_pgvector.sql` (1536 dims, HNSW) (GRE-26 done); loaded with 289,030 chunks (CDMX + Federal).
  - Table: `legal_chunks(chunk_id, doc_id, section, jurisdiction, tokenizer_model, metadata jsonb, content, embedding vector)`.
- API:
  - FastAPI service (`apps/api`), `/search` endpoint (GRE-27 done): filters (doc_ids, jurisdictions, sections, optional max_distance), returns scored chunks.
  - `/qa` endpoint (GRE-28 done): embeds query (OpenAI, handles nano/max_completion_tokens and standard max_tokens), retrieves via pgvector, returns answer + citations.
  - `/health` liveness.
  - DB pool/pgvector integration (`app/db.py`, `app/routers/search.py`, `app/routers/qa.py`, `app/schemas.py`).
- TODO for module completion: ingestion/upload endpoints, keyword search fallback, firm_id scoping, auth, audit logs, keep DB refreshed from exports, frontend search UI.

## 2) Module: Summarization + Distillation
- TBD. Planned APIs: `/summary/document`, `/summary/multi`, `/summary/selection`. Needs: long-context handling, prompt patterns, grounding + citations.

## 3) Module: Drafting Assistant (templates)
- TBD. Planned APIs: `/templates`, `/draft/generate`. Needs template storage, DOCX export, style options.

## 4) Module: Case Builder (structured extraction)
- TBD. Planned APIs: `/cases`, `/cases/{id}/extract`, etc. Needs NER/regex heuristics, case workspace model.

## 5) Module: Contract Analyzer
- TBD. Clause segmentation/classification, similarity search over clauses, risk heuristics.

## 6) Module: Personalization Engine
- TBD. Style profiles per user, optional persona prompting or style embeddings.

## 7) Module: Predictive Analytics
- TBD. Outcome/time/damages modeling; feature engineering and explainability.

## Infra & Ops
- Docker: root `docker-compose.yml` orchestrates pgvector, api, agent (placeholder), web (placeholder). Root `.env.example` carries Postgres defaults.
- Data: `data/` for normalized/chunks/embeddings exports; not versioned here.
- Agent: placeholder LangChain hello-world (`apps/agent/main.py`) to keep container alive.

## Decisions & Open Items
- Embedding dim currently 1536 (text-embedding-3-small). If using 3072, adjust init SQL and recreate volume or reduce dims before load.
- Need firm_id/tenant column in `legal_chunks` and all future tables; enforce in APIs.
- Security/auth not wired yet (JWT/RBAC planned).
- Logging/metrics/monitoring not wired; plan Sentry + basic request logging.
- Frontend palette (App Router, Nov 2025): background `#0d141f`, surface `#111a2c`, card `#16233a`, border `#1f2f4a`, contrast `#0a0f18`, foreground `#e8edf6`, muted `#a3b7d4`, accent `#d7b46a` (strong `#b58f3a`), success `#46c2ae`, danger `#f27c7c`. Fonts: Playfair Display (headings), Source Sans 3 (body). Applies to `apps/web`.
