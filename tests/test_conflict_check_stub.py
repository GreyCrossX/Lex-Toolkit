import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

rg = pytest.importorskip("apps.agent.research_graph")


class StubVectorTool:
    def __init__(self, hits):
        self.hits = hits
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        return {"results": self.hits}


class StubWebTool:
    def __init__(self):
        self.calls = []

    def invoke(self, payload):
        self.calls.append(payload)
        return (
            {"links": ["http://example.com/opposing-party"]}
            if payload.get("query")
            else {}
        )


def test_conflict_check_blocks_on_vector_hit(monkeypatch):
    stub_hits = [
        {"doc_id": "matter-1", "chunk_id": "c1", "distance": 0.25},
        {"doc_id": "matter-2", "chunk_id": "c2", "distance": 0.9},
    ]
    monkeypatch.setattr(rg, "pgvector_inspector_tool", StubVectorTool(stub_hits))
    monkeypatch.setattr(rg, "web_browser_tool", StubWebTool())

    state = {
        "parties": [
            {"id": "P1", "role": "client", "name": "Cliente"},
            {"id": "P2", "role": "opposing", "name": "Acme Corp"},
        ],
        "firm_id": "firm-1",
    }

    result = rg.conflict_check(state)
    cc = result["conflict_check"]
    assert cc["conflict_found"] is True
    assert any(hit["doc_id"] == "matter-1" for hit in cc["hits"])
    assert rg.pgvector_inspector_tool.calls, "vector tool should be called"
    assert rg.web_browser_tool.calls, "web tool should be called"
