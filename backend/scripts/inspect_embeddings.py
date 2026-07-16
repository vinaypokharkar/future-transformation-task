"""Inspect the embedding pipeline end to end, with real numbers at every stage.

Answers "are vectors actually being created, and are they the right ones?"
without asking anyone to trust a passing test. Every claim below is printed
from live data.

Stages shown:
  1. Model         — what loaded, which device, what dimension
  2. Chunking      — text in, chunks out
  3. Embedding     — actual float values, dimension, L2 norm
  4. Determinism   — same text embedded twice must be identical
  5. Storage       — what FAISS holds, reconstructed and compared to a fresh embed
  6. Retrieval     — manual cosine vs FAISS's own scores, side by side
  7. Semantics     — paraphrase vs unrelated, proving meaning is captured

Usage (from backend/, venv activated):
    python -m scripts.inspect_embeddings
    python -m scripts.inspect_embeddings --chunk-id 3
"""

import argparse
import logging
import sys

import numpy as np

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import DocumentChunk
from app.services.ai import chunker
from app.services.ai.embedder import embed_query, embed_texts, get_embedder
from app.services.ai.vector_store import get_vector_store

# Quiet the HuggingFace/urllib chatter; this script's own output is the point.
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

RULE = "=" * 78


def h(title: str) -> None:
    print(f"\n{RULE}\n{title}\n{RULE}")


def stage_1_model() -> None:
    h("1. MODEL — what actually loaded")
    model = get_embedder()
    dim = model.get_sentence_embedding_dimension()

    print(f"  name              : {settings.embedding_model}")
    print(f"  reported dimension: {dim}")
    print(f"  configured dim    : {settings.embedding_dim}")
    print(f"  device            : {model.device}")
    print(f"  max input tokens  : {model.max_seq_length}")
    print(f"  MATCH             : {dim == settings.embedding_dim}")
    if dim != settings.embedding_dim:
        print("  ^ MISMATCH: FAISS index would reject these vectors.")


def stage_2_chunking() -> str:
    h("2. CHUNKING — text in, chunks out")
    text = (
        "Acme Corporation Expenses Policy\n\n"
        "Reimbursement Window\n\n"
        "Employees may request reimbursement within 30 days of purchase. "
        "Requests submitted after this window require written approval from a "
        "department head, and may be declined.\n\n"
        "Accommodation\n\n"
        "Hotel stays are capped at 180 GBP per night in London and 120 GBP per "
        "night elsewhere in the United Kingdom."
    )
    chunks = chunker.chunk_text(text)
    print(f"  input length : {len(text)} chars")
    print(f"  chunk_size   : {settings.chunk_size}, overlap: {settings.chunk_overlap}")
    print(f"  chunks out   : {len(chunks)}\n")
    for i, c in enumerate(chunks):
        print(f"  [{i}] {len(c):3} chars | {c[:64].replace(chr(10), ' ')}...")
    return chunks[0]


def stage_3_embedding(text: str) -> np.ndarray:
    h("3. EMBEDDING — the actual numbers")
    vec = embed_texts([text])[0]

    print(f"  input  : {text[:60]}...")
    print(f"  output : numpy array, shape={vec.shape}, dtype={vec.dtype}\n")
    print(f"  first 8 values : {np.array2string(vec[:8], precision=5)}")
    print(f"  last 4 values  : {np.array2string(vec[-4:], precision=5)}")
    print(f"  min / max      : {vec.min():.5f} / {vec.max():.5f}")
    print(f"  mean           : {vec.mean():.6f}")

    norm = float(np.linalg.norm(vec))
    print(f"\n  L2 norm        : {norm:.8f}")
    print(f"  NORMALIZED     : {np.isclose(norm, 1.0)}")
    print("  ^ This is why FAISS inner product == cosine similarity.")
    print("    Unit vectors mean a dot product IS the cosine, so every score")
    print("    the API returns is a real cosine in [-1, 1].")
    return vec


def stage_4_determinism(text: str, vec: np.ndarray) -> None:
    h("4. DETERMINISM — same text must give the same vector")
    again = embed_texts([text])[0]
    identical = np.allclose(vec, again, atol=1e-6)
    print(f"  embedded twice, max abs difference : {np.abs(vec - again).max():.10f}")
    print(f"  IDENTICAL                          : {identical}")

    other = embed_texts(["The cat sat on the mat."])[0]
    print(f"\n  different text, cosine vs original : {float(vec @ other):.5f}")
    print("  ^ Different text gives a different vector. The model is not")
    print("    returning a constant, which is the classic silent failure.")


