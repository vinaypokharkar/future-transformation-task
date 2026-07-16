import logging

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.activity_log import ActivityAction
from app.models.role import RoleName
from app.models.task import Task, TaskAssignment, TaskStatus
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
    # dict.fromkeys rather than set(): duplicates must go, but the caller's
    # order is worth keeping so the UI lists assignees as they were chosen.
    assignee_ids = list(dict.fromkeys(payload.assignee_ids))

    users = {u.id: u for u in (user_repo.get_by_id(db, uid) for uid in assignee_ids) if u}
    missing = [uid for uid in assignee_ids if uid not in users]
    if missing:
        raise ValidationError(f"No user with id {', '.join(str(m) for m in missing)}")

    if payload.document_id is not None:
        if document_repo.get_by_id(db, payload.document_id) is None:
            raise ValidationError(f"No document with id {payload.document_id}")

    task = Task(
        title=payload.title,
        description=payload.description,
        created_by=creator.id,
        document_id=payload.document_id,
        due_date=payload.due_date,
    )
    task.assignments = [
        TaskAssignment(user_id=uid, status=TaskStatus.PENDING) for uid in assignee_ids
    ]
    task_repo.create(db, task)

    activity_service.log(
        db,
        user_id=creator.id,
        action=ActivityAction.TASK_UPDATE,
        entity_type="task",
        entity_id=task.id,
        detail={"event": "created", "assignee_ids": assignee_ids},
        ip_address=ip_address,
    )
    return task


def list_tasks(db: Session, *, filters: TaskFilters, user: User) -> list[Task]:
    """List tasks, scoped to what the caller is allowed to see.

    The inner half of defence in depth. The route's role guard cannot answer
    "are these *your* tasks?", so scoping happens here: a non-admin's
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

    # 404 rather than 403 when the task exists but the caller is not on it. A
    # 403 would confirm the ID is real, letting an attacker map the table by
    # probing IDs and reading status codes.
    if task is None:
        raise NotFoundError("Task not found")
    if not _is_admin(user) and user.id not in task.assignee_ids:
        raise NotFoundError("Task not found")
    return task


def update_status(
    db: Session,
    *,
    task_id: int,
    new_status: TaskStatus,
    user: User,
    target_user_id: int | None = None,
    ip_address: str | None = None,
) -> Task:
    """Update one assignee's status on a task.

    Status is per-assignee, so this always resolves to exactly one assignment.
    A caller changes their own; an admin may name another via target_user_id,
    which is how an admin who is not on the task can still correct it.
    """
    task = get_task(db, task_id=task_id, user=user)

    if target_user_id is not None and target_user_id != user.id:
        if not _is_admin(user):
            # Silently scoping this to self would tell a user their update
            # succeeded while changing a different row than they asked for.
            raise NotFoundError("Task not found")
        subject_id = target_user_id
    else:
        subject_id = user.id

    assignment = task_repo.get_assignment(db, task_id, subject_id)
    if assignment is None:
        # Covers an admin who is not assigned and named nobody. There is no
        # sensible assignment to change, and inventing one would be wrong.
        raise NotFoundError(
            f"User {subject_id} is not assigned to this task"
            if subject_id != user.id
            else "Task not found"
        )

    previous = assignment.status
    if previous == new_status:
        return task

    assignment.status = new_status
    db.commit()
    db.refresh(task)

    activity_service.log(
        db,
        user_id=user.id,
        action=ActivityAction.TASK_UPDATE,
        entity_type="task",
        entity_id=task.id,
        detail={
            "event": "status_change",
            "assignee_id": subject_id,
            "from": previous.value,
            "to": new_status.value,
            # The task-level rollup after this change, so the log answers "when
            # did this task actually finish?" without replaying every row.
            "task_status": task.status.value,
        },
        ip_address=ip_address,
    )
    logger.info(
        "Task %s assignment for user %s: %s -> %s (task now %s) by user %s",
        task.id,
        subject_id,
        previous.value,
        new_status.value,
        task.status.value,
        user.id,
    )
    return task
