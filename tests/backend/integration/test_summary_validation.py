def test_summary_requires_text_or_doc_ids(client):
    resp = client.post("/summary", json={})
    assert resp.status_code == 422


def test_summary_multi_requires_inputs(client):
    resp = client.post("/summary/multi", json={})
    assert resp.status_code == 422
