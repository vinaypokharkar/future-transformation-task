import io

import pytest

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.models.document import Document, DocumentChunk, DocumentStatus

P = settings.api_prefix


def test_empty_file_rejected(client, admin_headers):
    r = client.post(
        f"{P}/documents",
        headers=admin_headers,
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
    )
    assert r.status_code == 422


def test_unsupported_extension_rejected(client, admin_headers):
    r = client.post(
        f"{P}/documents",
        headers=admin_headers,
        files={"file": ("payload.exe", io.BytesIO(b"MZ\x90\x00"), "application/octet-stream")},
    )
    assert r.status_code == 422


def test_oversized_file_rejected(client, admin_headers):
    """The size limit must be enforced, not decorative.

    An earlier version read the whole body into memory and measured afterwards,
    so a large enough upload would exhaust memory before reaching the check it
    was supposed to fail.
    """
    oversized = b"x" * (settings.max_upload_bytes + 1024)
    r = client.post(
        f"{P}/documents",
        headers=admin_headers,
        files={"file": ("big.txt", io.BytesIO(oversized), "text/plain")},
    )
    assert r.status_code == 422
    assert "exceeds" in r.json()["detail"].lower()


def test_failed_indexing_leaves_no_orphan_chunks(db, admin_user, monkeypatch):
    """A failed index write must not commit the chunks it staged.

    _index_document flushes chunk rows to obtain the primary keys FAISS uses as
    vector IDs, so pending INSERTs exist by the time embedding runs. Committing
    the FAILED status without rolling back first commits those chunks too:
    rows in MySQL with no vectors in FAISS, on a document reporting
    chunk_count=0.

    That breaks ntotal == COUNT(document_chunks) permanently — /health reports
    index_consistent: false forever, and reindex would embed chunks belonging to
    a document that never indexed. Regression test for that exact path.
    """
    from fastapi import UploadFile

    from app.services import document_service

    def boom(_texts):
        raise RuntimeError("simulated embedding failure")

    monkeypatch.setattr(document_service.embedder, "embed_texts", boom)

    before = db.query(DocumentChunk).count()

    content = (
        b"Employees may request reimbursement within 30 days of purchase.\n\n"
        b"Hotel stays are capped at 180 GBP per night in London.\n\n"
        b"Passwords must be at least twelve characters long."
    )
    upload = UploadFile(filename="orphan.txt", file=io.BytesIO(content))

    with pytest.raises(ValidationError):
        document_service.upload(db, file=upload, title="Orphan", uploader=admin_user)

    db.expire_all()

    assert db.query(DocumentChunk).count() == before, "orphan chunks were committed"

    doc = db.query(Document).filter(Document.title == "Orphan").one()
    assert doc.status is DocumentStatus.FAILED
    assert doc.chunk_count == 0
    assert db.query(DocumentChunk).filter(DocumentChunk.document_id == doc.id).count() == 0
