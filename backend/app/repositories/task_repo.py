from sqlalchemy import exists, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.task import Task, TaskAssignment, TaskStatus
from app.schemas.task import TaskFilters


def _with_assignees(stmt):
    """Eager-load assignments and their users.

    Every task response lists its assignees by email, so lazy loading would fire
    one query per assignment per task — an N+1 that grows with both the page
    size and the number of people on each task.
    """
    return stmt.options(
        selectinload(Task.assignments).joinedload(TaskAssignment.user)
    )


def create(db: Session, task: Task) -> Task:
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_by_id(db: Session, task_id: int) -> Task | None:
    return db.scalar(_with_assignees(select(Task).where(Task.id == task_id)))


def list_filtered(db: Session, filters: TaskFilters) -> list[Task]:
    """The dynamic filtering API.

    One composable builder: each supplied filter narrows the statement, absent
    ones are skipped. Adding a filter is one branch, not a new combination.

    Assignment filters use EXISTS subqueries rather than a JOIN. A join against
    a many-to-many table multiplies rows — a task with three assignees would
    appear three times, and LIMIT would then count duplicates rather than
    tasks, silently returning short pages.

    Scoping is the caller's job: TaskFilters arrives already forced to the
    current user's own ID for non-admins. This layer applies what it is given
    and makes no authorisation decisions.
    """
    stmt = _with_assignees(select(Task))

    if filters.assigned_to is not None:
        stmt = stmt.where(
            exists().where(
                TaskAssignment.task_id == Task.id,
                TaskAssignment.user_id == filters.assigned_to,
            )
        )

    if filters.status is not None:
        # A task is completed only when nobody is still pending, which is the
        # same rule Task.status derives in Python. Expressed here as "has
        # assignees, and none of them are pending" so the database can answer it
        # without loading every row.
        has_assignees = exists().where(TaskAssignment.task_id == Task.id)
        pending_exists = exists().where(
            TaskAssignment.task_id == Task.id,
            TaskAssignment.status == TaskStatus.PENDING,
        )
        if filters.assigned_to is not None:
            # Scoped to one person: their own status is what "completed" means
            # to them, not whether the whole task is finished. Without this, a
            # user filtering their completed tasks would see nothing until every
            # other assignee had also finished.
            stmt = stmt.where(
                exists().where(
                    TaskAssignment.task_id == Task.id,
                    TaskAssignment.user_id == filters.assigned_to,
                    TaskAssignment.status == filters.status,
                )
            )
        elif filters.status is TaskStatus.COMPLETED:
            stmt = stmt.where(has_assignees, ~pending_exists)
        else:
            stmt = stmt.where(pending_exists)

    if filters.created_by is not None:
        stmt = stmt.where(Task.created_by == filters.created_by)
    if filters.document_id is not None:
        stmt = stmt.where(Task.document_id == filters.document_id)

    stmt = (
        stmt.order_by(Task.created_at.desc()).offset(filters.offset).limit(filters.limit)
    )
    return list(db.scalars(stmt).unique())


def get_assignment(db: Session, task_id: int, user_id: int) -> TaskAssignment | None:
    return db.scalar(
        select(TaskAssignment)
        .where(TaskAssignment.task_id == task_id, TaskAssignment.user_id == user_id)
        .options(joinedload(TaskAssignment.user))
    )


def update(db: Session, task: Task) -> Task:
    db.commit()
    db.refresh(task)
    return task
