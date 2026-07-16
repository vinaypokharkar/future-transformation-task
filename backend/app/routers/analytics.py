from fastapi import APIRouter

from app.core.deps import AdminUser, DbSession
from app.schemas.analytics import AnalyticsOut
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsOut)
def get_analytics(db: DbSession, admin: AdminUser) -> AnalyticsOut:
    return analytics_service.get_analytics(db)
