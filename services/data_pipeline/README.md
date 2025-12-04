# Data Pipeline Service

Home for ingestion, normalization, and chunking scripts. Existing scrapers and RAG prep utilities live here until they evolve into a package or microservice.

## Setup

Install deps from the repo root (single uv environment):
```bash
uv sync
```

The environment includes `sentence-transformers`, so you can run local embedding jobs (e.g., `intfloat/multilingual-e5-base`) directly on your GPU.

## Embedding chunks locally

1. Generate chunks with `build_chunks.py` (already run across the corpus):
   ```bash
   uv run python -m services.data_pipeline.build_chunks \
     --tokenizer-model gpt-4o-mini \
     --max-tokens 320 \
     --overlap-tokens 60
   ```
2. Encode them with the local embedder (defaults shown):
   ```bash
   uv run python -m services.data_pipeline.embed_chunks \
     --backend local \
     --local-model intfloat/multilingual-e5-base \
     --local-device cuda
   ```
   - Pass `--batch-size` to control how many chunks are embedded per step.
   - Use `--dry-run` to validate chunk discovery without generating embeddings.

The resulting vectors are stored in `data/legal_chunks.db`, ready for pgvector import or direct querying.

## Embedding chunks (OpenAI or local) and exporting for vector DBs

OpenAI (default choice):
```bash
OPENAI_API_KEY=... \
uv run python -m services.data_pipeline.embed_chunks \
  --backend openai \
  --embedding-model text-embedding-3-large \
  --chunks-dir data/chunks \
  --output-db data/legal_chunks.db \
  --batch-size 64 \
  --export-jsonl data/embeddings_export.jsonl \
  --export-limit 100000  # optional
  # --validate-query "amparo fiscal" --validate-limit 200 --validate-topk 5
```

Local (offline fallback):
```bash
uv run python -m services.data_pipeline.embed_chunks \
  --backend local \
  --local-model intfloat/multilingual-e5-base \
  --local-device cuda \
  --chunks-dir data/chunks \
  --output-db data/legal_chunks.db \
  --batch-size 32 \
  --export-jsonl data/embeddings_export.jsonl
```

- `--export-jsonl` writes per-chunk embedding rows (chunk_id, doc_id, metadata, tokenizer_model, embedding) for pgvector/Qdrant loading.
- `--validate-query` runs a small in-memory cosine search over stored embeddings to sanity-check quality.

## Tokenizing chunks for OpenAI models

Use `tokenize_chunks.py` to attach token counts (and optionally raw token ids) using `tiktoken` so downstream OpenAI agents can enforce context windows:

```bash
uv run python -m services.data_pipeline.tokenize_chunks \
  --model gpt-4o-mini \
  --chunks-dir data/chunks \
  --output-dir data/tokenized_chunks \
  --batch-size 512 \
  --threads 4 \
  # --validate-decode  # optional sanity check: ensures decoded text matches input

# Optional (debug): include raw token ids and store sidecar .npz for compact storage
# uv run python -m services.data_pipeline.tokenize_chunks \
#   --include-token-ids \
#   --save-token-ids-npy \
#   --chunks-dir data/chunks \
#   --output-dir data/tokenized_chunks
```
