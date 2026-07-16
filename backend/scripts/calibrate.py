"""Measure semantic search quality and derive the similarity floor.

Runs the fixture in sample_docs/calibration.md against a freshly built index and
reports two distributions: paraphrase scores (true positives) and control scores
(false positives). The floor is the midpoint between them — a measured number,
not a guess.

Runs standalone against the sample corpus. It does not touch MySQL or the live
index, so it is safe to run at any time.

Usage (from backend/, venv activated):
    python -m scripts.calibrate
"""

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.services.ai import chunker, extractor
from app.services.ai.embedder import embed_query, embed_texts
from app.models.document import FileType

SAMPLE_DIR = Path(__file__).resolve().parents[2] / "sample_docs"
RESULT_FILE = SAMPLE_DIR / "calibration_result.md"


@dataclass
class Pair:
    query: str
    expect_source: str
    expect_contains: str


PARAPHRASES: list[Pair] = [
    Pair(
        "how long do I have to claim money back after buying something?",
        "expenses_policy.txt",
        "30 days",
    ),
    Pair(
        "can I sleep somewhere expensive when I travel for work?",
        "expenses_policy.txt",
        "180 GBP",
    ),
    Pair(
        "how many characters should my login secret be?",
        "security_policy.txt",
        "twelve characters",
    ),
    Pair(
        "what happens if my laptop gets taken?",
        "security_policy.txt",
        "stolen",
    ),
    Pair(
        "how many days off do new joiners get each year?",
        "onboarding_guide.pdf",
        "25 days",
    ),
    Pair(
        "how long until I am a permanent member of staff?",
        "onboarding_guide.pdf",
        "probation",
    ),
    Pair(
        "am I allowed to do my job from home?",
        "onboarding_guide.pdf",
        "remotely",
    ),
]

# True negatives: off-topic for this corpus in both subject and vocabulary.
# These are what the similarity floor exists to exclude.
CONTROLS: list[str] = [
    "how do I file a patent application?",
    "which vaccinations are required for the office?",
    "how do I book the tennis court?",
    "what is the recipe for the canteen soup?",
    "who won the football match last night?",
]

# Near-miss queries: the same *topic* as something in the corpus, but asking for
# a fact the corpus does not contain. The corpus covers annual leave but not
# parental leave; pay dates but not dividends.
#
# These are measured separately and deliberately NOT used to set the floor,
# because no floor can exclude them. Cosine similarity scores topical
# relatedness, not whether the answer is actually present — so a near-miss
# lands in the same score band as a true hit, by design rather than by defect.
# Treating them as ordinary controls (the first version of this fixture did)
# produces a permanently negative separation gap and sends you chunk-tuning a
# problem that chunking cannot reach.
#
# The real fixes are a cross-encoder reranker or an LLM answerability check over
# the retrieved chunk. Both are out of scope here; the limitation is measured,
# reported, and owned instead of hidden. See README "Known limitations".
NEAR_MISS: list[str] = [
    "what is the parental leave allowance?",
    "what is the company dividend schedule?",
]


def build_corpus() -> tuple[list[str], list[str], np.ndarray]:
    """Chunk and embed every sample document. Returns (chunks, sources, vectors)."""
    chunks: list[str] = []
    sources: list[str] = []

    for path in sorted(SAMPLE_DIR.iterdir()):
        if path.suffix.lower() not in (".txt", ".pdf"):
            continue
        if path.name in ("calibration.md", "calibration_result.md"):
            continue

        file_type = FileType.PDF if path.suffix.lower() == ".pdf" else FileType.TXT
        text = extractor.extract_text(path, file_type)
        if extractor.is_extraction_empty(text):
            print(f"  WARNING: {path.name} extracted no text, skipping")
            continue

        doc_chunks = chunker.chunk_text(text)
        chunks.extend(doc_chunks)
        sources.extend([path.name] * len(doc_chunks))
        print(f"  {path.name:28} -> {len(doc_chunks):3} chunks")

    print(f"\nEmbedding {len(chunks)} chunks...")
    vectors = embed_texts(chunks)
    return chunks, sources, vectors


def top_hit(query: str, vectors: np.ndarray) -> tuple[int, float]:
    """Best (index, cosine) for a query. Vectors are normalized, so a dot
    product is the cosine — the same arithmetic FAISS IndexFlatIP performs."""
    qv = embed_query(query)[0]
    scores = vectors @ qv
    best = int(np.argmax(scores))
    return best, float(scores[best])


