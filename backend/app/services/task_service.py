import logging

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.activity_log import ActivityAction
from app.models.role import RoleName
from app.models.task import Task, TaskStatus
from app.models.user import User
from app.repositories import document_repo, task_repo, user_repo
from app.schemas.task import TaskCreate, TaskFilters
from app.services import activity_service

logger = logging.getLogger(__name__)


def _is_admin(user: User) -> bool:
    return user.role_name == RoleName.ADMIN


def create_task(
    db: Session, *, payload: TaskCreate, creator: User, ip_address: str | None = None
) -> Task:
    assignee = user_repo.get_by_id(db, payload.assigned_to)
    if assignee is None:
        raise ValidationError(f"No user with id {payload.assigned_to}")

    if payload.document_id is not None:
        if document_repo.get_by_id(db, payload.document_id) is None:
            raise ValidationError(f"No document with id {payload.document_id}")

    task = Task(
        title=payload.title,
        description=payload.description,
        status=TaskStatus.PENDING,
        assigned_to=payload.assigned_to,
        created_by=creator.id,
        document_id=payload.document_id,
        due_date=payload.due_date,
    )
    task_repo.create(db, task)

    activity_service.log(
        db,
        user_id=creator.id,
        action=ActivityAction.TASK_UPDATE,
        entity_type="task",
        entity_id=task.id,
        detail={"event": "created", "assigned_to": payload.assigned_to},
        ip_address=ip_address,
    )
    return task


def list_tasks(db: Session, *, filters: TaskFilters, user: User) -> list[Task]:
    """List tasks, scoped to what the caller is allowed to see.

    This is the inner half of defence in depth. The route's role guard cannot
    answer "are these *your* tasks?", so scoping happens here: a non-admin's
    assigned_to filter is overwritten with their own ID regardless of what they
    sent. A user probing ?assigned_to=<someone_else> gets their own tasks back,
    not a 403 — the request is legitimate, its scope is simply not theirs to
    choose.
    """
    if not _is_admin(user):
        filters = filters.model_copy(update={"assigned_to": user.id})
    return task_repo.list_filtered(db, filters)


def get_task(db: Session, *, task_id: int, user: User) -> Task:
    task = task_repo.get_by_id(db, task_id)

    # 404 rather than 403 when the task exists but is not the caller's. A 403
    # would confirm the ID is real, letting an attacker map the table by
    # probing IDs and reading the status code.
    if task is None:
        raise NotFoundError("Task not found")
    if not _is_admin(user) and task.assigned_to != user.id:
        raise NotFoundError("Task not found")
    return task


def update_status(
    db: Session,
    *,
    task_id: int,
    new_status: TaskStatus,
    user: User,
    ip_address: str | None = None,
) -> Task:
    task = get_task(db, task_id=task_id, user=user)

    previous = task.status
    if previous == new_status:
        return task

    task.status = new_status
    task_repo.update(db, task)

    activity_service.log(
        db,
        user_id=user.id,
        action=ActivityAction.TASK_UPDATE,
        entity_type="task",
        entity_id=task.id,
        detail={"event": "status_change", "from": previous.value, "to": new_status.value},
        ip_address=ip_address,
    )
    logger.info(
        "Task %s status %s -> %s by user %s",
        task.id,
        previous.value,
        new_status.value,
        user.id,
    )
    return task
