"""many-to-many task assignment with per-assignee status

Revision ID: b2c9f4a17e30
Revises: 6ef5333d4c6f
Create Date: 2026-07-16

Moves assignment off tasks and onto a join table, so one task can be assigned to
many users and each of them tracks their own status.

The data migration is the point. Dropping tasks.assigned_to and tasks.status
without copying them first would silently erase every existing assignment: the
schema would be correct and the data gone. So each existing task becomes exactly
one assignment row carrying its old status, and the downgrade collapses the
other way.
"""

import sqlalchemy as sa
from alembic import op

revision = "b2c9f4a17e30"
down_revision = "6ef5333d4c6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "completed", name="taskstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "user_id", name="uq_task_user"),
    )
    op.create_index(
        "ix_assignment_user_status", "task_assignments", ["user_id", "status"]
    )

    # Carry the existing data across before the old columns disappear.
    op.execute(
        """
        INSERT INTO task_assignments (task_id, user_id, status, created_at, updated_at)
        SELECT id, assigned_to, status, created_at, updated_at
        FROM tasks
        """
    )

    # ix_task_assignee_status is the index backing the assigned_to foreign key,
    # and MySQL refuses to drop an index a constraint depends on. The FK has to
    # go first, and its generated name is not portable, so look it up.
    conn = op.get_bind()
    fk = conn.execute(
        sa.text(
            """
            SELECT CONSTRAINT_NAME
            FROM information_schema.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'tasks'
              AND COLUMN_NAME = 'assigned_to'
              AND REFERENCED_TABLE_NAME = 'users'
            """
        )
    ).scalar()
    if fk:
        op.drop_constraint(fk, "tasks", type_="foreignkey")

    op.drop_index("ix_task_assignee_status", table_name="tasks")
    op.drop_column("tasks", "assigned_to")
    op.drop_column("tasks", "status")


def downgrade() -> None:
    op.add_column("tasks", sa.Column("assigned_to", sa.Integer(), nullable=True))
    op.add_column(
        "tasks",
        sa.Column(
            "status",
            sa.Enum("pending", "completed", name="taskstatus"),
            nullable=False,
            server_default="pending",
        ),
    )

    # Collapse many assignees back to one. This is lossy by nature — the old
    # schema cannot hold more than one — so keep the lowest user_id and mark the
    # task completed only if every assignee had finished, which is the same rule
    # the derived task status uses.
    op.execute(
        """
        UPDATE tasks t
        SET assigned_to = (
            SELECT MIN(a.user_id) FROM task_assignments a WHERE a.task_id = t.id
        ),
        status = CASE
            WHEN EXISTS (
                SELECT 1 FROM task_assignments a
                WHERE a.task_id = t.id AND a.status = 'pending'
            ) THEN 'pending'
            WHEN EXISTS (SELECT 1 FROM task_assignments a WHERE a.task_id = t.id)
                THEN 'completed'
            ELSE 'pending'
        END
        """
    )

    # A task with no assignments has no one to point at, and the column is about
    # to become NOT NULL. Deleting is the only honest option: the old schema
    # cannot represent it.
    op.execute("DELETE FROM tasks WHERE assigned_to IS NULL")

    op.alter_column("tasks", "assigned_to", existing_type=sa.Integer(), nullable=False)
    op.create_foreign_key(
        "tasks_ibfk_assigned_to", "tasks", "users", ["assigned_to"], ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_task_assignee_status", "tasks", ["assigned_to", "status"])

    # No drop_index here. ix_assignment_user_status (user_id, status) is the
    # index backing that table's user_id foreign key, and MySQL refuses to drop
    # an index a constraint still needs:
    #   (1553, "Cannot drop index 'ix_assignment_user_status':
    #           needed in a foreign key constraint")
    # DROP TABLE removes the table's indexes anyway, so the explicit call was
    # both redundant and fatal. Same trap as the initial migration.
    op.drop_table("task_assignments")
