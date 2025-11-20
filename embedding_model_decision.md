# Embedding model decision (GRE-24)

## Default choice
- **Primary:** OpenAI `text-embedding-3-large` (3072 dims) for best quality on multilingual/legal text.
- **Cost:** ~$0.13 per 1M input tokens (input-only pricing).
- **Why:** Strong multilingual performance, higher dimensionality aids recall on long legal spans, and minimal engineering lift with existing `embed_chunks.py` OpenAI backend.

## Fallback / offline
- **Fallback:** `intfloat/multilingual-e5-base` via SentenceTransformers (768 dims, normalized).
- **Why:** Good Spanish performance, runs on local GPU/CPU, already wired into `embed_chunks.py`.
- **Prefix:** Keep `passage: ` (default) for E5.

## How to run embedding (recommended)
```bash
# OpenAI default (primary)
OPENAI_API_KEY=... \
pipenv run python -m services.data_pipeline.embed_chunks \
  --backend openai \
  --embedding-model text-embedding-3-large \
  --chunks-dir data/chunks \
  --output-db data/legal_chunks.db \
  --batch-size 64

# Fallback local (no network)
pipenv run python -m services.data_pipeline.embed_chunks \
  --backend local \
  --local-model intfloat/multilingual-e5-base \
  --local-device cuda \
  --chunks-dir data/chunks \
  --output-db data/legal_chunks.db \
  --batch-size 32
```

## Notes
- Keep token ids off by default; embeddings use chunk text and metadata.
- For vector DB load: consider exporting embeddings to pgvector/Qdrant instead of SQLite when GRE-26 begins.
- If cost is sensitive and quality acceptable, `text-embedding-3-small` (1536 dims, ~$0.02 per 1M tokens) is a viable low-cost alternative; stick to `-3-large` for recall-critical legal QA.
