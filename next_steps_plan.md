# Next Steps Plan (based on Linear)

Context: Chunking/tokenization validated and marked Done (GRE-23). Remaining critical path is retrieving, embedding, search, and QA APIs.

## Proposed order of execution
- Embedding model decision (GRE-24): choose default embedder for RAG (OpenAI vs local, e.g., mxbai-e5). Output: model choice, dims, cost envelope.
- Embedding pipeline (GRE-25): wire `embed_chunks` with chosen model; produce vectors DB-ready.
- Vector database setup (GRE-26): stand up pgvector/Qdrant/Chroma; define schema (chunk_id, doc_id, metadata, embedding, tokenizer_model).
- Semantic search API (GRE-27): `/api/search` over the vector DB with filters; return metadata + chunk text.
- Q&A API with citations (GRE-28): retrieval-augmented generation using search results; stream answer + citations.
- Ingestion pipeline review (GRE-22): finish review/merge; ensure normalized docs feed chunker.
- Frontend (GRE-29/30/34): search UI, upload UI, summary UI after backend endpoints stabilize.
- Summarization (GRE-31/32/33): templates, single/multi-doc summarizer after search/Q&A are working.

## Immediate next steps (actionable)
1) GRE-24: Decide embedder
   - Compare: OpenAI text-embedding-3-large/small vs local intfloat/multilingual-e5-base or mxbai-large.
   - Criteria: quality on Spanish/Legal, cost per 1M tokens, latency, context dimension.
   - Deliverable: pick default + fallback; document env vars.
2) GRE-25: Hook embedder into `embed_chunks.py`
   - Parameterize backend (openai/local) and batch size; emit vectors + metadata to SQLite/pgvector loadable format.
   - Add validation: sample similarity search vs manual query.
3) GRE-26: Vector DB setup
   - Choose pgvector (if Postgres available) or Qdrant (managed/local).
   - Define schema/index; load embeddings from step 2; basic health check query.
4) GRE-27: Semantic search API
   - Endpoint contract (filters: jurisdiction, doc_id, section; limit/offset; score).
   - Implement query → vector search → return scored chunks + metadata.
5) GRE-28: Q&A API with citations
   - Use search results → prompt template → LLM answer; return citations (chunk_id/doc_id) and token usage.

## Notes
- Token ids stay disabled by default; counts only (decision logged on GRE-23 comment).
- Use `--validate-decode` only for sampling; production runs can omit for speed.
