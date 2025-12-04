# LexToolkit Web (Next.js App Router)

Frontend shell for the LexToolkit MVP. Uses pnpm, App Router, Tailwind v4, and the palette documented in `ARCHITECTURE.md`.

## Commands

```bash
# from apps/web
pnpm dev               # runs Next.js
pnpm dev -- --full     # runs docker compose up -d pgvector api, then Next.js
pnpm lint              # next lint
pnpm build             # next build
pnpm test              # vitest (jsdom) for dashboard page/hooks/utils
```

`NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000` (see `.env.example`). The dev script fails fast with a readable error if Docker/compose is not available when `--full` is used.

## Pages
- `/` landing hero with tools overview and CTA
- `/login` fake login (stores demo token locally; JWT planned)
- `/dashboard` tool grid with endpoint pings and backend availability toasts; search/QA form (filters/pagination/sorting), upload card hitting `/upload`, summary card hitting `/summary/document` (streaming NDJSON), with citations rendering.

## Notes
- Tool cards list ready vs coming-soon; search/QA/summary/upload call real endpoints and handle errors with toasts/placeholders.
- Vitest covers dashboard flows (search/QA, summary, upload), hook `useBackendHealth`, and auth helpers.
- If the backend is down, a toast shows and details are logged to the console.
