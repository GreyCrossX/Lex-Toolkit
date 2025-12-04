import importlib
from types import SimpleNamespace

from app.interfaces.api.schemas import MultiSummaryRequest, SearchResult, SummaryRequest


def _fake_result(idx: int) -> SearchResult:
    return SearchResult(
        chunk_id=f"chunk-{idx}",
        doc_id=f"doc-{idx}",
        section="sec",
        jurisdiction="mx",
        metadata={"foo": "bar"},
        content=f"contenido {idx}",
        distance=0.1 * idx,
    )


def test_summarize_document_uses_retrieval(monkeypatch):
    svc = importlib.import_module("app.application.summary_service")

    # Fake search results and LLM output.
    monkeypatch.setattr(
        svc,
        "run_search",
        lambda pool, req: [_fake_result(1), _fake_result(2)],
    )
    monkeypatch.setattr(svc.llm, "embed_text", lambda q: [0.1, 0.2])
    monkeypatch.setattr(
        svc.llm,
        "summarize_text",
        lambda text, chunks, max_tokens: f"summary of {len(chunks)} chunks for {text}",
    )

    req = SummaryRequest(text="hola mundo", top_k=2)
    resp = svc.summarize_document(pool=SimpleNamespace(), req=req)

    assert resp.summary.startswith("summary of 2 chunks")
    assert len(resp.citations) == 2
    assert resp.chunks_used == 2
    assert resp.citations[0].chunk_id == "chunk-1"


def test_stream_summary_document_yields_events(monkeypatch):
    svc = importlib.import_module("app.application.summary_service")

    monkeypatch.setattr(
        svc,
        "run_search",
        lambda pool, req: [_fake_result(1)],
    )
    monkeypatch.setattr(svc.llm, "embed_text", lambda q: [0.1, 0.2])

    def fake_stream(text, chunks, max_tokens):
        yield "parte A"
        yield "parte B"

    monkeypatch.setattr(svc.llm, "stream_summary_text", fake_stream)

    req = SummaryRequest(text="demo", top_k=1, stream=True)
    events = list(svc.stream_summary_document(pool=SimpleNamespace(), req=req))

    types = [e.type for e in events]
    assert types == ["citation", "summary_chunk", "summary_chunk", "done"]
    assert events[0].data.chunk_id == "chunk-1"
    assert events[-1].data["chunks_used"] == 1


def test_summarize_multi_combines_texts(monkeypatch):
    svc = importlib.import_module("app.application.summary_service")

    monkeypatch.setattr(
        svc,
        "run_search",
        lambda pool, req: [_fake_result(1)],
    )
    monkeypatch.setattr(svc.llm, "embed_text", lambda q: [0.1, 0.2])
    monkeypatch.setattr(
        svc.llm,
        "summarize_text",
        lambda text, chunks, max_tokens: f"multi summary for: {text[:10]}",
    )

    req = MultiSummaryRequest(texts=["uno", "dos"], top_k=1)
    resp = svc.summarize_multi(pool=SimpleNamespace(), req=req)

    assert "multi summary" in resp.summary
    assert len(resp.citations) == 1
