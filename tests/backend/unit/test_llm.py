import importlib

import pytest


def test_embed_text_raises_without_api_key(monkeypatch):
  llm = importlib.import_module("app.llm")
  monkeypatch.setattr(llm, "OPENAI_API_KEY", None)
  monkeypatch.setattr(llm, "openai", None)
  with pytest.raises(RuntimeError):
    llm.embed_text("hola")


def test_generate_answer_offline_fallback(monkeypatch):
  llm = importlib.import_module("app.llm")
  monkeypatch.setattr(llm, "OPENAI_API_KEY", None)
  monkeypatch.setattr(llm, "openai", None)

  prompt = "¿Cuál es el requisito?"
  snippets = ["Contexto relevante", "Otro fragmento"]

  answer = llm.generate_answer(prompt, snippets, max_tokens=50)

  assert "(offline stub)" in answer
  assert prompt in answer
  assert "Contexto relevante" in answer
