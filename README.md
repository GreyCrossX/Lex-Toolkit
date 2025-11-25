# Legal Scraper Monorepo

This repository is structured as a monorepo so we can add a Next.js frontend, FastAPI backend, LangGraph agents, and infrastructure side-by-side with the existing data pipeline.

## Directory layout

- `apps/web` – placeholder for the Next.js frontend.
- `apps/api` – placeholder for the FastAPI backend.
- `apps/agent` – reserved for LangGraph agent flows and tooling.
- `services/data_pipeline` – all ingestion, normalization, and chunk/embedding code plus its Pipenv environment and configs.
- `data` – shared datasets (raw, normalized, chunks, etc.).
- `infra/docker` – future Docker/infra manifests.

## Data pipeline quick start

Each script now lives under `services/data_pipeline`. Run them as modules so imports resolve cleanly:

```bash
pipenv run python -m services.data_pipeline.build_chunks --help
pipenv run python -m services.data_pipeline.embed_chunks --backend local --help
pipenv run python -m services.data_pipeline.dof_scraper --help
```

Config JSON files live in `services/data_pipeline/config/`, and helpers in `services/data_pipeline/paths.py` keep the scripts pointing at the right defaults regardless of your working directory.

## Docker (pgvector + service shells)

Start Postgres with pgvector from the repo root:
```bash
docker compose up -d pgvector
```
- Optional: copy `.env.example` to `.env` at the repo root to override Postgres defaults.
- Defaults are `vector/vectorpass/legalscraper` on port `5432` (override with `POSTGRES_*` envs).
- Init scripts live in `infra/docker/init`; vector table defaults to 1536 dims (OpenAI `text-embedding-3-small`) with HNSW. If you embed at a different dimension (e.g., 3072), adjust the init SQL and drop/recreate the DB volume.

Service placeholders (API/agent/web) use `profiles` and simply keep containers running so you can attach once code lands:
```bash
docker compose --profile api up -d api      # FastAPI hello-world on :8000
docker compose --profile agent up -d agent  # LangChain placeholder prints a greeting
docker compose --profile web up -d web    # node:20 shell in apps/web
```

## Docs map
- Architecture & modules: `ARCHITECTURE.md`
- Tasks/status: `tasks.md`, `next_steps_plan.md`
- Decisions: `embedding_model_decision.md`
- Data pipeline: `services/data_pipeline/README.md`
- API: `apps/api/README.md`
- Infra (pgvector init): `infra/docker/README.md`
- Quick index: `docs/README.md`
