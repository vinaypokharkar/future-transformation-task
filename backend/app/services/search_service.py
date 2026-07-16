import logging
import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.activity_log import ActivityAction
from app.models.user import User
from app.repositories import document_repo
from app.schemas.search import SearchResult
from app.services import activity_service
from app.services.ai import embedder
from app.services.ai.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def search(
    db: Session,
    *,
    query: str,
    k: int | None,
    user: User,
    ip_address: str | None = None,
) -> list[SearchResult]:
    """Semantic search: embed the query, retrieve nearest chunks, hydrate.

    The floor is what stops the system inventing answers. FAISS always returns
    its k nearest neighbours no matter how far away they are, so without a
    cut-off an unrelated query still comes back with confident-looking results.
    Its value is measured by scripts/calibrate.py, not guessed — see
    sample_docs/calibration_result.md.
    """
    k = k or settings.search_top_k
    started = time.perf_counter()

    query_vector = embedder.embed_query(query)
    hits = get_vector_store().search(query_vector, k)

    above_floor = [(cid, s) for cid, s in hits if s >= settings.similarity_floor]

    chunks = document_repo.get_chunks_by_ids(db, [cid for cid, _ in above_floor])
    by_id = {c.id: c for c in chunks}

    results: list[SearchResult] = []
    for chunk_id, score in above_floor:
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
        results.append(
            SearchResult(
                document_id=chunk.document_id,
                document_title=chunk.document.title,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.content,
                score=round(score, 4),
            )
        )

    elapsed_ms = (time.perf_counter() - started) * 1000
    top_score = results[0].score if results else None

    # Instrumentation, not decoration: a rising rate of zero-result searches is
    # the only signal that would reveal a silently broken index. Without it, the
    # failure reads as "users searching for things we don't have".
    logger.info(
        "search q_len=%d k=%d hits=%d above_floor=%d returned=%d top=%s %.1fms",
        len(query),
        k,
        len(hits),
        len(above_floor),
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
