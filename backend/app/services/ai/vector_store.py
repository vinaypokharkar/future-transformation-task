import logging
import threading
from pathlib import Path

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS index mapping chunk IDs to embeddings.

    Design notes:

    - IndexFlatIP over normalized vectors: inner product equals cosine
      similarity. Exact brute-force search — no training step, deterministic
      results, and instant at this scale (a few thousand chunks). IndexIVFFlat
      is the swap for ~100k+ vectors, with the caveat that remove_ids on an
      IDMap2-wrapped IVF index is a known FAISS issue (facebookresearch/faiss
      #4535), so the delete path would need rework alongside it.

    - IndexIDMap2 wraps it so FAISS stores real document_chunks.id values rather
      than sequential positions. A search result therefore maps straight back to
      MySQL with no side-car mapping file to keep in sync. (IndexIDMap also
      supports remove_ids; IDMap2 additionally maintains a reverse map enabling
      efficient reconstruct.)

    - MySQL is the source of truth. This index holds vectors and IDs only, and is
      rebuildable at any time from the database via scripts/reindex.py.

    - The lock serialises writes between threads in this process. It cannot help
      across processes, which is why the app refuses to run multi-worker. See
      ADR-007.
    """

    def __init__(self, dim: int, index_path: str) -> None:
        self.dim = dim
        self.index_path = Path(index_path)
        self._lock = threading.Lock()
        self._index = self._load_or_create()

    def _new_index(self):
        import faiss

        return faiss.IndexIDMap2(faiss.IndexFlatIP(self.dim))

    def _load_or_create(self):
        import faiss

        if self.index_path.exists():
            try:
                index = faiss.read_index(str(self.index_path))
                logger.info(
                    "Loaded FAISS index from %s (ntotal=%d)",
                    self.index_path,
                    index.ntotal,
                )
                return index
            except Exception:
                # A corrupt index is recoverable — MySQL still holds every chunk.
                # Warn loudly and start empty; reindex.py restores it.
                logger.exception(
                    "FAISS index at %s is unreadable; starting empty. "
                    "Run scripts/reindex.py to rebuild from MySQL.",
                    self.index_path,
                )
        return self._new_index()

    @property
    def ntotal(self) -> int:
        return int(self._index.ntotal)

    def add(self, vectors: np.ndarray, chunk_ids: list[int]) -> None:
        if len(chunk_ids) == 0:
            return
        if vectors.shape[0] != len(chunk_ids):
            raise ValueError(
                f"vector/id length mismatch: {vectors.shape[0]} vs {len(chunk_ids)}"
            )
        ids = np.asarray(chunk_ids, dtype=np.int64)
        with self._lock:
            self._index.add_with_ids(np.asarray(vectors, dtype=np.float32), ids)

    def search(self, query_vector: np.ndarray, k: int) -> list[tuple[int, float]]:
        """Return [(chunk_id, score)] ranked by descending cosine similarity."""
        if self.ntotal == 0:
            return []

        k = min(k, self.ntotal)
        with self._lock:
            scores, ids = self._index.search(
                np.asarray(query_vector, dtype=np.float32), k
            )

        results: list[tuple[int, float]] = []
        for score, chunk_id in zip(scores[0], ids[0], strict=True):
            # FAISS pads short result sets with -1.
            if chunk_id == -1:
                continue
            results.append((int(chunk_id), float(score)))
        return results

    def remove(self, chunk_ids: list[int]) -> int:
        if not chunk_ids:
            return 0
        import faiss

        ids = np.asarray(chunk_ids, dtype=np.int64)
        with self._lock:
            removed = self._index.remove_ids(faiss.IDSelectorArray(ids))
        return int(removed)

    def persist(self) -> None:
        import faiss

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        with self._lock:
            faiss.write_index(self._index, str(self.index_path))
        logger.debug("Persisted FAISS index (ntotal=%d)", self.ntotal)

    def reset(self) -> None:
        with self._lock:
            self._index = self._new_index()


_store: VectorStore | None = None
_store_lock = threading.Lock()


def get_vector_store() -> VectorStore:
    global _store
    if _store is None:
        with _store_lock:
            if _store is None:
                _store = VectorStore(settings.embedding_dim, settings.faiss_index_path)
    return _store
