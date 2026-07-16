import enum
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class Task(Base):
    """A unit of work, assignable to one or many users.

    Note what is NOT here: assignee and status. A task assigned to three people
    has three independent states, so neither belongs on this row — they live on
    task_assignments. The task-level status a client sees is derived from its
    assignments (completed only when every assignee is done) rather than stored,
    because a stored rollup is a second source of truth that drifts the first
    time an assignment changes without it.
    """

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    # Optional link to the knowledge needed to complete the task.
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    creator: Mapped["User"] = relationship(
        back_populates="created_tasks", foreign_keys=[created_by]
    )
    document: Mapped["Document | None"] = relationship(back_populates="tasks")
    assignments: Mapped[list["TaskAssignment"]] = relationship(
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    @property
    def assignee_ids(self) -> list[int]:
        return [a.user_id for a in self.assignments]

    @property
    def completed_count(self) -> int:
        return sum(1 for a in self.assignments if a.status is TaskStatus.COMPLETED)

    @property
    def status(self) -> TaskStatus:
        """Derived: completed only when every assignee has finished.

        An unassigned task is pending — 'all zero assignees are done' is
        technically true and obviously the wrong answer to show a user.
        """
        if not self.assignments:
            return TaskStatus.PENDING
        if all(a.status is TaskStatus.COMPLETED for a in self.assignments):
            return TaskStatus.COMPLETED
        return TaskStatus.PENDING

    def status_for(self, user_id: int) -> TaskStatus | None:
        for a in self.assignments:
            if a.user_id == user_id:
                return a.status
        return None

    def __repr__(self) -> str:
        return f"<Task {self.title} ({len(self.assignments)} assignees)>"


class TaskAssignment(Base):
    """One person's stake in one task, with their own status.

    This is the join table that makes many-to-many assignment possible, but it
    is not a bare join: it carries `status`, because the whole point of
    assigning a task to three people is that each of them completes it
    separately. Alice finishing does not finish it for Bob.
    """

    __tablename__ = "task_assignments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )
    # RESTRICT, like tasks.created_by: deleting a user must not silently erase
    # the record of what they were responsible for.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, values_callable=lambda e: [m.value for m in e]),
        default=TaskStatus.PENDING,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    task: Mapped["Task"] = relationship(back_populates="assignments")
    user: Mapped["User"] = relationship(back_populates="assignments")

    __table_args__ = (
        # Assigning the same person twice is meaningless and would double-count
        # them in every analytic. Enforced by the database, not by hoping the
        # service always de-duplicates.
        UniqueConstraint("task_id", "user_id", name="uq_task_user"),
        # Backs the hot path: /tasks?assigned_to=&status=
        Index("ix_assignment_user_status", "user_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<TaskAssignment task={self.task_id} user={self.user_id} {self.status.value}>"
