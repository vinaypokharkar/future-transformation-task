from typing import Annotated

from fastapi import APIRouter, File, Form, Query, Request, UploadFile, status

from app.core.deps import AdminUser, CurrentUser, DbSession, get_client_ip
from app.models.document import DocumentStatus, FileType
from app.schemas.document import DocumentFilters, DocumentOut
from app.services import document_service

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    db: DbSession,
    admin: AdminUser,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form()] = None,
) -> DocumentOut:
    document = document_service.upload(
        db,
        file=file,
        title=title,
        uploader=admin,
        ip_address=get_client_ip(request),
    )
    return DocumentOut.model_validate(document)


@router.get("", response_model=list[DocumentOut])
def list_documents(
    db: DbSession,
    current_user: CurrentUser,
    file_type: Annotated[FileType | None, Query()] = None,
    status_: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    uploaded_by: Annotated[int | None, Query()] = None,
) -> list[DocumentOut]:
    filters = DocumentFilters(
        file_type=file_type, status=status_, uploaded_by=uploaded_by
    )
    documents = document_service.list_documents(db, filters)
    return [DocumentOut.model_validate(d) for d in documents]


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(
    document_id: int, db: DbSession, current_user: CurrentUser
) -> DocumentOut:
    return DocumentOut.model_validate(document_service.get_document(db, document_id))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: DbSession, admin: AdminUser) -> None:
    document_service.delete_document(db, document_id)
