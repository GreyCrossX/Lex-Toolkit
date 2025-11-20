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
