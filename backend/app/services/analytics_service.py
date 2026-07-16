from datetime import UTC, datetime, timedelta

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityAction, ActivityLog
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.task import Task, TaskAssignment, TaskStatus
from app.schemas.analytics import (
    ActivityAnalytics,
    AnalyticsOut,
    AssignmentAnalytics,
    DocumentAnalytics,
    SearchAnalytics,
    TaskAnalytics,
    TopQuery,
)


def get_analytics(db: Session) -> AnalyticsOut:
    return AnalyticsOut(
        tasks=_task_analytics(db),
        assignments=_assignment_analytics(db),
        documents=_document_analytics(db),
        search=_search_analytics(db),
        activity=_activity_analytics(db),
    )


def _task_analytics(db: Session) -> TaskAnalytics:
    """Task-level counts: a task is completed only when every assignee is done.

    With per-assignee status, "completed vs pending" has two honest answers and
    they are not interchangeable. A task assigned to three people with one
    finished is 1/3 done as work, but 0/1 done as a task. Reporting only one
    number would misrepresent the other, so both are returned: this function
    counts tasks, _assignment_analytics counts the work inside them.

    Status is derived rather than stored, so it is computed here in SQL with the
    same rule Task.status uses in Python: completed means the task has
    assignees and none of them are still pending.
    """
    total = db.scalar(select(func.count()).select_from(Task)) or 0

    has_assignees = exists().where(TaskAssignment.task_id == Task.id)
    pending_exists = exists().where(
        TaskAssignment.task_id == Task.id,
        TaskAssignment.status == TaskStatus.PENDING,
    )
    completed = (
        db.scalar(
            select(func.count())
            .select_from(Task)
            .where(has_assignees, ~pending_exists)
        )
        or 0
    )

    return TaskAnalytics(
        total=total,
        completed=completed,
        pending=total - completed,
        completion_rate=round(completed / total, 4) if total else 0.0,
    )


def _assignment_analytics(db: Session) -> AssignmentAnalytics:
    """Per-person counts: how much of the assigned work is actually done.

    The task-level view hides progress. Three people assigned, two finished, is
    "0 tasks completed" — true, and useless for telling whether the work is
    moving.
    """
    rows = db.execute(
        select(TaskAssignment.status, func.count()).group_by(TaskAssignment.status)
    ).all()
    counts = {status: count for status, count in rows}

    completed = counts.get(TaskStatus.COMPLETED, 0)
    pending = counts.get(TaskStatus.PENDING, 0)
    total = completed + pending

    return AssignmentAnalytics(
        total=total,
        completed=completed,
        pending=pending,
        completion_rate=round(completed / total, 4) if total else 0.0,
    )


def _document_analytics(db: Session) -> DocumentAnalytics:
    total = db.scalar(select(func.count()).select_from(Document)) or 0
    indexed = (
        db.scalar(
            select(func.count())
            .select_from(Document)
            .where(Document.status == DocumentStatus.INDEXED)
        )
        or 0
    )
    total_chunks = db.scalar(select(func.count()).select_from(DocumentChunk)) or 0
    return DocumentAnalytics(total=total, indexed=indexed, total_chunks=total_chunks)


def _search_analytics(db: Session) -> SearchAnalytics:
    """Most-searched queries, read out of the activity log's JSON payload.

    This is why activity_logs.detail is a JSON column and why searches record
    their query there: the audit trail the brief mandates doubles as the source
    for this analytic. MySQL's ->> operator unquotes the extracted scalar, so
    the value groups as a plain string.
    """
    total_searches = (
        db.scalar(
            select(func.count())
            .select_from(ActivityLog)
            .where(ActivityLog.action == ActivityAction.SEARCH)
        )
        or 0
    )

    query_expr = ActivityLog.detail["query"].as_string()
    rows = db.execute(
        select(query_expr.label("query"), func.count().label("count"))
        .where(ActivityLog.action == ActivityAction.SEARCH)
        .where(query_expr.is_not(None))
        .group_by(query_expr)
        .order_by(func.count().desc())
        .limit(5)
    ).all()

    return SearchAnalytics(
        total_searches=total_searches,
        top_queries=[TopQuery(query=q, count=c) for q, c in rows],
    )


def _activity_analytics(db: Session) -> ActivityAnalytics:
    since = datetime.now(UTC) - timedelta(days=7)
    logins = (
        db.scalar(
            select(func.count())
            .select_from(ActivityLog)
            .where(ActivityLog.action == ActivityAction.LOGIN)
            .where(ActivityLog.created_at >= since)
        )
        or 0
    )
    return ActivityAnalytics(logins_last_7_days=logins)
