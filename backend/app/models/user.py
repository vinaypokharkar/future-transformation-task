from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # RESTRICT: a role must not vanish while users still reference it.
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    role: Mapped["Role"] = relationship(back_populates="users", lazy="joined")

    # Assignment is many-to-many via task_assignments, so a user reaches their
    # tasks through that table rather than a foreign key on tasks.
    assignments: Mapped[list["TaskAssignment"]] = relationship(back_populates="user")
    created_tasks: Mapped[list["Task"]] = relationship(
        back_populates="creator", foreign_keys="Task.created_by"
    )
    documents: Mapped[list["Document"]] = relationship(back_populates="uploader")

    @property
    def role_name(self) -> str:
        return self.role.name

    def __repr__(self) -> str:
        return f"<User {self.email}>"
