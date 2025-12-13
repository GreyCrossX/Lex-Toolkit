import pytest

from app.interfaces.api.schemas import SearchRequest


def test_search_request_requires_query_or_embedding():
    with pytest.raises(Exception):
        SearchRequest()


def test_search_request_accepts_query():
    req = SearchRequest(query="hola", limit=3)
    assert req.limit == 3
    assert req.query == "hola"


def test_search_request_accepts_embedding_without_query():
    req = SearchRequest(embedding=[0.1, 0.2])
    assert req.embedding == [0.1, 0.2]


def test_search_request_rejects_empty_embedding():
    with pytest.raises(Exception):
        SearchRequest(embedding=[])
