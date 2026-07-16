from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.schemas.task import TaskFilters


def create(db: Session, task: Task) -> Task:
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_by_id(db: Session, task_id: int) -> Task | None:
    return db.get(Task, task_id)


def list_filtered(db: Session, filters: TaskFilters) -> list[Task]:
    """The dynamic filtering API.

    One composable builder: each supplied filter narrows the statement, absent
    filters are skipped. Adding a filter is one branch, not a new combination —
    the alternative (a handler per permutation, or f-string SQL) is what this
    shape exists to avoid.

    Note the caller is responsible for scoping: TaskFilters arrives here already
    forced to the current user's own ID for non-admins. This layer applies what
    it is given and makes no authorisation decisions.
    """
    stmt = select(Task)

    if filters.status is not None:
        stmt = stmt.where(Task.status == filters.status)
    if filters.assigned_to is not None:
        stmt = stmt.where(Task.assigned_to == filters.assigned_to)
    if filters.created_by is not None:
        stmt = stmt.where(Task.created_by == filters.created_by)
    if filters.document_id is not None:
        stmt = stmt.where(Task.document_id == filters.document_id)

    stmt = stmt.order_by(Task.created_at.desc()).offset(filters.offset).limit(filters.limit)
    return list(db.scalars(stmt))


def update(db: Session, task: Task) -> Task:
    db.commit()
    db.refresh(task)
    return task
