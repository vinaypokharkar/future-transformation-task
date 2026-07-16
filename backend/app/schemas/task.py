from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    # A list, because a task can be assigned to many people. min_length=1: an
    # unassigned task has nobody to complete it, and its derived status would be
    # permanently pending.
    assignee_ids: list[int] = Field(min_length=1)
    document_id: int | None = None
    due_date: date | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus
    # Admin-only override, to mark someone else's assignment. Ignored for
    # non-admins, who may only ever change their own.
    user_id: int | None = None


class TaskFilters(BaseModel):
    """Validated filter set for GET /tasks."""

    status: TaskStatus | None = None
    assigned_to: int | None = None
    created_by: int | None = None
    document_id: int | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class AssigneeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    email: str
    full_name: str | None
    status: TaskStatus


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    created_by: int
    document_id: int | None
    due_date: date | None
    created_at: datetime
    updated_at: datetime

    assignees: list[AssigneeOut]
    # Derived, never stored: completed only when every assignee is done. A
    # stored rollup would be a second source of truth and drift the first time
    # an assignment changed without it.
    status: TaskStatus
    assignee_count: int
    completed_count: int
    # This caller's own status, or null if they are not assigned. Saves the
    # frontend from searching `assignees` for itself on every render.
    my_status: TaskStatus | None = None

    @classmethod
    def from_task(cls, task, current_user_id: int | None = None) -> "TaskOut":
        return cls(
            id=task.id,
            title=task.title,
            description=task.description,
            created_by=task.created_by,
            document_id=task.document_id,
            due_date=task.due_date,
            created_at=task.created_at,
            updated_at=task.updated_at,
            assignees=[
                AssigneeOut(
                    user_id=a.user_id,
                    email=a.user.email,
                    full_name=a.user.full_name,
                    status=a.status,
                )
                for a in task.assignments
            ],
            status=task.status,
            assignee_count=len(task.assignments),
            completed_count=task.completed_count,
            my_status=task.status_for(current_user_id) if current_user_id else None,
        )
