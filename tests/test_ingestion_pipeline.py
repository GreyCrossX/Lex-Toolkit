import os

import pytest

from app.infrastructure.ingestion import pipeline


class DummyCursor:
    def __init__(self, executed):
        self.executed = executed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, _sql, params):
        self.executed.append(params)


class DummyConnection:
    def __init__(self, executed):
        self.executed = executed
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return DummyCursor(self.executed)

    def commit(self):
        self.committed = True


class DummyPool:
    def __init__(self):
        self.executed = []
        self.committed = False

    def connection(self):
        return DummyConnection(self.executed)


@pytest.fixture(autouse=True)
def _jwt_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", os.environ.get("JWT_SECRET", "testsecret" * 4))
    monkeypatch.setenv("JWT_AUDIENCE", "lex-web")
    monkeypatch.setenv("JWT_ISSUER", "legalscraper-api")


def test_ingest_pdf_uses_doc_type_tuning(monkeypatch, tmp_path):
    calls = []

    def fake_extract(_raw_bytes, max_pages):
        calls.append(max_pages)
        return "Suprema Corte de Justicia de la Nación\n" + "jurisprudencia " * 600

    monkeypatch.setattr(pipeline, "extract_plain_text_from_pdf", fake_extract)
    monkeypatch.setattr(pipeline, "Json", lambda payload: payload)
    monkeypatch.setattr(
        pipeline.llm,
        "embed_texts",
        lambda texts: [[float(i)] for i, _ in enumerate(texts)],
    )

    pool = DummyPool()
    pdf_path = tmp_path / "case.pdf"
    pdf_path.write_text("dummy")

    doc_id, chunk_count = pipeline.ingest_pdf(
        pool, pdf_path, "doc-1", doc_type="jurisprudence"
    )

    assert calls[0] == pipeline.DOC_TYPE_CONFIG["jurisprudence"]["max_pages"]
    assert chunk_count == pipeline.DOC_TYPE_CONFIG["jurisprudence"]["max_chunks"]
    assert pool.executed, "expected insert statements"
    inserted_metadata = pool.executed[0]["metadata"]
    assert inserted_metadata["doc_type"] == "jurisprudence"
    assert "jurisprudence" in inserted_metadata["tags"]
    assert inserted_metadata["jurisdiction_hint"] == "federal"
    assert (
        inserted_metadata["chunking"]["max_chunks"]
        == pipeline.DOC_TYPE_CONFIG["jurisprudence"]["max_chunks"]
    )
