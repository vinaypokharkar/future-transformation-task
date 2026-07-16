from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.task import TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    assigned_to: int
    document_id: int | None = None
    due_date: date | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskFilters(BaseModel):
    """Validated filter set for GET /tasks.

    Parsing filters into a schema keeps the repository's query builder free of
    raw request values — nothing reaches SQL without passing a type first.
    """

    status: TaskStatus | None = None
    assigned_to: int | None = None
    created_by: int | None = None
    document_id: int | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    status: TaskStatus
    assigned_to: int
    created_by: int
    document_id: int | None
    due_date: date | None
    created_at: datetime
    updated_at: datetime
