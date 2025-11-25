# Task Tracker (Linear-sync)
Statuses shown as Local / Linear.

- GRE-21 Define initial data sources — Local: Done / Linear: Done.
- GRE-22 Build PDF/text ingestion pipeline — Local: In Review (ingestion scripts exist; needs finalization) / Linear: In Review.
- GRE-23 Implement chunking strategy — Local: Done / Linear: Done.
- GRE-24 Choose embedding model — Local: Done (`embedding_model_decision.md`) / Linear: Done.
- GRE-25 Embedding pipeline implementation — Local: Done (`services/data_pipeline/embed_chunks.py`) / Linear: Done.
- GRE-26 Set up vector database — Local: Done (pgvector via root compose, 1536-dim HNSW) / Linear: Todo (needs status update).
- GRE-27 Semantic search API — Local: Done (`apps/api` /search) / Linear: Todo (needs status update).
- GRE-28 Q&A API with citations — Local: Not started / Linear: Todo.
- GRE-29 Search interface UI — Local: Not started / Linear: Todo.
- GRE-30 Upload document UI — Local: Not started / Linear: Todo.
- GRE-31 Define summarization templates — Local: Not started / Linear: Todo.
- GRE-32 Summarization API — Local: Not started / Linear: Todo.
- GRE-33 Multi-document summarizer — Local: Not started / Linear: Todo.
- GRE-34 Summary UI page — Local: Not started / Linear: Todo.
- GRE-45/46/47 (Dockerize backend/frontend, dev DB), GRE-44 env vars — Local: Partially covered by root compose and `.env.example`, but not fully per issue scope / Linear: Backlog/Todo.
- GRE-50 End-to-end smoke test, GRE-49 test plan, GRE-48 API docs — Local: Not started / Linear: Backlog.

Next immediate actions (keep Local + Linear aligned):
1) Update Linear statuses for GRE-26 and GRE-27 to Done when ready to report.
2) Start GRE-28 (Q&A API) using existing `/search` as retrieval.
3) Decide on frontend scope for GRE-29/30 to unblock upload/search UI.
