# Docker Infrastructure

Postgres + pgvector init scripts live here. Use the root-level `docker-compose.yml` to run services:

```bash
cd ..
docker compose up -d pgvector
```

The init SQL in this directory enables pgvector and creates indexed `legal_chunks` sized for 1536-dim embeddings (text-embedding-3-small), using HNSW. Adjust the dimension in `init/001_enable_pgvector.sql` if needed and recreate the volume.

## Quick start
1) Copy env defaults and edit secrets if needed:
```bash
cd infra/docker
cp .env.example .env  # edit POSTGRES_PASSWORD if desired
```
2) Start Postgres with pgvector:
```bash
docker compose up -d
```
The `init/001_enable_pgvector.sql` script enables the extension, creates a `legal_chunks` table sized for `text-embedding-3-large` (3072 dims), and builds btree/GIN/IVFFlat indexes. Adjust the `dim` in that file if you use a different embedding model.

## Sanity query
Once running, connect and run a vector search (replace the sample vector with one from your export):
```bash
psql postgresql://vector:vectorpass@localhost:5432/legalscraper
SELECT chunk_id, doc_id, section, embedding <-> '[0,0,0]'::vector AS distance
FROM legal_chunks
ORDER BY embedding <-> '[0,0,0]'::vector
LIMIT 5;
```

## Importing embeddings
- Export embeddings from `embed_chunks.py` with `--export-jsonl data/embeddings_export.jsonl`.
- Load into Postgres (example using `psql` + `jq`):
```bash
cat data/embeddings_export.jsonl | \
  jq -r '[.chunk_id,.doc_id,.section,(.metadata|tojson),(.embedding|tojson)] | @tsv' | \
  psql postgresql://vector:vectorpass@localhost:5432/legalscraper \
    -c "COPY legal_chunks (chunk_id, doc_id, section, metadata, embedding) FROM STDIN"
```
  - Adjust fields if you include `jurisdiction`, `tokenizer_model`, or `content` in your export.
  - Rebuild the IVFFlat index after bulk loads if rows changed significantly:
```bash
psql postgresql://vector:vectorpass@localhost:5432/legalscraper \
  -c "REINDEX INDEX CONCURRENTLY idx_legal_chunks_embedding;"
```
