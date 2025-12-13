import os
from typing import Generator, Iterable, List, Optional

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


def embed_texts(texts: Iterable[str]) -> List[List[float]]:
    if openai is None or not OPENAI_API_KEY:
        raise RuntimeError("OpenAI client not configured")
    resp = openai.embeddings.create(model=OPENAI_EMBED_MODEL, input=list(texts))
    return [item.embedding for item in resp.data]  # type: ignore[return-value]


def generate_answer(
    prompt: str, context_chunks: List[str], max_tokens: int = 400
) -> str:
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
            "content": f"Question: {prompt}\n\nContext:\n"
            + "\n\n".join(context_chunks),
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


def summarize_text(
    text: str,
    context_chunks: List[str],
    max_tokens: int = 400,
    model: Optional[str] = None,
) -> str:
    """
    Summarize text using OpenAI if configured; otherwise return a stub with context echoes.
    """
    if openai is None or not OPENAI_API_KEY:
        # Offline fallback: echo the input with a compact stub summary.
        prefix = text[:240].replace("\n", " ")
        bullets = "\n".join(f"- {c[:180]}" for c in context_chunks if c)
        return f"(offline stub summary) {prefix}...\n\nContext:\n{bullets}"

    chosen_model = model or OPENAI_MODEL
    messages = [
        {
            "role": "system",
            "content": (
                "You are a legal summarizer. Produce a concise summary grounded ONLY in the provided context. "
                "If you cite, reference chunk_id values explicitly."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize the following text:\n\n{text}\n\nContext:\n"
            + "\n\n".join(context_chunks),
        },
    ]
    kwargs = {
        "model": chosen_model,
        "messages": messages,
    }
    if "gpt-5" in chosen_model or "nano" in chosen_model:
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["temperature"] = 0.2
        kwargs["max_tokens"] = max_tokens

    resp = openai.chat.completions.create(**kwargs)
    return resp.choices[0].message.content or ""


def stream_summary_text(
    text: str,
    context_chunks: List[str],
    max_tokens: int = 400,
    model: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Stream a summary token-by-token. Yields text chunks as they arrive.
    """
    if openai is None or not OPENAI_API_KEY:
        stub = summarize_text(text, context_chunks, max_tokens=max_tokens, model=model)
        yield stub
        return

    chosen_model = model or OPENAI_MODEL
    messages = [
        {
            "role": "system",
            "content": (
                "You are a legal summarizer. Produce a concise summary grounded ONLY in the provided context. "
                "If you cite, reference chunk_id values explicitly."
            ),
        },
        {
            "role": "user",
            "content": f"Summarize the following text:\n\n{text}\n\nContext:\n"
            + "\n\n".join(context_chunks),
        },
    ]
    kwargs = {
        "model": chosen_model,
        "messages": messages,
        "stream": True,
    }
    if "gpt-5" in chosen_model or "nano" in chosen_model:
        kwargs["max_completion_tokens"] = max_tokens
    else:
        kwargs["temperature"] = 0.2
        kwargs["max_tokens"] = max_tokens

    stream = openai.chat.completions.create(**kwargs)
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        if delta and delta.content:
            yield delta.content


def summarize(
    context_chunks: List[str],
    query_text: str,
    max_tokens: int = 400,
    model: Optional[str] = None,
) -> str:
    """
    Compatibility wrapper: summarize given context with a query_text prompt.
    """
    return summarize_text(
        query_text, context_chunks, max_tokens=max_tokens, model=model
    )


def stream_summary(
    context_chunks: List[str],
    query_text: str,
    max_tokens: int = 400,
    model: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Compatibility wrapper: stream summary chunks for the given context + query_text.
    """
    yield from stream_summary_text(
        query_text, context_chunks, max_tokens=max_tokens, model=model
    )
