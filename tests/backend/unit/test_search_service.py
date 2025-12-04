from app.application.search_service import run_search
from app.interfaces.api.schemas import SearchRequest


class FakeCursor:
    def __init__(self, pool):
        self.pool = pool

    def execute(self, query, params):
        self.pool.last_query = query
        self.pool.last_params = params

    def fetchall(self):
        return self.pool.rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeConnection:
    def __init__(self, pool):
        self.pool = pool

    def cursor(self):
        return FakeCursor(self.pool)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakePool:
    def __init__(self, rows):
        self.rows = rows
        self.last_query = None
        self.last_params = None

    def connection(self):
        return FakeConnection(self)


def test_run_search_builds_params_and_maps_rows():
    request = SearchRequest(
        embedding=[0.1, 0.2],
        limit=2,
        doc_ids=["DOC1"],
        jurisdictions=["CDMX"],
        sections=["intro"],
        max_distance=0.5,
    )
    rows = [
        {
            "chunk_id": "c1",
            "doc_id": "doc-1",
            "section": "s1",
            "jurisdiction": "CDMX",
            "metadata": None,
            "content": "texto",
            "distance": 0.25,
        }
    ]
    pool = FakePool(rows)

    results = run_search(pool, request)

    assert pool.last_params["embedding"] == "[0.1,0.2]"
    assert pool.last_params["doc_ids"] == ["DOC1"]
    assert pool.last_params["jurisdictions"] == ["cdmx"]
    assert pool.last_params["sections"] == ["intro"]
    assert pool.last_params["max_distance"] == 0.5
    assert results[0].doc_id == "doc-1"
    assert results[0].metadata == {}
