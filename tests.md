# Estrategia de pruebas (LexToolkit)

## Enfoque general
- **Unitarias**: lógica pura y validaciones sin dependencias externas. Objetivo: rápida retroalimentación (subsegundos).
- **Integración**: rutas FastAPI y servicios tocando contratos de entrada/salida, con dependencias stub o mínimas. Validar shape de requests/responses y validaciones.
- **End-to-end (E2E)**: flujo usuario → API → almacenamiento. Se ejecutan contra el stack levantado (Docker Compose) y usan datos seed.

## Cobertura por componente
- **API (FastAPI)**  
  - Unit: validaciones de esquemas (`SearchRequest` requiere query o embedding), manejo de errores de embeddings.  
  - Integración: rutas `/search` y `/qa` responden 4xx si faltan campos; healthcheck 200.  
  - E2E: `/upload` → ingesta → `/search`/`/qa` sobre pgvector con embeddings reales (requiere stack y seeds).
- **Frontend (Next.js)**  
  - Unit/jsdom: hooks y helpers (Vitest + Testing Library).  
  - Integración ligera: dashboard (search/QA/sumario/upload) con fetch/toasts mockeados (Vitest).  
  - E2E: flujo UI contra backend vivo (pendiente cuando stack esté estable).
- **Data pipeline**  
  - Unit: funciones puras de chunking/tokenización/paths.  
  - Integración: scripts contra fixtures pequeños (pendiente).
- **Infra/DevEx**  
  - Smoke: `docker compose up` + `/health` (pendiente script).

## Suites actuales
- **Unitarias (pytest)**: validación de esquemas (SearchRequest exige query o embedding) y manejo de error en `llm.embed_text` sin API key.
- **Integración (pytest)**: rutas `/search` y `/qa` validan 422 si faltan campos, y tests stub de éxito usando monkeypatch de embedding + search/LLM para formas de respuesta (sin tocar DB real).
- **E2E (pytest)**: placeholder marcado como `xfail` hasta levantar stack completo.
- **Frontend (Vitest)**: dashboard page (search/QA, summary, upload), hook `useBackendHealth`, helpers de auth localStorage.

## Cómo correr
```bash
# Desde la raíz
uv run pytest               # ejecuta unit + integración + e2e placeholder
# Con stack vivo (futuro): uv run pytest -m "not e2e"  # o incluir e2e cuando haya seed/compose
# Desde apps/web
pnpm test                   # Vitest jsdom
```

## Próximos pasos
- Backend: agregar tests de éxito para `/search` y `/qa` usando un pool de test o fixtures de pgvector (requiere seed).
- Frontend: incorporar Playwright para flujos básicos (login demo → dashboard → search/upload/summary) cuando backend esté estable.
- Data pipeline: fixtures pequeños para chunking/embed/export.
