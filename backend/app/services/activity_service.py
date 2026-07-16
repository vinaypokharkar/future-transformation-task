import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityAction, ActivityLog

logger = logging.getLogger(__name__)


def log(
    db: Session,
    *,
    user_id: int | None,
    action: ActivityAction,
    entity_type: str | None = None,
    entity_id: int | None = None,
    detail: dict[str, Any] | None = None,
    ip_address: str | None = None,
    commit: bool = True,
) -> ActivityLog:
    """Record one audited action.

    Single writer for the whole audit trail — the four call sites (login, upload,
    task update, search) all route through here rather than inserting inline, so
    the table cannot drift into inconsistent shapes.

    Logging never breaks the action it describes: a failure here is swallowed and
    reported to stderr. An audit gap is bad; a failed upload because its log row
    could not be written is worse.
    """
    entry = ActivityLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        ip_address=ip_address,
    )
    try:
        db.add(entry)
        if commit:
            db.commit()
    except Exception:
        logger.exception("Failed to write activity log for action=%s", action.value)
        db.rollback()
    return entry
