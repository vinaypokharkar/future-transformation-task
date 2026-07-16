"""Diagnostic: how does chunk size affect retrieval separation?

Not part of the app. This exists because calibrate.py reported an overlap and
the right response to that is a measurement, not a guessed constant.

Hypothesis under test: at 500 characters a chunk spans several unrelated policy
sections, so its embedding is an average of multiple topics and represents none
of them well. Smaller chunks should isolate one topic each and separate cleanly.

Usage (from backend/, venv activated):
    python -m scripts.sweep_chunking
"""

import numpy as np

from app.models.document import FileType
from app.services.ai import chunker, extractor
from app.services.ai.embedder import embed_query, embed_texts
from scripts.calibrate import CONTROLS, PARAPHRASES, SAMPLE_DIR


def build(chunk_size: int, overlap: int) -> tuple[list[str], list[str], np.ndarray]:
    chunks: list[str] = []
    sources: list[str] = []
    for path in sorted(SAMPLE_DIR.iterdir()):
        if path.suffix.lower() not in (".txt", ".pdf"):
            continue
        file_type = FileType.PDF if path.suffix.lower() == ".pdf" else FileType.TXT
        text = extractor.extract_text(path, file_type)
        if extractor.is_extraction_empty(text):
            continue
        doc_chunks = chunker.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        chunks.extend(doc_chunks)
        sources.extend([path.name] * len(doc_chunks))
    return chunks, sources, embed_texts(chunks)


def evaluate(chunk_size: int, overlap: int) -> dict:
    chunks, sources, vectors = build(chunk_size, overlap)

    para_scores: list[float] = []
    correct = 0
    for pair in PARAPHRASES:
        qv = embed_query(pair.query)[0]
        scores = vectors @ qv
        best = int(np.argmax(scores))
        para_scores.append(float(scores[best]))
        if (
            sources[best] == pair.expect_source
            and pair.expect_contains.lower() in chunks[best].lower()
        ):
            correct += 1

    ctrl_scores: list[float] = []
    for query in CONTROLS:
        qv = embed_query(query)[0]
        ctrl_scores.append(float(np.max(vectors @ qv)))

    lowest = min(para_scores)
    highest = max(ctrl_scores)
    return {
        "chunk_size": chunk_size,
        "overlap": overlap,
        "n_chunks": len(chunks),
        "correct": correct,
        "total": len(PARAPHRASES),
        "lowest_para": lowest,
        "highest_ctrl": highest,
        "gap": lowest - highest,
    }


def main() -> None:
    configs = [
        (150, 30),
        (200, 40),
        (250, 50),
        (300, 60),
        (400, 50),
        (500, 50),
    ]

    print(
        f"{'size':>5} {'ovl':>4} {'chunks':>7} {'ranked':>8} "
        f"{'low_para':>9} {'high_ctrl':>10} {'gap':>8}"
    )
    print("-" * 60)
    rows = []
    for size, overlap in configs:
        r = evaluate(size, overlap)
        rows.append(r)
        print(
            f"{r['chunk_size']:>5} {r['overlap']:>4} {r['n_chunks']:>7} "
            f"{r['correct']:>4}/{r['total']:<3} {r['lowest_para']:>9.4f} "
            f"{r['highest_ctrl']:>10.4f} {r['gap']:>+8.4f}"
        )

    print()
    clean = [r for r in rows if r["gap"] > 0 and r["correct"] == r["total"]]
    if clean:
        best = max(clean, key=lambda r: r["gap"])
        print(
            f"Best fully-correct config: size={best['chunk_size']} "
            f"overlap={best['overlap']} gap={best['gap']:+.4f}"
        )
    else:
        best = max(rows, key=lambda r: r["gap"])
        print(
            f"No config ranks every paraphrase correctly. "
            f"Widest gap: size={best['chunk_size']} gap={best['gap']:+.4f}"
        )
        print("If the gap stays negative at every size, the controls themselves")
        print("may be semantically adjacent to the corpus rather than unrelated.")


if __name__ == "__main__":
    main()
