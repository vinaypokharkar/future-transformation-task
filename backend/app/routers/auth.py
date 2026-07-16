from fastapi import APIRouter, Request

from app.core.deps import CurrentUser, DbSession, get_client_ip
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: DbSession) -> TokenResponse:
    return auth_service.authenticate(
        db,
        email=payload.email,
        password=payload.password,
        ip_address=get_client_ip(request),
    )


@router.get("/me", response_model=UserOut)
def me(current_user: CurrentUser) -> UserOut:
    return UserOut.from_user(current_user)
