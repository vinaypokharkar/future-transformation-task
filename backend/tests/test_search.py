from app.core.config import settings

P = settings.api_prefix


def test_paraphrase_ranks_first(client, alice_headers, indexed_document):
    """The test that proves the AI requirement is genuinely met.

    The query shares no content words with the chunk that answers it:
    "claim money back" vs "reimbursement within 30 days of purchase". A keyword
    search (LIKE, TF-IDF, BM25) scores this at zero. Only an embedding connects
    them, so if this passes, retrieval is really semantic.
    """
    r = client.post(
        f"{P}/search",
        headers=alice_headers,
        json={"query": "how long do I have to claim money back after buying something?"},
    )
    assert r.status_code == 200

    results = r.json()
    assert results, "paraphrase returned nothing"
    assert "30 days" in results[0]["chunk_text"]
    assert results[0]["score"] >= settings.similarity_floor


def test_second_paraphrase_ranks_first(client, alice_headers, indexed_document):
    r = client.post(
        f"{P}/search",
        headers=alice_headers,
        json={"query": "can I sleep somewhere expensive when I travel for work?"},
    )
    results = r.json()
    assert results
    assert "180 GBP" in results[0]["chunk_text"]


def test_unrelated_query_returns_empty(client, alice_headers, indexed_document):
    """Precision matters as much as recall.

    FAISS always returns its k nearest neighbours regardless of distance, so
    without the floor an off-topic query still comes back with confident-looking
    results. The floor's value is measured by scripts/calibrate.py.
    """
    r = client.post(
        f"{P}/search", headers=alice_headers, json={"query": "how do I book the tennis court?"}
    )
    assert r.status_code == 200
    assert r.json() == []


def test_results_ranked_descending(client, alice_headers, indexed_document):
    r = client.post(
        f"{P}/search", headers=alice_headers, json={"query": "expenses and travel policy", "k": 5}
    )
    scores = [hit["score"] for hit in r.json()]
    assert scores == sorted(scores, reverse=True)


def test_search_writes_activity_log(client, db, alice_headers, alice, indexed_document):
    from app.models.activity_log import ActivityAction, ActivityLog

    query = "how long do I have to claim money back after buying something?"
    client.post(f"{P}/search", headers=alice_headers, json={"query": query})

    logs = db.query(ActivityLog).filter(ActivityLog.action == ActivityAction.SEARCH).all()
    assert len(logs) == 1
    # /analytics reads top queries out of this JSON payload.
    assert logs[0].detail["query"] == query
    assert logs[0].detail["result_count"] >= 1


def test_search_requires_auth(client, indexed_document):
    r = client.post(f"{P}/search", json={"query": "anything"})
    assert r.status_code == 401
