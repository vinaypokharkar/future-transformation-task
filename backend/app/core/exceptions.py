from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base for domain errors. Routers raise these; nothing catches broad
    Exception and reshapes it, so an unexpected error stays a real 500."""


class InvalidCredentialsError(AppError):
    def __init__(self) -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            # Identical for unknown email and wrong password. A specific message
            # ("no such user") would confirm which emails are registered.
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


class NotAuthenticatedError(AppError):
    def __init__(self, detail: str = "Not authenticated") -> None:
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(AppError):
    def __init__(self, detail: str = "Insufficient permissions") -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundError(AppError):
    """Also used for resources that exist but belong to someone else.

    Returning 403 there would confirm the row exists, letting an attacker
    enumerate valid IDs by probing. 404 leaks nothing.
    """

    def __init__(self, detail: str = "Not found") -> None:
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ValidationError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail)


class ConflictError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
