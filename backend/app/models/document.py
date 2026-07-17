import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FileType(str, enum.Enum):
    TXT = "txt"
    PDF = "pdf"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    INDEXED = "indexed"
    FAILED = "failed"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[FileType] = mapped_column(
        Enum(FileType, values_callable=lambda e: [m.value for m in e]), nullable=False
    )
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, values_callable=lambda e: [m.value for m in e]),
        default=DocumentStatus.PENDING,
        nullable=False,
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    uploader: Mapped["User"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan", passive_deletes=True
    )
    tasks: Mapped[list["Task"]] = relationship(back_populates="document")

    def __repr__(self) -> str:
        return f"<Document {self.title} ({self.status.value})>"


class DocumentChunk(Base):
    """One embeddable slice of a document.

    Not in the brief's minimum table list, but chunk-level retrieval is the only
    design that works: a single embedding for a 20-page PDF averages away every
    specific fact and retrieves nothing useful. The primary key is what FAISS
    stores as its vector ID, which is what lets a search hit map straight back to
    MySQL without a side-car mapping file. See ADR-003.
    """

    __tablename__ = "document_chunks"

    # BIGINT because FAISS vector IDs are int64.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_chunk_document_order", "document_id", "chunk_index"),
        # Backs the lexical half of hybrid retrieval. Embeddings cannot find a
        # rare proper noun — MiniLM has never seen the token, so it embeds the
        # nearest everyday word instead and the real chunk scores below the
        # floor. A FULLTEXT index answers "is this string actually here?", which
        # is the one question cosine similarity cannot. See ADR-009.
        Index("ix_chunk_content_fulltext", "content", mysql_prefix="FULLTEXT"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk doc={self.document_id} #{self.chunk_index}>"
