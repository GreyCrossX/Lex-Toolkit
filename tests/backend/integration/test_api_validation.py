def test_search_requires_query_or_embedding(client):
    resp = client.post("/search", json={})
    assert resp.status_code == 422


def test_qa_requires_query(client):
    resp = client.post("/qa", json={})
    assert resp.status_code == 422
