import logging
import uuid
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.models.activity_log import ActivityAction
from app.models.document import Document, DocumentChunk, DocumentStatus, FileType
from app.models.user import User
from app.repositories import document_repo
from app.schemas.document import DocumentFilters
from app.services import activity_service
from app.services.ai import chunker, embedder, extractor
from app.services.ai.vector_store import get_vector_store

logger = logging.getLogger(__name__)

_EXTENSION_TO_TYPE = {".txt": FileType.TXT, ".pdf": FileType.PDF}


def _resolve_file_type(filename: str) -> FileType:
    suffix = Path(filename).suffix.lower()
    file_type = _EXTENSION_TO_TYPE.get(suffix)
    if file_type is None:
        raise ValidationError(
            f"Unsupported file type '{suffix or filename}'. Allowed: .txt, .pdf"
        )
    return file_type


def upload(
    db: Session,
    *,
    file: UploadFile,
    title: str | None,
    uploader: User,
    ip_address: str | None = None,
) -> Document:
    """Ingest a document: store, extract, chunk, embed, index.

    Ordering is deliberate. MySQL is committed before the FAISS index is
    written, and the document is only marked 'indexed' once both have
    succeeded. If the index write fails the document stays 'pending' and
    scripts/reindex.py repairs it from the database.

    The reverse order — index first, then database — would leave vectors
    pointing at rows that never got committed, so searches would return hits
    that cannot be hydrated. That is a silent wrong answer, the worst failure
    mode available to a search system.
    """
    file_type = _resolve_file_type(file.filename or "")

    # Check the declared size BEFORE reading. Reading first and measuring after
    # makes the limit decorative: a multi-GB upload would exhaust memory long
    # before the check it was supposed to fail.
    if file.size is not None and file.size > settings.max_upload_bytes:
        raise ValidationError(
            f"File exceeds {settings.max_upload_mb}MB limit "
            f"({file.size / 1024 / 1024:.1f}MB)"
        )

    contents = file.file.read(settings.max_upload_bytes + 1)
    # file.size is client-supplied via Content-Length, so re-check what actually
    # arrived. Reading one byte past the limit is what makes an over-sized body
    # detectable without holding all of it.
    if len(contents) > settings.max_upload_bytes:
        raise ValidationError(f"File exceeds {settings.max_upload_mb}MB limit")
    if not contents:
        raise ValidationError("File is empty")

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{Path(file.filename or '').suffix.lower()}"
    storage_path = upload_dir / stored_name
    storage_path.write_bytes(contents)

    document = Document(
        title=title or Path(file.filename or stored_name).stem,
        filename=stored_name,
        original_filename=file.filename,
        file_type=file_type,
        file_size=len(contents),
        storage_path=str(storage_path),
        uploaded_by=uploader.id,
        status=DocumentStatus.PENDING,
        chunk_count=0,
    )
    document_repo.create(db, document)

    try:
        _index_document(db, document, storage_path, file_type)
    except ValidationError:
        _mark_failed(db, document)
        raise
    except Exception:
        logger.exception("Indexing failed for document %s", document.id)
        _mark_failed(db, document)
        raise ValidationError("Failed to index document")

    activity_service.log(
        db,
        user_id=uploader.id,
        action=ActivityAction.DOCUMENT_UPLOAD,
        entity_type="document",
        entity_id=document.id,
        detail={
            "title": document.title,
            "file_type": file_type.value,
            "chunk_count": document.chunk_count,
        },
        ip_address=ip_address,
    )
    return document


def _mark_failed(db: Session, document: Document) -> None:
    """Mark a document failed, discarding anything the failed attempt staged.

    The rollback is the load-bearing part. _index_document flushes chunk rows to
    obtain the primary keys FAISS uses as vector IDs, so by the time embedding
    runs there are pending INSERTs in the transaction. Committing the FAILED
    status without rolling back first would commit those chunks too: rows in
    MySQL with no vectors in FAISS, on a document reporting chunk_count=0.

    That breaks ntotal == COUNT(document_chunks) permanently — /health would
    report index_consistent: false forever, and reindex would embed chunks
    belonging to a document that never successfully indexed.
    """
    db.rollback()
    document.status = DocumentStatus.FAILED
    document.chunk_count = 0
    db.commit()


def _index_document(
    db: Session, document: Document, path: Path, file_type: FileType
) -> None:
    text = extractor.extract_text(path, file_type)

    if extractor.is_extraction_empty(text):
        # Almost always a scanned or image-only PDF. Failing loudly beats
        # accepting a document that would never be findable.
        raise ValidationError(
            "No text could be extracted. Scanned or image-only PDFs are not "
            "supported (OCR is out of scope)."
        )

    chunks = chunker.chunk_text(text)
    if not chunks:
        raise ValidationError("Document produced no indexable content")

    chunk_rows = [
        DocumentChunk(
            document_id=document.id,
            chunk_index=i,
            content=content,
            token_count=len(content.split()),
        )
        for i, content in enumerate(chunks)
    ]
    # flush() assigns the primary keys that FAISS will store as vector IDs.
    document_repo.add_chunks(db, chunk_rows)

    vectors = embedder.embed_texts([c.content for c in chunk_rows])
    chunk_ids = [c.id for c in chunk_rows]

    document.chunk_count = len(chunk_rows)
    document.status = DocumentStatus.INDEXED
    db.commit()

    store = get_vector_store()
    ntotal_before = store.ntotal
    store.add(vectors, chunk_ids)
    store.persist()

    logger.info(
        "Indexed document id=%s title=%r chunks=%d ntotal %d -> %d",
        document.id,
        document.title,
        len(chunk_rows),
        ntotal_before,
        store.ntotal,
    )


def list_documents(db: Session, filters: DocumentFilters) -> list[Document]:
    return document_repo.list_filtered(db, filters)


def get_document(db: Session, document_id: int) -> Document:
    document = document_repo.get_by_id(db, document_id)
    if document is None:
        raise NotFoundError("Document not found")
    return document


def delete_document(db: Session, document_id: int) -> None:
    """Delete a document, its chunks (FK cascade), and its vectors.

    Vector IDs and the storage path are both read before the delete. The IDs
    because afterwards the chunk rows are gone and there is no way to know which
    vectors to remove — exactly how an index accumulates orphans that still
    match searches. The path because reading an attribute off an instance the
    session has already deleted relies on detached-object semantics rather than
    on anything guaranteed.
    """
    document = get_document(db, document_id)
    chunk_ids = document_repo.get_chunk_ids_for_document(db, document_id)
    storage_path = Path(document.storage_path)

    document_repo.delete(db, document)

    if chunk_ids:
        store = get_vector_store()
        removed = store.remove(chunk_ids)
        store.persist()
        logger.info(
            "Deleted document %s: removed %d/%d vectors (ntotal=%d)",
            document_id,
            removed,
            len(chunk_ids),
            store.ntotal,
        )

    if storage_path.exists():
        storage_path.unlink()
