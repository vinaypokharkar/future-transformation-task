from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus, FileType


class DocumentFilters(BaseModel):
    file_type: FileType | None = None
    status: DocumentStatus | None = None
    uploaded_by: int | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    filename: str
    original_filename: str | None
    file_type: FileType
    file_size: int | None
    uploaded_by: int
    status: DocumentStatus
    chunk_count: int
    created_at: datetime
