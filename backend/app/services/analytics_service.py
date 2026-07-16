from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityAction, ActivityLog
from app.models.document import Document, DocumentChunk, DocumentStatus
from app.models.task import Task, TaskStatus
from app.schemas.analytics import (
    ActivityAnalytics,
    AnalyticsOut,
    DocumentAnalytics,
    SearchAnalytics,
    TaskAnalytics,
    TopQuery,
)


def get_analytics(db: Session) -> AnalyticsOut:
    return AnalyticsOut(
        tasks=_task_analytics(db),
        documents=_document_analytics(db),
        search=_search_analytics(db),
        activity=_activity_analytics(db),
    )


def _task_analytics(db: Session) -> TaskAnalytics:
    # One grouped query rather than three counts.
    rows = db.execute(
        select(Task.status, func.count()).group_by(Task.status)
    ).all()
    counts = {status: count for status, count in rows}

    completed = counts.get(TaskStatus.COMPLETED, 0)
    pending = counts.get(TaskStatus.PENDING, 0)
    total = completed + pending

    return TaskAnalytics(
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
