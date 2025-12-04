# API Service

FastAPI service with a semantic search endpoint backed by pgvector.

## Run (Docker Compose)
From repo root:
```bash
docker compose --profile api up --build -d pgvector redis api worker
```
`DATABASE_URL` is provided by `docker-compose.yml`. Ensure pgvector is up (`docker compose up -d pgvector`).

## Layout (clean architecture)
- `app/core/domain`: domain entities (`User`, `IngestionJob`).
- `app/application`: use-cases/services (search + ingestion orchestration).
- `app/infrastructure`: db connection + repositories, pdfplumber ingestion pipeline, LLM client, auth hashing/JWT, Celery wiring.
- `app/interfaces/api`: FastAPI schemas + routers.
- `app/interfaces/worker`: Celery tasks (ingestion worker).
- `app/main.py`: entrypoint that wires routers and ensures DB tables exist on startup.

## Endpoints (most currently unauthenticated; tighten as we roll out frontend auth)
- `GET /health` – liveness probe.
- `GET /auth/health` – auth liveness.
- `POST /search` – vector similarity search over `legal_chunks`.
- `POST /qa` – retrieval + answer with citations (uses OpenAI if configured, otherwise offline stub).
- `POST /summary/document` – summarize a single text or scoped doc_ids; supports NDJSON streaming when `stream=true`.
- `POST /summary/multi` – summarize multiple texts/doc_ids into one narrative; supports NDJSON streaming when `stream=true`.
- `POST /upload` – ingests a PDF as statute/regulation (legacy default), enqueues job, returns `job_id`.
- `POST /ingestion/{doc_type}` – ingests a PDF for a specific doc_type (`statute`, `jurisprudence`, `contract`, `policy`), enqueues job, returns `job_id`.
- `GET /upload/{job_id}` – polls ingestion status/progress for a specific job.
- `GET /ingestion/{job_id}` – same as `/upload/{job_id}`.
- `POST /auth/register` – create user (returns access + refresh tokens in body).
- `POST /auth/login` – login (returns access + refresh tokens in body).
- `POST /auth/refresh` – rotates refresh token (returns new access + refresh tokens).
- `POST /auth/logout` – revokes refresh token.
- `GET /auth/me` – returns current user (requires `Authorization: Bearer ...`).

Notes:
- Access token is short-lived and returned in the JSON body; refresh token is returned in the body and should be stored as an HttpOnly/Secure cookie at the frontend proxy layer.
- Auth is not yet enforced on search/qa/upload; add middleware/guards once the frontend stores tokens.

### Search request body
```json
{
  "query": "texto opcional si no envías embedding",
  "embedding": [0.1, 0.2, ...],   // length must match DB dimension (default 1536)
  "limit": 5,
  "doc_ids": ["doc123"],
  "jurisdictions": ["cdmx"],
  "sections": ["article"],
  "max_distance": 1.2
}
```

Notes:
- If `query` is provided, the API will embed it server-side (OpenAI `text-embedding-3-small`). Send `embedding` directly if you already have one.
- `max_distance` filters by L2 distance when provided.

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

### Summary (single)
`POST /summary/document` (alias `/summary`)
```json
{
  "text": "texto a resumir",
  "doc_ids": ["doc123"],      // optional grounding filter
  "top_k": 5,                 // retrieval budget
  "max_tokens": 400,          // summary length cap
  "stream": true              // NDJSON streaming when true
}
```

Response (non-stream):
```json
{
  "summary": "…",
  "citations": [
    { "chunk_id": "c1", "doc_id": "doc123", "section": "art", "jurisdiction": "mx", "metadata": {}, "content": "...", "distance": 0.12 }
  ],
  "model": "gpt-4o-mini",
  "chunks_used": 3
}
```

Streaming shape (`application/x-ndjson`):
```
{"type":"citation","data":{...}}
{"type":"summary_chunk","data":"texto parcial"}
{"type":"summary_chunk","data":"..."}
{"type":"done","data":{"model":"gpt-4o-mini","chunks_used":3}}
```
If no `OPENAI_API_KEY`, the service returns a deterministic stub summary and echoes context.

Quick smoke (non-stream):
```bash
curl -s -X POST http://localhost:8000/summary/document \
  -H "Content-Type: application/json" \
  -d '{"text": "texto a resumir", "doc_ids": ["doc123"], "top_k": 5, "max_tokens": 200}'
```

Quick smoke (streaming NDJSON):
```bash
curl -N -X POST http://localhost:8000/summary/document \
  -H "Content-Type: application/json" \
  -d '{"text": "texto a resumir", "stream": true, "top_k": 3, "max_tokens": 200}'
```

### Summary (multi)
`POST /summary/multi`
```json
{
  "texts": ["texto 1", "texto 2"],  // optional
  "doc_ids": ["doc123", "doc456"],  // optional
  "top_k": 5,
  "max_tokens": 400,
  "stream": true
}
```
Response/streaming shapes match single-summary.


### Upload contract
- `POST /upload` (multipart form): field `file` (PDF, max ~25MB). Returns `{ "job_id": "...", "status": "queued", "message": "..." }` with HTTP 202.
- `GET /upload/{job_id}`: returns `{ "job_id": "...", "filename": "...", "status": "uploading|processing|completed|failed", "progress": 0-100, "message": "...", "error": "...", "doc_ids": [] }`.
- Statuses (including `doc_type`) are persisted in Postgres table `ingestion_jobs`; files are saved under `data/uploads/{job_id}/`.
- Ingest runs asynchronously via Celery workers (Redis broker), parsing PDFs with pdfplumber and embedding a limited number of chunks to keep jobs fast. Set `OPENAI_API_KEY` for successful ingestion. Without it, uploads will fail with a clear error.

## Testing
- Unit/integration: `uv run pytest`
- Live pgvector smoke (requires seed + env): `RUN_PGVECTOR_TESTS=1 DATABASE_URL=... uv run pytest tests/e2e/test_pgvector_live.py`
- Quick smoke (health/search/qa/upload) from repo root: `API_BASE_URL=http://localhost:8000 bash scripts/smoke_api.sh` (`jq` optional; needs `sample.pdf` for upload). Ensure `redis` + `worker` containers are running so uploads complete.
