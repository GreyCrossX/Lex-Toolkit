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
