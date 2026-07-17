import logging
import time

import numpy as np
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.activity_log import ActivityAction
from app.models.document import DocumentChunk
from app.models.user import User
from app.repositories import document_repo
from app.schemas.search import MatchType, SearchResult
from app.services import activity_service
from app.services.ai import embedder
from app.services.ai.vector_store import VectorStore, get_vector_store

logger = logging.getLogger(__name__)


def _score_lexically_found(
    store: VectorStore,
    chunk_ids: list[int],
    by_id: dict[int, DocumentChunk],
    query_vector: np.ndarray,
) -> dict[int, float]:
    """Cosine for chunks the lexical half found, so one scale reaches the API.

    Normally this is a reconstruct: the vector is already in FAISS, and reading
    it back costs nothing.

    The fallback matters more than it looks. A chunk with no vector means the
    index has drifted from MySQL, and in that state the semantic half is blind
    for the whole document — but the text is still in MySQL, so the lexical half
    still finds it. Embedding the stored content recovers exactly the cosine the
    vector would have produced, which turns a lost index into slower search
    rather than missing results. Scoring these at some placeholder instead would
    put an invented number in the response, and the drift is already logged by
    similarity_for and repaired by scripts/reindex.py.
    """
    scores = store.similarity_for(chunk_ids, query_vector)

    missing = [cid for cid in chunk_ids if cid not in scores and cid in by_id]
    if missing:
        query = np.asarray(query_vector, dtype=np.float32).reshape(-1)
        vectors = embedder.embed_texts([by_id[cid].content for cid in missing])
        for chunk_id, vector in zip(missing, vectors, strict=True):
            scores[chunk_id] = float(vector @ query)

    return scores


def search(
    db: Session,
    *,
    query: str,
    k: int | None,
    user: User,
    ip_address: str | None = None,
) -> list[SearchResult]:
    """Hybrid search: embed the query, retrieve semantically and lexically, fuse.

    Two retrievers, because they fail in opposite directions.

    The semantic half embeds the query and takes FAISS's nearest neighbours. It
    finds paraphrases — "claim money back" retrieves "reimbursement within 30
    days" — and it is what the AI requirement asks for. But FAISS always returns
    its k nearest neighbours no matter how far away they are, so the floor is
    what stops an unrelated query coming back with confident-looking results.
    Its value is measured by scripts/calibrate.py, not guessed.

    The lexical half asks MySQL whether the terms are literally present. It
    exists because the floor has a blind spot that tuning the floor cannot fix:
    a rare proper noun is invisible to the embedding model. MiniLM never saw
    "Impeccable" as a project name, so it embeds the everyday adjective, the
    chunk genuinely containing the word scores 0.2337, and a floor of 0.2668
    drops it. Lowering the floor does not help — measured against that same
    corpus, an absent word ("Kubernetes") scored 0.3732, higher than the present
    one. No floor separates them, because cosine measures topical relatedness
    rather than presence. See ADR-009.

    Fusion is a union, not an arithmetic blend. A result is admitted when it is
    semantically close OR lexically present, and every admitted result is then
    scored the same way — as a cosine — so one comparable number reaches the API
    and results still rank by descending score. MySQL's FULLTEXT relevance ranks
    candidates within the lexical query and is discarded afterwards; adding it to
    a cosine would combine two different units into a meaningless third.
    """
    k = k or settings.search_top_k
    started = time.perf_counter()
    store = get_vector_store()

    query_vector = embedder.embed_query(query)
    semantic_hits = store.search(query_vector, k)
    semantic = {
        chunk_id: score
        for chunk_id, score in semantic_hits
        if score >= settings.similarity_floor
    }

    lexical_hits = document_repo.lexical_search(db, query, k)
    lexical_ids = [chunk_id for chunk_id, _ in lexical_hits]
    lexical_only = [cid for cid in lexical_ids if cid not in semantic]

    # Hydrate before scoring: the drift fallback needs the chunk text to embed.
    chunks = document_repo.get_chunks_by_ids(
        db, list(dict.fromkeys(list(semantic) + lexical_only))
    )
    by_id = {c.id: c for c in chunks}

    # Lexical hits arrive without a cosine, so they are scored the same way the
    # semantic path scores its own — one comparable number for every result.
    candidates: dict[int, float] = dict(semantic)
    candidates.update(
        _score_lexically_found(store, lexical_only, by_id, query_vector)
    )

    lexical_id_set = set(lexical_ids)
    results: list[SearchResult] = []
    for chunk_id, score in candidates.items():
        chunk = by_id.get(chunk_id)
        if chunk is None:
            # A vector whose row is gone: the index has drifted from MySQL.
            # Skip it rather than 500, and log — /health's index_consistent
            # flag reports the same drift, and reindex.py repairs it.
            logger.warning(
                "Vector %s has no chunk row; index is stale. Run scripts/reindex.py",
                chunk_id,
            )
            continue

        in_semantic = chunk_id in semantic
        in_lexical = chunk_id in lexical_id_set
        if in_semantic and in_lexical:
            match_type = MatchType.BOTH
        elif in_semantic:
            match_type = MatchType.SEMANTIC
        else:
            match_type = MatchType.LEXICAL

        results.append(
            SearchResult(
                document_id=chunk.document_id,
                document_title=chunk.document.title,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.content,
                score=round(score, 4),
                match_type=match_type,
            )
        )

    results.sort(key=lambda r: r.score, reverse=True)
    results = results[:k]

    elapsed_ms = (time.perf_counter() - started) * 1000
    top_score = results[0].score if results else None

    # Instrumentation, not decoration: a rising rate of zero-result searches is
    # the only signal that would reveal a silently broken index. The semantic and
    # lexical counts are logged separately because the two halves fail
    # independently — a FULLTEXT index that never fires looks identical to one
    # that is simply never needed.
    logger.info(
        "search q_len=%d k=%d semantic=%d above_floor=%d lexical=%d returned=%d top=%s %.1fms",
        len(query),
        k,
        len(semantic_hits),
        len(semantic),
        len(lexical_hits),
        len(results),
        f"{top_score:.4f}" if top_score is not None else "none",
        elapsed_ms,
    )

    activity_service.log(
        db,
        user_id=user.id,
        action=ActivityAction.SEARCH,
        detail={
            "query": query,
            "result_count": len(results),
            "top_score": top_score,
        },
        ip_address=ip_address,
    )
    return results
