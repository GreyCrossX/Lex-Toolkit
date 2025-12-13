from app.application.search_service import _build_where_clauses
from app.interfaces.api.schemas import SearchRequest


def test_build_where_clauses_with_filters_and_distance():
    req = SearchRequest(
        query=None,
        embedding=[0.1],
        doc_ids=["Doc1", "Doc2"],
        jurisdictions=["CDMX", "FED"],
        sections=["intro"],
        max_distance=0.9,
    )
    clauses, params = _build_where_clauses(
        req, {"embedding": "[0.1]"}, "embedding <-> %(embedding)s::vector"
    )

    assert clauses == [
        "embedding IS NOT NULL",
        "doc_id = ANY(%(doc_ids)s)",
        "jurisdiction = ANY(%(jurisdictions)s)",
        "section = ANY(%(sections)s)",
        "embedding <-> %(embedding)s::vector <= %(max_distance)s",
    ]
    assert params["doc_ids"] == ["Doc1", "Doc2"]
    assert params["jurisdictions"] == ["cdmx", "fed"]
    assert params["sections"] == ["intro"]
    assert params["max_distance"] == 0.9


def test_build_where_clauses_defaults_to_embedding_present():
    req = SearchRequest(query=None, embedding=[0.2])
    clauses, params = _build_where_clauses(
        req, {"embedding": "[0.2]"}, "d <-> %(embedding)s"
    )

    assert clauses == ["embedding IS NOT NULL"]
    assert params["embedding"] == "[0.2]"
