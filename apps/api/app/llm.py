import os
from typing import List

try:
    import openai
except ImportError:  # pragma: no cover - optional dependency
    openai = None  # type: ignore[assignment]

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_EMBED_MODEL = os.environ.get("OPENAI_EMBED_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if openai and OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY


def embed_text(query: str) -> List[float]:
    if openai is None or not OPENAI_API_KEY:
        raise RuntimeError("OpenAI client not configured")
    resp = openai.embeddings.create(model=OPENAI_EMBED_MODEL, input=[query])
    return resp.data[0].embedding  # type: ignore[return-value]


def generate_answer(prompt: str, context_chunks: List[str], max_tokens: int = 400) -> str:
    """
    Generate an answer using OpenAI if configured; otherwise return a simple concatenation.
    """
    if openai is None or not OPENAI_API_KEY:
        # Offline fallback: return concatenated snippets with prompt prefix.
        bullets = "\n".join(f"- {c[:200]}" for c in context_chunks if c)
        return f"(offline stub) {prompt}\n\nContext:\n{bullets}"

    messages = [
        {
            "role": "system",
            "content": "You are a legal assistant. Answer concisely using only the provided context. Always cite chunk_id values.",
        },
        {
            "role": "user",
            "content": f"Question: {prompt}\n\nContext:\n" + "\n\n".join(context_chunks),
        },
    ]
    kwargs = {
        "model": OPENAI_MODEL,
        "messages": messages,
    }
    if "gpt-5" in OPENAI_MODEL or "nano" in OPENAI_MODEL:
        # Nano models: keep default temperature; use max_completion_tokens.
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["temperature"] = 0.2
        kwargs["max_tokens"] = max_tokens

    resp = openai.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""
