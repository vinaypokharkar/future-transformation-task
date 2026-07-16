from sqlalchemy import func, select
from sqlalchemy.orm import Session

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
    if not chunk_ids:
        return []
    stmt = select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))
    return list(db.scalars(stmt))


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
