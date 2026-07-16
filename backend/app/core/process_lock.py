"""An exclusive, cross-process lock on the vector index.

Why this exists
---------------
The FAISS index lives in this process's memory. Two processes serving the same
app means two divergent indexes: an upload mutates process A's copy, a search
routed to process B finds nothing, and both race writes to the same index file.
Every response is still 200 — the failure is completely silent.

An environment-variable check (WEB_CONCURRENCY) catches how compose runs the
app, but it cannot see `uvicorn --workers 4`: the CLI flag never touches the
environment, so the guard would pass and four workers would boot happily. The
README claimed the app refuses to start multi-worker; without this, that claim
was false for the exact command the README warns about.

An OS-level lock has no such blind spot. It does not care how the second
process came to exist — uvicorn workers, a stray second uvicorn, a script run
while the server is up. The kernel releases the lock when the holder dies, so
a crash cannot strand it the way a PID file would.
"""

import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

_lock_handle = None


class IndexLockError(RuntimeError):
    """Raised when another process already owns the index."""


def _lock_exclusive(fh) -> bool:
    """Try to take an exclusive, non-blocking lock. False if already held."""
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def acquire(index_path: str) -> None:
    """Claim sole ownership of the index, or refuse to start.

    The handle is deliberately kept in a module global: the lock lives exactly
    as long as this process does, and letting the file object be collected
    would release it.
    """
    global _lock_handle

    if _lock_handle is not None:
        return

    # Derived from the index filename, not its directory: the test suite points
    # at data/test_faiss.index while the dev server uses data/faiss.index, and a
    # directory-level lock would make them collide — pytest would refuse to run
    # whenever the server was up, for no real reason. One lock per index.
    lock_path = Path(f"{index_path}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    fh = open(lock_path, "a+")
    if not _lock_exclusive(fh):
        fh.close()
        raise IndexLockError(
            f"Another process already holds the vector index lock at {lock_path}.\n"
            "\n"
            "The FAISS index is in-process, so exactly one process may own it. "
            "Running multiple workers gives each its own divergent copy: uploads "
            "land in one, searches hit another and silently return nothing, and "
            "all of them race writes to the same index file — while every "
            "response stays 200.\n"
            "\n"
            "Run with --workers 1, or stop the other server. Scaling out means "
            "externalising the vector store (Chroma in server mode, Qdrant). "
            "See ADR-007 in the README."
        )

    _lock_handle = fh
    fh.seek(0)
    fh.truncate()
    fh.write(str(os.getpid()))
    fh.flush()
    logger.info("Acquired exclusive index lock (pid=%s)", os.getpid())


def release() -> None:
    global _lock_handle
    if _lock_handle is None:
        return
    try:
        if sys.platform == "win32":
            import msvcrt

            _lock_handle.seek(0)
            msvcrt.locking(_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(_lock_handle.fileno(), fcntl.LOCK_UN)
    except OSError:
        # The kernel drops the lock on process exit regardless, so a failure to
        # release explicitly is not worth crashing shutdown over.
        logger.debug("Explicit index lock release failed; the OS will reclaim it")
    finally:
        _lock_handle.close()
        _lock_handle = None
        logger.info("Released index lock")
