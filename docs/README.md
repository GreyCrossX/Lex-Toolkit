# Docs Map (for me)

Quick pointers to all markdown references and what they cover.

- Repo overview: `README.md` (monorepo layout, docker usage, current snapshot).
- Architecture: `ARCHITECTURE.md` (modules 0–7, current implementation status).
- Planning/status: `tasks.md` (Linear-aligned tasks), `next_steps_plan.md` (older Linear plan snapshot).
- Decisions: `embedding_model_decision.md` (GRE-24 embedder choice), `services/data_pipeline/tiktoken_chunking_review.md` (chunk/tokenization review).
- Data pipeline: `services/data_pipeline/README.md` (scripts usage).
- Services: `apps/api/README.md` (API + Redis/Celery upload worker), `apps/agent/README.md` (agent placeholder, not containerized yet), `apps/web/README.md` (frontend dashboard + tests).
- Infra: `infra/docker/README.md` (pgvector init scripts and compose notes).
- Testing: `tests.md` (coverage + how to run pytest/Vitest).
- Utility: `PUSH_COMMANDS.md` (local CLI hints, if needed).
