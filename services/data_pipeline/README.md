# Data Pipeline Service

Home for ingestion, normalization, and chunking scripts. Existing scrapers and RAG prep utilities live here until they evolve into a package or microservice.

## Setup

```bash
cd services/data_pipeline
pipenv install
```

The Pipenv environment now includes `sentence-transformers`, so you can run local embedding jobs (e.g., `intfloat/multilingual-e5-base`) directly on your GPU.

## Embedding chunks locally

1. Generate chunks with `build_chunks.py` (already run across the corpus):
   ```bash
   pipenv run python -m services.data_pipeline.build_chunks \
     --tokenizer-model gpt-4o-mini \
     --max-tokens 320 \
     --overlap-tokens 60
   ```
2. Encode them with the local embedder (defaults shown):
   ```bash
   pipenv run python -m services.data_pipeline.embed_chunks \
     --backend local \
     --local-model intfloat/multilingual-e5-base \
     --local-device cuda
   ```
   - Pass `--batch-size` to control how many chunks are embedded per step.
   - Use `--dry-run` to validate chunk discovery without generating embeddings.

The resulting vectors are stored in `data/legal_chunks.db`, ready for pgvector import or direct querying.

## Tokenizing chunks for OpenAI models

Use `tokenize_chunks.py` to attach token counts (and optionally raw token ids) using `tiktoken` so downstream OpenAI agents can enforce context windows:

```bash
pipenv run python -m services.data_pipeline.tokenize_chunks \
  --model gpt-4o-mini \
  --chunks-dir data/chunks \
  --output-dir data/tokenized_chunks \
  --batch-size 512 \
  --threads 4 \
  # --validate-decode  # optional sanity check: ensures decoded text matches input

# Optional (debug): include raw token ids and store sidecar .npz for compact storage
# pipenv run python -m services.data_pipeline.tokenize_chunks \
#   --include-token-ids \
#   --save-token-ids-npy \
#   --chunks-dir data/chunks \
#   --output-dir data/tokenized_chunks
```
