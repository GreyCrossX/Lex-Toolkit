from typing import List


def test_search_with_query_uses_embed(monkeypatch, app_modules, client):
    search_module = app_modules["search"]
    called = {"embed": False, "run": False}

    def fake_embed(text: str) -> List[float]:
        called["embed"] = True
        return [0.1, 0.2, 0.3]

    def fake_run(pool, req):
        called["run"] = True
        # return minimal shape
        return [
            {
                "chunk_id": "c1",
                "doc_id": "d1",
                "section": "s1",
                "jurisdiction": "mx",
                "metadata": {},
                "content": "texto",
                "distance": 0.12,
            }
        ]

    monkeypatch.setattr(search_module.llm, "embed_text", fake_embed)
    monkeypatch.setattr(search_module, "run_search", fake_run)

    resp = client.post("/search", json={"query": "hola", "limit": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert called["embed"] and called["run"]
    assert data["results"][0]["doc_id"] == "d1"


def test_qa_with_query_returns_answer(monkeypatch, app_modules, client):
    qa_module = app_modules["qa"]

    def fake_embed(text: str) -> List[float]:
        return [0.1, 0.2]

    def fake_run(pool, req):
        return [
            type(
                "Res",
                (),
                {
                    "chunk_id": "c1",
                    "doc_id": "d1",
                    "section": "s1",
                    "jurisdiction": "mx",
                    "metadata": {},
                    "content": "texto",
                    "distance": 0.1,
                },
            )
        ]

    def fake_generate(prompt, ctx, max_tokens=400):
        return "respuesta"

    monkeypatch.setattr(qa_module.llm, "embed_text", fake_embed)
    monkeypatch.setattr(qa_module.llm, "generate_answer", fake_generate)
    monkeypatch.setattr(qa_module, "run_search", fake_run)

    resp = client.post("/qa", json={"query": "hola", "top_k": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "respuesta"
    assert data["citations"][0]["doc_id"] == "d1"


def test_search_with_embedding_skips_llm(monkeypatch, app_modules, client):
    search_module = app_modules["search"]
    called = {"embed": False, "run": False, "embedding": None}

    def fake_embed(text: str) -> List[float]:
        called["embed"] = True
        return [9.9]

    def fake_run(pool, req):
        called["run"] = True
        called["embedding"] = req.embedding
        return [
            {
                "chunk_id": "c1",
                "doc_id": "d1",
                "section": "s1",
                "jurisdiction": "mx",
                "metadata": {},
                "content": "texto",
                "distance": 0.33,
            }
        ]

    monkeypatch.setattr(search_module.llm, "embed_text", fake_embed)
    monkeypatch.setattr(search_module, "run_search", fake_run)

    resp = client.post("/search", json={"embedding": [0.5, 0.6, 0.7], "limit": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert called["run"] is True
    assert called["embed"] is False
    assert called["embedding"] == [0.5, 0.6, 0.7]
    assert data["results"][0]["distance"] == 0.33


def test_qa_without_results_returns_placeholder(monkeypatch, app_modules, client):
    qa_module = app_modules["qa"]

    def fake_embed(text: str) -> List[float]:
        return [0.1, 0.2, 0.3]

    def fake_run(pool, req):
        return []

    def fail_generate(*args, **kwargs):
        raise AssertionError("generate_answer should not be called when no results")

    monkeypatch.setattr(qa_module.llm, "embed_text", fake_embed)
    monkeypatch.setattr(qa_module, "run_search", fake_run)
    monkeypatch.setattr(qa_module.llm, "generate_answer", fail_generate)

    resp = client.post("/qa", json={"query": "sin contexto", "top_k": 2})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "No relevant context found."
    assert data["citations"] == []


def test_search_accepts_max_distance_and_returns_sorted(
    monkeypatch, app_modules, client
):
    search_module = app_modules["search"]
    captured = {"max_distance": None}

    def fake_run(pool, req):
        captured["max_distance"] = req.max_distance
        unsorted = [
            {
                "chunk_id": "c1",
                "doc_id": "d1",
                "section": "s1",
                "jurisdiction": "mx",
                "metadata": {},
                "content": "A",
                "distance": 0.8,
            },
            {
                "chunk_id": "c2",
                "doc_id": "d2",
                "section": "s2",
                "jurisdiction": "mx",
                "metadata": {},
                "content": "B",
                "distance": 0.2,
            },
        ]
        return sorted(unsorted, key=lambda r: r["distance"])

    monkeypatch.setattr(search_module, "run_search", fake_run)

    resp = client.post(
        "/search", json={"embedding": [0.1], "limit": 5, "max_distance": 0.9}
    )
    assert resp.status_code == 200
    data = resp.json()

    assert captured["max_distance"] == 0.9
    distances = [r["distance"] for r in data["results"]]
    assert distances == sorted(distances)


def test_qa_accepts_max_distance_and_returns_sorted_citations(
    monkeypatch, app_modules, client
):
    qa_module = app_modules["qa"]
    captured = {"max_distance": None}

    def fake_embed(text: str):
        return [0.1]

    def fake_run(pool, req):
        captured["max_distance"] = req.max_distance
        unsorted = [
            type(
                "Res",
                (),
                {
                    "chunk_id": "c1",
                    "doc_id": "d1",
                    "section": "s1",
                    "jurisdiction": "mx",
                    "metadata": {},
                    "content": "A",
                    "distance": 0.5,
                },
            ),
            type(
                "Res",
                (),
                {
                    "chunk_id": "c2",
                    "doc_id": "d2",
                    "section": "s2",
                    "jurisdiction": "mx",
                    "metadata": {},
                    "content": "B",
                    "distance": 0.1,
                },
            ),
        ]
        return sorted(unsorted, key=lambda r: r.distance)

    def fake_generate(prompt, ctx, max_tokens=400):
        return "ok"

    monkeypatch.setattr(qa_module.llm, "embed_text", fake_embed)
    monkeypatch.setattr(qa_module, "run_search", fake_run)
    monkeypatch.setattr(qa_module.llm, "generate_answer", fake_generate)

    resp = client.post("/qa", json={"query": "hola", "top_k": 2, "max_distance": 1.1})
    assert resp.status_code == 200
    data = resp.json()

    assert captured["max_distance"] == 1.1
    distances = [c["distance"] for c in data["citations"]]
    assert distances == sorted(distances)
