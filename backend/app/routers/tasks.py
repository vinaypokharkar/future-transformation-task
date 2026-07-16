from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status

from app.core.deps import AdminUser, CurrentUser, DbSession, get_client_ip
from app.models.task import TaskStatus
from app.schemas.task import TaskCreate, TaskFilters, TaskOut, TaskStatusUpdate
from app.services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate, request: Request, db: DbSession, admin: AdminUser
) -> TaskOut:
    task = task_service.create_task(
        db, payload=payload, creator=admin, ip_address=get_client_ip(request)
    )
    return TaskOut.model_validate(task)


@router.get("", response_model=list[TaskOut])
def list_tasks(
    db: DbSession,
    current_user: CurrentUser,
    status_: Annotated[TaskStatus | None, Query(alias="status")] = None,
    assigned_to: Annotated[int | None, Query()] = None,
    created_by: Annotated[int | None, Query()] = None,
    document_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[TaskOut]:
    """Dynamic filtering: every param is optional and composes with the rest.

    Non-admin callers are scoped to their own tasks in the service, whatever
    assigned_to they pass.
    """
    filters = TaskFilters(
        status=status_,
        assigned_to=assigned_to,
        created_by=created_by,
        document_id=document_id,
        limit=limit,
        offset=offset,
    )
    tasks = task_service.list_tasks(db, filters=filters, user=current_user)
    return [TaskOut.model_validate(t) for t in tasks]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: DbSession, current_user: CurrentUser) -> TaskOut:
    task = task_service.get_task(db, task_id=task_id, user=current_user)
    return TaskOut.model_validate(task)


@router.patch("/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: int,
    payload: TaskStatusUpdate,
    request: Request,
    db: DbSession,
    current_user: CurrentUser,
) -> TaskOut:
    task = task_service.update_status(
        db,
        task_id=task_id,
        new_status=payload.status,
        user=current_user,
        ip_address=get_client_ip(request),
    )
    return TaskOut.model_validate(task)
