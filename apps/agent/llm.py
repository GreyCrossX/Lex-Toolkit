"""
Shared LLM client builder to keep configuration DRY across agents.

Uses OPENAI_API_KEY from the environment. Swap models or providers here to
propagate changes everywhere.
"""
from __future__ import annotations

import os
from typing import Optional

from langchain_openai import ChatOpenAI


DEFAULT_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")


def get_llm(model: Optional[str] = None, temperature: float = 0.0, max_tokens: Optional[int] = None) -> ChatOpenAI:
    """
    Create a ChatOpenAI client with sensible defaults.

    Args:
        model: Model name; defaults to env OPENAI_MODEL or gpt-4o-mini.
        temperature: Sampling temperature (default 0.0 for determinism).
        max_tokens: Optional cap on completion tokens.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set; cannot create LLM client.")

    return ChatOpenAI(
        api_key=api_key,
        model=model or DEFAULT_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
    )
