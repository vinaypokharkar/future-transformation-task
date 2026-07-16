"""Model package.

Every model must be imported here. Alembic's autogenerate walks Base.metadata,
and any model not imported by the time env.py runs is silently missing from the
generated migration — producing an empty revision that looks like it worked.
"""

from app.models.activity_log import ActivityAction, ActivityLog
from app.models.document import Document, DocumentChunk, DocumentStatus, FileType
from app.models.role import Role, RoleName
from app.models.task import Task, TaskAssignment, TaskStatus
from app.models.user import User

__all__ = [
    "ActivityAction",
    "ActivityLog",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "FileType",
    "Role",
    "RoleName",
    "Task",
    "TaskAssignment",
    "TaskStatus",
    "User",
]
