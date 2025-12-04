# Agent

LangGraph / orchestration code lives here (graphs, tools, agent configs).

## Research agent

- Graph: `apps/agent/research_graph.py` with structured nodes (intake → qualify → classify → facts → issues → plan → search loop → briefing), status constants, and tenant-aware filters.
- Tools: `pgvector_inspector` (pgvector semantic lookup) and `web_browser` (HTTP(S) fetch with allowlist/limits) via shared registry.
- LLM config: centralized in `apps/agent/llm.py` (OpenAI chat + structured output). Env vars: `OPENAI_API_KEY`, `OPENAI_MODEL` (default gpt-4o-mini), `OPENAI_EMBED_MODEL`.

Quick use:

```python
from apps.agent.research_graph import demo_research_run, get_research_tools

print(demo_research_run("Cliente indica despido injustificado en CDMX"))
tools = get_research_tools()  # pgvector_inspector, web_browser
```

## Tools

Reusable tools sit in `apps/agent/tools` and are exported via `TOOL_REGISTRY`:

- `pgvector_inspector` — semantic lookup over `legal_chunks` in Postgres/pgvector (honors `firm_id` filter, clamps top_k).
- `web_browser` — HTTP(S) fetch returning title/text/links with size/time limits and env allowlist (`BROWSER_ALLOWED_DOMAINS`).

Import helpers with:

```python
from apps.agent.tools import get_tools

tools = get_tools()
```
