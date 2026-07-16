"""Rebuild the FAISS index from MySQL.

MySQL is the source of truth; the index holds nothing that cannot be
regenerated from document_chunks. This script is the answer to "what happens
when the index and the database drift apart?" — a question the design invites
by keeping two stores, and one a reviewer will reasonably ask.

Run it when:
  - data/faiss.index is deleted, corrupt, or missing
  - GET /health reports index_consistent: false
  - search logs warn "Vector <id> has no chunk row"
  - a document is stuck in 'pending' after a failed index write

Safe to run repeatedly: the index is rebuilt from scratch, not appended to.

Usage (from backend/, venv activated):
    python -m scripts.reindex
    python -m scripts.reindex --check    # report drift, change nothing
"""

import argparse
import logging
import sys

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document, DocumentStatus
from app.repositories import document_repo
from app.services.ai.embedder import embed_texts
from app.services.ai.vector_store import get_vector_store

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("reindex")


def check() -> int:
    """Report index/database drift without touching anything."""
    store = get_vector_store()
    with SessionLocal() as db:
        chunk_count = document_repo.count_chunks(db)

    ntotal = store.ntotal
    logger.info("FAISS vectors      : %d", ntotal)
    logger.info("MySQL chunk rows   : %d", chunk_count)

    if ntotal == chunk_count:
        logger.info("Status             : consistent")
        return 0

    logger.warning("Status             : DRIFT (%+d)", ntotal - chunk_count)
    logger.warning("Run `python -m scripts.reindex` to rebuild from MySQL.")
    return 1


def rebuild() -> int:
    store = get_vector_store()
    logger.info("Index before rebuild: %d vectors", store.ntotal)

    with SessionLocal() as db:
        chunks = document_repo.all_chunks(db)

        if not chunks:
            store.reset()
            store.persist()
            logger.info("No chunks in MySQL; index reset to empty.")
            return 0

        logger.info("Embedding %d chunks from MySQL...", len(chunks))
        vectors = embed_texts([c.content for c in chunks])
        chunk_ids = [c.id for c in chunks]

        # Rebuild rather than append: appending to an index that already holds
        # some of these IDs would duplicate vectors and skew every score.
        store.reset()
        store.add(vectors, chunk_ids)
        store.persist()

        # A document whose index write failed is left 'pending' by the upload
        # path so that this script can finish the job. Its chunks are in MySQL
        # and now in the index, so the status is the only thing still stale.
        repaired = (
            db.query(Document)
            .filter(
                Document.status == DocumentStatus.PENDING,
                Document.chunk_count > 0,
            )
            .all()
        )
        for doc in repaired:
            doc.status = DocumentStatus.INDEXED
            logger.info("Repaired stuck document id=%s %r", doc.id, doc.title)
        if repaired:
            db.commit()

        chunk_count = document_repo.count_chunks(db)

    logger.info("Index after rebuild : %d vectors", store.ntotal)
    logger.info("MySQL chunk rows    : %d", chunk_count)

    if store.ntotal != chunk_count:
        logger.error("Rebuild finished inconsistent. This should not happen.")
        return 1

    logger.info("Consistent. Index written to %s", settings.faiss_index_path)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report drift and exit without rebuilding",
    )
    args = parser.parse_args()
    return check() if args.check else rebuild()


if __name__ == "__main__":
    sys.exit(main())