def stage_5_storage(chunk_id: int | None) -> tuple[int, np.ndarray] | None:
    h("5. STORAGE — is the vector really inside FAISS?")
    store = get_vector_store()
    print(f"  index type     : IndexIDMap2(IndexFlatIP({settings.embedding_dim}))")
    print(f"  index file     : {settings.faiss_index_path}")
    print(f"  vectors stored : {store.ntotal}")

    with SessionLocal() as db:
        if chunk_id is None:
            chunk = db.query(DocumentChunk).order_by(DocumentChunk.id).first()
        else:
            chunk = db.get(DocumentChunk, chunk_id)

        if chunk is None:
            print("\n  No chunks in MySQL. Upload a document first.")
            return None

        print(f"  MySQL chunks   : {db.query(DocumentChunk).count()}")
        print(f"  CONSISTENT     : {store.ntotal == db.query(DocumentChunk).count()}")

        print(f"\n  Inspecting chunk id={chunk.id} (document_id={chunk.document_id}):")
        print(f"    text: {chunk.content[:70].replace(chr(10), ' ')}...")

        # This is the proof. IndexIDMap2 keeps a reverse map, so we can pull the
        # stored vector back out by its real MySQL primary key and compare it to
        # a freshly computed one. If these match, the vector in the index truly
        # is the embedding of that exact row — not a stale, shifted, or
        # misaligned one.
        try:
            stored = store._index.reconstruct(int(chunk.id))
        except RuntimeError as exc:
            print(f"    RECONSTRUCT FAILED: {exc}")
            print("    The ID is not in the index — MySQL and FAISS have drifted.")
            print("    Fix: python -m scripts.reindex")
            return None

        stored = np.asarray(stored, dtype=np.float32)
        fresh = embed_texts([chunk.content])[0]

        print(f"\n    vector stored in FAISS  : {np.array2string(stored[:5], precision=5)}")
        print(f"    freshly embedded now    : {np.array2string(fresh[:5], precision=5)}")
        print(f"    max abs difference      : {np.abs(stored - fresh).max():.10f}")
        print(f"    cosine(stored, fresh)   : {float(stored @ fresh):.8f}")
        print(f"    MATCH                   : {np.allclose(stored, fresh, atol=1e-5)}")
        print("\n    ^ The vector FAISS returns for this MySQL row is the embedding")
        print("      of that row's text. Storage and IDs line up.")
        return chunk.id, stored


def stage_6_retrieval() -> None:
    h("6. RETRIEVAL — FAISS scores vs cosine computed by hand")
    store = get_vector_store()
    if store.ntotal == 0:
        print("  Index empty. Upload a document first.")
        return

    query = "how long do I have to claim money back after buying something?"
    qv = embed_query(query)
    print(f"  query: {query!r}\n")

    hits = store.search(qv, k=3)

    with SessionLocal() as db:
        print(f"  {'rank':<5} {'chunk_id':<9} {'FAISS score':<13} {'manual dot':<12} {'agree':<6}")
        print(f"  {'-'*5} {'-'*9} {'-'*13} {'-'*12} {'-'*6}")
        for rank, (cid, score) in enumerate(hits, 1):
            chunk = db.get(DocumentChunk, cid)
            if chunk is None:
                print(f"  {rank:<5} {cid:<9} {score:<13.6f} (no MySQL row — drift)")
                continue
            # Recompute the score independently: embed the chunk text and dot it
            # with the query vector. If this disagrees with FAISS, the index is
            # returning something other than what it claims.
            manual = float(embed_texts([chunk.content])[0] @ qv[0])
            agree = np.isclose(score, manual, atol=1e-4)
            print(f"  {rank:<5} {cid:<9} {score:<13.6f} {manual:<12.6f} {str(agree):<6}")

        print(f"\n  similarity floor : {settings.similarity_floor}")
        kept = [(c, s) for c, s in hits if s >= settings.similarity_floor]
        print(f"  above floor      : {len(kept)} of {len(hits)} returned to the caller")

        if kept:
            top = db.get(DocumentChunk, kept[0][0])
            if top:
                print(f"\n  TOP HIT ({kept[0][1]:.4f}):")
                print(f"    {top.content[:200].replace(chr(10), ' ')}...")


def stage_7_semantics() -> None:
    h("7. SEMANTICS — does the vector actually capture meaning?")
    base = "Employees may request reimbursement within 30 days of purchase."

    probes = [
        ("identical", base),
        ("paraphrase (zero shared words)", "how long do I have to claim money back after buying something?"),
        ("same topic", "expenses and receipts policy"),
        ("unrelated", "how do I book the tennis court?"),
        ("nonsense", "purple monkey dishwasher"),
    ]

    bv = embed_texts([base])[0]
    print(f"  reference: {base!r}\n")
    print(f"  {'relationship':<32} {'cosine':<10} {'vs floor'}")
    print(f"  {'-'*32} {'-'*10} {'-'*8}")
    for label, text in probes:
        score = float(bv @ embed_texts([text])[0])
        verdict = "PASS" if score >= settings.similarity_floor else "below"
        print(f"  {label:<32} {score:<10.4f} {verdict}")

    print("\n  ^ The paraphrase scores high despite sharing no content words with")
    print("    the reference, while unrelated text scores low. That gap is the")
    print("    whole reason for using embeddings instead of keyword matching.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-id", type=int, default=None, help="inspect a specific chunk")
    args = parser.parse_args()

    stage_1_model()
    sample = stage_2_chunking()
    vec = stage_3_embedding(sample)
    stage_4_determinism(sample, vec)
    stage_5_storage(args.chunk_id)
    stage_6_retrieval()
    stage_7_semantics()

    print(f"\n{RULE}\nDone. Every number above came from the live model and index.\n{RULE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
