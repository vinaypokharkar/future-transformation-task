from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, joinedload

from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentFilters


def create(db: Session, document: Document) -> Document:
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_by_id(db: Session, document_id: int) -> Document | None:
    return db.get(Document, document_id)


def list_filtered(db: Session, filters: DocumentFilters) -> list[Document]:
    stmt = select(Document)

    if filters.file_type is not None:
        stmt = stmt.where(Document.file_type == filters.file_type)
    if filters.status is not None:
        stmt = stmt.where(Document.status == filters.status)
    if filters.uploaded_by is not None:
        stmt = stmt.where(Document.uploaded_by == filters.uploaded_by)

    return list(db.scalars(stmt.order_by(Document.created_at.desc())))


def add_chunks(db: Session, chunks: list[DocumentChunk]) -> list[DocumentChunk]:
    """Insert chunks and flush so MySQL assigns their IDs.

    The flush is load-bearing: those IDs are what FAISS stores as vector IDs.
    Adding vectors before the database has assigned IDs would build an index
    pointing at rows that do not exist yet.
    """
    db.add_all(chunks)
    db.flush()
    return chunks


def get_chunks_by_ids(db: Session, chunk_ids: list[int]) -> list[DocumentChunk]:
    """Load chunks with their parent document eagerly.

    joinedload is not decoration: every search result renders its document
    title, so a lazy relationship issues one extra SELECT per hit. At k=5 that
    turns a single search into six queries — the classic N+1, on the hottest
    path in the app.
    """
    if not chunk_ids:
        return []
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.id.in_(chunk_ids))
        .options(joinedload(DocumentChunk.document))
    )
    return list(db.scalars(stmt))


def lexical_search(db: Session, query: str, k: int) -> list[tuple[int, float]]:
    """Return [(chunk_id, relevance)] for chunks literally containing the terms.

    The lexical half of hybrid retrieval, backed by the FULLTEXT index on
    content. This exists because embeddings are blind to rare proper nouns: a
    token the model never saw in training has no vector of its own, so it embeds
    as the nearest everyday word and the chunk that actually contains it scores
    below the floor. See ADR-009.

    NATURAL LANGUAGE MODE rather than BOOLEAN MODE: boolean mode would make
    punctuation in a user's query (+, -, *, ") operators rather than text, so
    an innocent question could silently become a different search. Natural
    language mode treats the whole string as terms and ranks by relevance.

    Relevance here is MySQL's own score, on an unbounded scale that has nothing
    to do with cosine. The two are never compared or added — the caller re-scores
    every lexical hit as a cosine so one comparable number reaches the API.

    Parameterised, so a query string is data and never SQL.
    """
    if not query.strip():
        return []

    stmt = text(
        """
        SELECT id, MATCH(content) AGAINST (:q IN NATURAL LANGUAGE MODE) AS relevance
        FROM document_chunks
        WHERE MATCH(content) AGAINST (:q IN NATURAL LANGUAGE MODE)
        ORDER BY relevance DESC
        LIMIT :k
        """
    )
    rows = db.execute(stmt, {"q": query, "k": k}).all()
    return [(int(row.id), float(row.relevance)) for row in rows]


def get_chunk_ids_for_document(db: Session, document_id: int) -> list[int]:
    stmt = select(DocumentChunk.id).where(DocumentChunk.document_id == document_id)
    return list(db.scalars(stmt))


def all_chunks(db: Session) -> list[DocumentChunk]:
    return list(db.scalars(select(DocumentChunk).order_by(DocumentChunk.id)))


def count_chunks(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(DocumentChunk)) or 0


def delete(db: Session, document: Document) -> None:
    db.delete(document)
    db.commit()
