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
- GRE-29 Search interface UI — Local: Not started / Linear: Todo.
- GRE-30 Upload document UI — Local: Not started / Linear: Todo.
- GRE-31 Define summarization templates — Local: Not started / Linear: Todo.
- GRE-32 Summarization API — Local: Not started / Linear: Todo.
- GRE-33 Multi-document summarizer — Local: Not started / Linear: Todo.
- GRE-34 Summary UI page — Local: Not started / Linear: Todo.
- GRE-45/46/47 (Dockerize backend/frontend, dev DB), GRE-44 env vars — Local: Partially covered by root compose and `.env.example`, but not fully per issue scope / Linear: Backlog/Todo.
- GRE-50 End-to-end smoke test, GRE-49 test plan, GRE-48 API docs — Local: Not started / Linear: Backlog.

Next immediate actions (keep Local + Linear aligned):
1) GRE-29/30/34: define minimal frontend scope (search + upload + summary UX) now that APIs exist; stub UI tasks.
2) GRE-44/45/46/47: finish env var doc + Dockerfiles/runbook to match current compose.
3) GRE-48/49/50: draft API docs, test plan, and a basic end-to-end smoke test once ingestion/frontends are underway.
