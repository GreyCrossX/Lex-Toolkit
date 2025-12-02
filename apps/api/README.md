# API Service

FastAPI service with a semantic search endpoint backed by pgvector.

## Run (Docker Compose)
From repo root:
```bash
docker compose --profile api up --build
```
`DATABASE_URL` is provided by `docker-compose.yml`. Ensure pgvector is up (`docker compose up -d pgvector`).

## Endpoints
- `GET /health` – liveness probe.
- `POST /search` – vector similarity search over `legal_chunks`.
- `POST /qa` – retrieval + answer with citations (uses OpenAI if configured, otherwise offline stub).

### Search request body
```json
{
  "embedding": [0.1, 0.2, ...],   // length must match DB dimension (default 1536)
  "limit": 5,
  "doc_ids": ["doc123"],
  "jurisdictions": ["cdmx"],
  "sections": ["article"],
  "max_distance": 1.2
}
```

### QA request body
```json
{
  "query": "¿Qué dice el artículo 5?",
  "top_k": 5,
  "doc_ids": ["doc123"],
  "jurisdictions": ["cdmx"],
  "sections": ["article"],
  "max_distance": 1.2,
  "max_tokens": 400
}
```

### QA response
```json
{
  "answer": "…",
  "citations": [
    {
      "chunk_id": "chunk-1",
      "doc_id": "doc123",
      "section": "article",
      "jurisdiction": "cdmx",
      "metadata": {},
      "content": "...",
      "distance": 0.42
    }
  ]
}
```

Notes:
- Embeddings in `/qa` are computed with OpenAI `text-embedding-3-small` when `OPENAI_API_KEY` is set. Without it, `/qa` falls back to an offline stub answer using retrieved snippets.

### Response shape
```json
{
  "results": [
    {
      "chunk_id": "chunk-1",
      "doc_id": "doc123",
      "section": "article",
      "jurisdiction": "cdmx",
      "metadata": {},
      "content": "...",
      "distance": 0.42
    }
  ]
}
```
