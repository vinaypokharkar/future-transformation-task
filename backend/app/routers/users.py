from fastapi import APIRouter

from app.core.deps import AdminUser, DbSession
from app.repositories import user_repo
from app.schemas.auth import UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: DbSession, admin: AdminUser) -> list[UserOut]:
    """Admin-only: populates the assignee picker when creating a task.

    Admin-gated because a full user roster is exactly the list an attacker
    wants for credential stuffing.
    """
    return [UserOut.from_user(u) for u in user_repo.list_all(db)]
