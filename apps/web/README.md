# LexToolkit Web (Next.js App Router)

Frontend shell for the LexToolkit MVP. Uses pnpm, App Router, Tailwind v4, and the palette documented in `ARCHITECTURE.md`.

## Commands

```bash
# from apps/web
pnpm dev               # runs Next.js
pnpm dev -- --full     # runs docker compose up -d pgvector api, then Next.js
pnpm lint              # next lint
pnpm build             # next build
```

`NEXT_PUBLIC_API_URL` defaults to `http://localhost:8000` (see `.env.example`). The dev script fails fast with a readable error if Docker/compose is not available when `--full` is used.

## Pages
- `/` landing hero with tools overview and CTA
- `/login` fake login (stores demo token locally; JWT planned)
- `/dashboard` tool grid with endpoint pings and backend availability toasts

## Notes
- Tool cards are placeholders for unfinished modules. Available tools (search, QA) ping the backend health endpoint.
- If the backend is down, a toast shows and details are logged to the console.
