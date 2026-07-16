import re

from app.core.config import settings

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[str]:
    """Split text into overlapping chunks on natural boundaries.

    Two decisions worth stating:

    - Split on paragraph, then sentence boundaries rather than at a fixed
      character offset. A chunk that starts mid-sentence embeds badly: the
      vector reflects a fragment rather than a claim.

    - Overlap consecutive chunks. Without it, a fact spanning a chunk boundary
      is halved and neither half retrieves it — the query matches the whole
      statement, not either fragment.
    """
    chunk_size = chunk_size or settings.chunk_size
    overlap = overlap if overlap is not None else settings.chunk_overlap

    text = text.strip()
    if not text:
        return []

    units = _split_into_units(text, chunk_size)

    chunks: list[str] = []
    current = ""

    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if len(candidate) <= chunk_size:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = _tail(current, overlap)
            current = f"{current}\n\n{unit}" if current else unit
            # A single oversized unit can still exceed the budget after the
            # overlap tail is prepended; hard-split it rather than emit a chunk
            # far larger than every other one.
            if len(current) > chunk_size:
                chunks.extend(_hard_split(current, chunk_size, overlap))
                current = ""
        else:
            chunks.extend(_hard_split(unit, chunk_size, overlap))
            current = ""

    if current.strip():
        chunks.append(current)

    return [c.strip() for c in chunks if c.strip()]


def _split_into_units(text: str, chunk_size: int) -> list[str]:
    """Paragraphs, falling back to sentences for oversized paragraphs."""
    units: list[str] = []
    for paragraph in _PARAGRAPH_SPLIT.split(text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= chunk_size:
            units.append(paragraph)
        else:
            units.extend(s.strip() for s in _SENTENCE_SPLIT.split(paragraph) if s.strip())
    return units


def _tail(text: str, overlap: int) -> str:
    """Trailing `overlap` characters, snapped forward to a word boundary."""
    if overlap <= 0 or len(text) <= overlap:
        return text if overlap > 0 else ""
    tail = text[-overlap:]
    space = tail.find(" ")
    return tail[space + 1 :] if space != -1 else tail


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Last resort for text with no usable boundary (e.g. a wall of tokens)."""
    step = max(chunk_size - overlap, 1)
    return [text[i : i + chunk_size] for i in range(0, len(text), step)]
