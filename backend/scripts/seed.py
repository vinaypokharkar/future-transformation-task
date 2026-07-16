"""Seed roles and demo users.

Idempotent: get-or-create throughout, so re-running never raises a duplicate-key
error. A seed script that only works against a virgin database is a seed script
that fails the one time you need it.

Usage (from backend/, venv activated):
    python -m scripts.seed
"""

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.role import Role, RoleName
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("seed")


def get_or_create_role(db: Session, name: str) -> Role:
    role = db.query(Role).filter(Role.name == name).one_or_none()
    if role is None:
        role = Role(name=name)
        db.add(role)
        db.flush()
        logger.info("Created role: %s", name)
    return role


def get_or_create_user(
    db: Session, *, email: str, password: str, full_name: str, role: Role
) -> User:
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role_id=role.id,
            is_active=True,
        )
        db.add(user)
        db.flush()
        logger.info("Created user: %s (%s)", email, role.name)
    else:
        logger.info("User already exists: %s", email)
    return user


def main() -> None:
    with SessionLocal() as db:
        admin_role = get_or_create_role(db, RoleName.ADMIN)
        user_role = get_or_create_role(db, RoleName.USER)

        get_or_create_user(
            db,
            email=settings.seed_admin_email,
            password=settings.seed_admin_password,
            full_name="Admin User",
            role=admin_role,
        )
        get_or_create_user(
            db,
            email="alice@example.com",
            password=settings.seed_user_password,
            full_name="Alice Chen",
            role=user_role,
        )
        get_or_create_user(
            db,
            email="bob@example.com",
            password=settings.seed_user_password,
            full_name="Bob Martin",
            role=user_role,
        )

        db.commit()

    logger.info("")
    logger.info("Seed complete. Credentials:")
    logger.info("  admin: %s / %s", settings.seed_admin_email, settings.seed_admin_password)
    logger.info("  user:  alice@example.com / %s", settings.seed_user_password)
    logger.info("  user:  bob@example.com / %s", settings.seed_user_password)


if __name__ == "__main__":
    main()
