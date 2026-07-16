import enum
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, Enum, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActivityAction(str, enum.Enum):
    LOGIN = "login"
    TASK_UPDATE = "task_update"
    DOCUMENT_UPLOAD = "document_upload"
    SEARCH = "search"


class ActivityLog(Base):
    """Audit trail for the four actions the brief mandates.

    This table doubles as the system's observability layer: /analytics reads its
    top-search-queries from `detail`, and a rising rate of zero-result searches
    logged here is the only signal that would reveal a silently broken index.
    """

    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # Nullable and SET NULL: audit history must outlive the user it describes.
    # Deliberately asymmetric with tasks.assigned_to, which uses RESTRICT.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[ActivityAction] = mapped_column(
        Enum(ActivityAction, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # The one genuinely schemaless payload in the schema: {"query": ..., "result_count": ...}
    # for searches, {"from": ..., "to": ...} for task updates. Queried via
    # MySQL's JSON path operator for the analytics top-queries aggregation.
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False, index=True
    )

    user: Mapped["User | None"] = relationship()

    # Supports the analytics aggregations, which all filter by action + time.
    __table_args__ = (Index("ix_log_action_created", "action", "created_at"),)

    def __repr__(self) -> str:
        return f"<ActivityLog {self.action.value} user={self.user_id}>"
