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
- GRE-29 Search interface UI — Local: In progress (dashboard tool selector now has búsqueda/Q&A form hitting /qa, shows respuesta y citas; dedicated results UI still to polish) / Linear: Todo.
- GRE-30 Upload document UI — Local: In progress (UI placeholder en dashboard; no backend wiring) / Linear: Todo.
- GRE-31 Define summarization templates — Local: Not started / Linear: Todo.
- GRE-32 Summarization API — Local: Not started / Linear: Todo.
- GRE-33 Multi-document summarizer — Local: Not started / Linear: Todo.
- GRE-34 Summary UI page — Local: In progress (summary placeholder UI en dashboard; awaiting /summary backend) / Linear: Todo.
- Marketing shell (landing + pricing + login) — Local: Done (App Router, shared header, Spanish copy) / Linear: n/a.
- GRE-45/46/47 (Dockerize backend/frontend, dev DB), GRE-44 env vars — Local: Partially covered by root compose and `.env.example`, but not fully per issue scope / Linear: Backlog/Todo.
- GRE-50 End-to-end smoke test, GRE-49 test plan, GRE-48 API docs — Local: Not started / Linear: Backlog.

Next immediate actions (keep Local + Linear aligned):
1) GRE-51: polish search UI (results view, pagination, filters; clean separation search/QA).
   - TODO: /search requiere un vector de consulta; frontend no embebe. Extender backend para aceptar `query` y embebecer server-side (o endpoint de embedding) y conectar modo Search ahí; hoy usa /qa como placeholder.
2) GRE-52: wire upload UI to ingestion endpoint with progress + statuses.
3) GRE-53: connect summary UI to /summary with citations rendering.
4) GRE-44/45/46/47: finish env var doc + Dockerfiles/runbook to match current compose.
5) GRE-48/49/50: draft API docs, test plan, and a basic end-to-end smoke test once ingestion/frontends are underway.