def main() -> int:
    print("Building corpus from sample_docs/\n")
    chunks, sources, vectors = build_corpus()

    if not chunks:
        print("No chunks built. Run: python -m scripts.make_sample_pdf")
        return 1

    lines: list[str] = []

    print("\n" + "=" * 78)
    print("PARAPHRASE QUERIES (true positives — zero shared content words)")
    print("=" * 78)

    para_scores: list[float] = []
    failures: list[str] = []

    for i, pair in enumerate(PARAPHRASES, 1):
        idx, score = top_hit(pair.query, vectors)
        hit_source = sources[idx]
        chunk = chunks[idx]

        source_ok = hit_source == pair.expect_source
        content_ok = pair.expect_contains.lower() in chunk.lower()
        verdict = "PASS" if (source_ok and content_ok) else "FAIL"
        if verdict == "FAIL":
            failures.append(
                f"Q{i} {pair.query!r}: expected {pair.expect_source} "
                f"containing {pair.expect_contains!r}, got {hit_source}"
            )

        para_scores.append(score)
        print(f"\n[{verdict}] Q{i}: {pair.query}")
        print(f"       score : {score:.4f}")
        print(f"       source: {hit_source} (expected {pair.expect_source})")
        print(f"       chunk : {chunk[:100].replace(chr(10), ' ')}...")
        lines.append(f"| {i} | `{pair.query}` | {hit_source} | {score:.4f} | {verdict} |")

    print("\n" + "=" * 78)
    print("CONTROL QUERIES (false-positive ceiling — must be unanswerable)")
    print("=" * 78)

    ctrl_scores: list[float] = []
    ctrl_lines: list[str] = []
    for i, query in enumerate(CONTROLS, 1):
        idx, score = top_hit(query, vectors)
        ctrl_scores.append(score)
        print(f"\nC{i}: {query}")
        print(f"       best score: {score:.4f} (from {sources[idx]})")
        ctrl_lines.append(f"| {i} | `{query}` | {sources[idx]} | {score:.4f} |")

    print("\n" + "=" * 78)
    print("NEAR-MISS QUERIES (right topic, absent fact — a known limitation)")
    print("=" * 78)

    near_scores: list[float] = []
    near_lines: list[str] = []
    for i, query in enumerate(NEAR_MISS, 1):
        idx, score = top_hit(query, vectors)
        near_scores.append(score)
        print(f"\nN{i}: {query}")
        print(f"       best score: {score:.4f} (from {sources[idx]})")
        print("       (scores like a true hit — cosine measures topic, not answerability)")
        near_lines.append(f"| {i} | `{query}` | {sources[idx]} | {score:.4f} |")

    lowest_para = min(para_scores)
    highest_ctrl = max(ctrl_scores)
    highest_near = max(near_scores) if near_scores else 0.0
    gap = lowest_para - highest_ctrl
    floor = (lowest_para + highest_ctrl) / 2

    print("\n" + "=" * 78)
    print("RESULT")
    print("=" * 78)
    print(f"  lowest paraphrase score : {lowest_para:.4f}  (weakest true positive)")
    print(f"  highest control score   : {highest_ctrl:.4f}  (strongest true negative)")
    print(f"  separation gap          : {gap:+.4f}")
    print(f"  highest near-miss score : {highest_near:.4f}  (known limitation, not gated)")

    if failures:
        print("\n  RANKING FAILURES:")
        for f in failures:
            print(f"    - {f}")

    if gap <= 0:
        print("\n  VERDICT: OVERLAP — no floor can separate signal from noise.")
        print("  A real answer scores below a piece of noise. This is a retrieval")
        print("  problem: adjust CHUNK_SIZE / CHUNK_OVERLAP and re-measure.")
        print("  Do NOT pick a threshold to paper over this.")
        status = "OVERLAP — retrieval needs work"
    else:
        print(f"\n  VERDICT: SEPARATED — set SIMILARITY_FLOOR={floor:.4f}")
        print(f"  Every true positive scores above it; every control falls below.")
        status = f"SEPARATED (gap {gap:+.4f})"

    RESULT_FILE.write_text(
        "\n".join(
            [
                "# Calibration Result",
                "",
                "Generated by `backend/scripts/calibrate.py`. These are measured",
                "values, not estimates. Fixture and rationale: `calibration.md`.",
                "",
                f"**Verdict: {status}**",
                "",
                "## Paraphrase queries (true positives)",
                "",
                "Each query shares zero content words with the passage that answers it,",
                "so keyword search cannot connect them. Only embeddings can.",
                "",
                "| # | Query | Top hit | Score | Ranked correctly |",
                "|---|-------|---------|-------|------------------|",
                *lines,
                "",
                "## Control queries (true negatives)",
                "",
                "Off-topic for this corpus in both subject and vocabulary. These are",
                "what the floor exists to exclude.",
                "",
                "| # | Query | Nearest doc | Score |",
                "|---|-------|-------------|-------|",
                *ctrl_lines,
                "",
                "## Near-miss queries (known limitation)",
                "",
                "Right topic, absent fact. The corpus covers annual leave but not",
                "parental leave; pay but not dividends. These score like true hits,",
                "because cosine similarity measures topical relatedness rather than",
                "whether the answer is actually present. No similarity floor can",
                "separate them — raising the floor to exclude these would start",
                "rejecting genuine answers first.",
                "",
                "| # | Query | Nearest doc | Score |",
                "|---|-------|-------------|-------|",
                *near_lines,
                "",
                "Fixing this properly needs a cross-encoder reranker or an LLM",
                "answerability check over the retrieved chunk. Both are out of scope",
                "here, so the limitation is measured and documented rather than hidden.",
                "",
                "## Derived threshold",
                "",
                f"- Lowest paraphrase score (weakest true positive): **{lowest_para:.4f}**",
                f"- Highest control score (strongest true negative): **{highest_ctrl:.4f}**",
                f"- Separation gap: **{gap:+.4f}**",
                f"- Chosen `SIMILARITY_FLOOR`: **{floor:.4f}** (midpoint)",
                f"- Highest near-miss score: **{highest_near:.4f}** (not gated — see above)",
                "",
                f"Ranking failures: {len(failures)}",
                *([""] + [f"- {f}" for f in failures] if failures else []),
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"\n  Written to {RESULT_FILE}")

    return 0 if (gap > 0 and not failures) else 1


if __name__ == "__main__":
    sys.exit(main())
