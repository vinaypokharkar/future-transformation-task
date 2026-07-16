import logging
import threading

import numpy as np

from app.core.config import settings

logger = logging.getLogger(__name__)

_model = None
_lock = threading.Lock()


def get_embedder():
    """Return the process-wide SentenceTransformer, loading it on first call.

    Loading is ~80MB of download on a cold machine and several seconds of init
    even when cached, so it happens once at startup (see main.lifespan) rather
    than per request. Double-checked locking keeps a burst of concurrent first
    requests from loading the model N times.
    """
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading embedding model %s", settings.embedding_model)
                _model = SentenceTransformer(settings.embedding_model)
                logger.info(
                    "Loaded embedding model, dim=%d",
                    _model.get_sentence_embedding_dimension(),
                )
    return _model


def is_loaded() -> bool:
    return _model is not None


def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed a batch of texts into L2-normalized float32 vectors.

    Normalization is what makes FAISS's inner-product index equivalent to cosine
    similarity, so every score the API returns is a cosine in [-1, 1] and is
    comparable across queries. Batching in one encode() call rather than looping
    is roughly an order of magnitude faster.
    """
    if not texts:
        return np.empty((0, settings.embedding_dim), dtype=np.float32)

    model = get_embedder()
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
        batch_size=32,
    )
    return np.asarray(vectors, dtype=np.float32)


def embed_query(query: str) -> np.ndarray:
    """Embed one query, shaped (1, dim) as FAISS expects."""
    return embed_texts([query]).reshape(1, -1)
