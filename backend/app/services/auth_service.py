from sqlalchemy.orm import Session

from app.core.exceptions import InvalidCredentialsError
from app.core.security import (
    create_access_token,
    verify_password,
    verify_password_dummy,
)
from app.models.activity_log import ActivityAction
from app.models.user import User
from app.repositories import user_repo
from app.schemas.auth import TokenResponse, UserOut
from app.services import activity_service


def authenticate(
    db: Session, email: str, password: str, ip_address: str | None = None
) -> TokenResponse:
    user = user_repo.get_by_email(db, email)

    if user is None:
        # Burn an equivalent verify before failing. Returning early here would
        # make "unknown email" measurably faster than "wrong password", turning
        # response time into an oracle for which emails are registered.
        verify_password_dummy()
        raise InvalidCredentialsError

    if not verify_password(password, user.hashed_password):
        raise InvalidCredentialsError

    if not user.is_active:
        raise InvalidCredentialsError

    activity_service.log(
        db,
        user_id=user.id,
        action=ActivityAction.LOGIN,
        entity_type="user",
        entity_id=user.id,
        ip_address=ip_address,
    )

    token = create_access_token(subject=user.id, role=user.role_name)
    return TokenResponse(access_token=token, user=UserOut.from_user(user))
