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


def test_rare_proper_noun_is_found_lexically(client, alice_headers, indexed_proper_noun):
    """The bug hybrid retrieval exists to fix.

    "Impeccable" is a project name. MiniLM only knows the everyday adjective, so
    it embeds the chunk that genuinely contains the word at 0.2337 — below the
    0.2668 floor — and pure semantic search returns nothing at all. The word is
    right there in the text. See ADR-009.
    """
    r = client.post(f"{P}/search", headers=alice_headers, json={"query": "Impeccable"})
    assert r.status_code == 200

    results = r.json()
    assert results, "a word present in the corpus returned nothing"
    assert "Impeccable" in results[0]["chunk_text"]
    assert results[0]["match_type"] == "lexical"


def test_lexical_hit_reports_a_score_below_the_floor(
    client, alice_headers, indexed_proper_noun
):
    """A lexical result keeps its real cosine rather than a flattering one.

    Reporting the true 0.2337 alongside match_type=lexical is what makes the
    result honest: it says "found because the string is here, not because the
    meaning matched". Inventing a passing score would hide exactly the thing
    worth knowing.
    """
    r = client.post(f"{P}/search", headers=alice_headers, json={"query": "Impeccable"})
    hit = r.json()[0]

    assert hit["match_type"] == "lexical"
    assert hit["score"] < settings.similarity_floor


def test_paraphrase_still_matches_semantically(client, alice_headers, indexed_document):
    """Adding lexical retrieval must not weaken the semantic half.

    This query shares no content words with its answer, so FULLTEXT cannot find
    it. If this ever reports match_type=lexical, the embedding path has broken
    and the AI requirement is no longer being met by the thing meeting it.
    """
    r = client.post(
        f"{P}/search",
        headers=alice_headers,
        json={"query": "how long do I have to claim money back after buying something?"},
    )
    hit = r.json()[0]

    assert "30 days" in hit["chunk_text"]
    assert hit["match_type"] in ("semantic", "both")
    assert hit["score"] >= settings.similarity_floor


def test_lexical_half_does_not_admit_unrelated_queries(
    client, alice_headers, indexed_document
):
    """The regression risk of hybrid search, tested rather than assumed.

    Lexical retrieval widens what gets admitted, which is the point — and also
    the danger. If FULLTEXT matched loosely, a control query would start
    returning results and the floor's precision would be quietly gone. It does
    not, because none of these content words appear in the corpus.
    """
    for query in [
        "how do I book the tennis court?",
        "what is the parental leave allowance?",
    ]:
        r = client.post(f"{P}/search", headers=alice_headers, json={"query": query})
        assert r.status_code == 200
        assert r.json() == [], f"{query!r} should return nothing"


def test_query_punctuation_is_text_not_operators(
    client, alice_headers, indexed_proper_noun
):
    """NATURAL LANGUAGE MODE, not BOOLEAN MODE.

    In boolean mode a leading +/-/* in a user's query becomes an operator, so
    "-Impeccable" would silently invert the search. Natural language mode treats
    the whole string as terms, and a parameterised query keeps it data either
    way. The point is that these return rather than 500.
    """
    for query in ["+Impeccable", "-Impeccable", 'Impeccable "', "Impeccable*"]:
        r = client.post(f"{P}/search", headers=alice_headers, json={"query": query})
        assert r.status_code == 200, f"{query!r} broke the endpoint"
