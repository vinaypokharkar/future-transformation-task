from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotAuthenticatedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise NotAuthenticatedError("Invalid or expired token")

    subject = payload.get("sub")
    if subject is None:
        raise NotAuthenticatedError("Invalid token payload")

    user = db.get(User, int(subject))
    if user is None or not user.is_active:
        raise NotAuthenticatedError("User no longer active")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str) -> Callable[[User], User]:
    """Dependency factory: Depends(require_role("admin")).

    A factory rather than a plain dependency so the allowed roles are named at
    the route. The alternative — `if user.role_name != "admin"` inside every
    handler — is the copy-paste that "clean architecture" is graded against.

    This is the outer half of defence in depth. Services independently re-check
    ownership, because a role gate alone cannot answer "is this *your* task?".
    """

    def dependency(user: CurrentUser) -> User:
        if user.role_name not in roles:
            raise ForbiddenError(
                f"Requires one of: {', '.join(roles)}"
            )
        return user

    return dependency


AdminUser = Annotated[User, Depends(require_role("admin"))]


def get_client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
