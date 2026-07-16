import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _assert_single_worker() -> None:
    """Refuse to boot silently under multiple workers.

    The FAISS index lives in this process's memory. Under N workers there are N
    divergent indexes: an upload mutates worker A's copy, a later search is
    routed to worker B and finds nothing, and every worker races writes to the
    same index file. Every response is still 200 — the failure is completely
    silent, which is why it gets an explicit check instead of a README note.

    The vector_store lock guards threads inside one process and is useless
    across processes. Single-worker is the constraint that makes this design
    correct; scaling out means externalising the vector store.
    See ADR-007 in the README.

    This check is only the early, friendly half: it reads the environment, which
    is how compose configures workers, and fails with a clear message before any
    expensive startup work. It cannot see `uvicorn --workers 4`, because the CLI
    flag never touches the environment — the exclusive index lock in
    core.process_lock is what actually enforces the constraint.
    """
    workers = os.getenv("WEB_CONCURRENCY") or os.getenv("UVICORN_WORKERS")
    if workers and workers.isdigit() and int(workers) > 1:
        raise RuntimeError(
            f"Refusing to start with {workers} workers. The FAISS index is "
            "in-process; multiple workers cause silent search failures and "
            "index corruption. Run with --workers 1. See ADR-007 in the README."
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    _assert_single_worker()

    # The real enforcement. Unlike the env check above, an OS-level lock is
    # blind to *how* a second process arrived — uvicorn --workers, a stray
    # second server, a script run against the live index. Taken before the model
    # loads so a rejected worker fails in milliseconds rather than after
    # several seconds of wasted startup.
    from app.core import process_lock

    process_lock.acquire(settings.faiss_index_path)

    # Load the embedding model once, at startup. On a cold machine the first
    # call downloads ~80MB from HuggingFace; doing that lazily inside a request
    # handler makes the first search look like a production hang.
    from app.services.ai.embedder import get_embedder
    from app.services.ai.vector_store import get_vector_store

    logger.info("Loading embedding model: %s", settings.embedding_model)
    get_embedder()
    logger.info("Embedding model ready")

    store = get_vector_store()
    logger.info("Vector index ready (ntotal=%d)", store.ntotal)

    yield

    store.persist()
    logger.info("Vector index persisted on shutdown")
    process_lock.release()


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# The exact Vite origin, never "*". Browsers silently reject wildcard origins
# combined with allow_credentials, which presents as an opaque CORS failure.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers import analytics, auth, documents, search, tasks, users  # noqa: E402

for r in (auth.router, users.router, tasks.router, documents.router, search.router, analytics.router):
    app.include_router(r, prefix=settings.api_prefix)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Liveness plus the one invariant this architecture rests on.

    index_consistent compares FAISS's vector count against the chunk rowcount.
    If index writes start failing while database commits keep succeeding, search
    quietly degrades to nothing while every endpoint still returns 200. This
    flag is the only thing that would surface that.
    """
    from sqlalchemy import text

    from app.db.session import SessionLocal
    from app.repositories import document_repo
    from app.services.ai.embedder import is_loaded
    from app.services.ai.vector_store import get_vector_store

    db_ok = True
    chunk_count = 0
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            chunk_count = document_repo.count_chunks(db)
    except Exception:
        logger.exception("Health check: database unreachable")
        db_ok = False

    ntotal = get_vector_store().ntotal
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "model_loaded": is_loaded(),
        "index_ntotal": ntotal,
        "chunk_count": chunk_count,
        "index_consistent": db_ok and ntotal == chunk_count,
    }
