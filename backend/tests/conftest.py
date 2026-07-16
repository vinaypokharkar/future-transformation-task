"""Test fixtures.

Tests run against the throwaway MySQL on :3307, never SQLite. SQLite cannot
parse `detail->>'$.query'` (analytics), does not enforce ENUM, and has foreign
keys off by default — so the analytics, cascade, and JSON tests would pass
locally while proving nothing about the database this app actually runs on.

Start it with: docker compose up -d mysql_test
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("FAISS_INDEX_PATH", "data/test_faiss.index")
# JWT_SECRET_KEY has no default and is validated, so the suite must supply one
# before app.core.config is imported. setdefault, not assignment: a real .env
# still wins. This value only ever signs tokens inside the test process.
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-only-secret-not-used-outside-pytest-0123456789abcdef"
)

from app.core.config import settings  # noqa: E402
from app.core.deps import get_db  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.activity_log import ActivityLog  # noqa: E402
from app.models.document import Document, DocumentChunk, DocumentStatus, FileType  # noqa: E402
from app.models.role import Role, RoleName  # noqa: E402
from app.models.task import Task, TaskStatus  # noqa: E402
from app.models.user import User  # noqa: E402

engine = create_engine(settings.test_database_url, pool_pre_ping=True)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def _schema():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"Test MySQL unavailable on :3307 ({exc}). Run: docker compose up -d mysql_test")

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    """A session per test, with every table truncated first.

    Truncation order respects the foreign keys rather than disabling them —
    the constraints are part of what these tests exercise.

    ActivityLog must be cleared explicitly and first. Its FK to users is
    SET NULL by design (audit history outlives the user it describes), so
    deleting users leaves orphaned log rows behind rather than cascading them
    away — and those rows then leak into the next test's log assertions.
    """
    with TestSession() as session:
        for model in (ActivityLog, DocumentChunk, Task, Document, User, Role):
            session.query(model).delete()
        session.commit()
        yield session


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def roles(db):
    admin = Role(name=RoleName.ADMIN)
    user = Role(name=RoleName.USER)
    db.add_all([admin, user])
    db.commit()
    return {"admin": admin, "user": user}


def _make_user(db, roles, email, role_key):
    u = User(
        email=email,
        hashed_password=hash_password("Secret@123"),
        full_name=email.split("@")[0],
        role_id=roles[role_key].id,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


@pytest.fixture
def admin_user(db, roles):
    return _make_user(db, roles, f"admin-{uuid.uuid4().hex[:6]}@test.com", "admin")


@pytest.fixture
def alice(db, roles):
    return _make_user(db, roles, f"alice-{uuid.uuid4().hex[:6]}@test.com", "user")


@pytest.fixture
def bob(db, roles):
    return _make_user(db, roles, f"bob-{uuid.uuid4().hex[:6]}@test.com", "user")


def auth_header(client, email):
    r = client.post(
        f"{settings.api_prefix}/auth/login",
        json={"email": email, "password": "Secret@123"},
    )
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_headers(client, admin_user):
    return auth_header(client, admin_user.email)


@pytest.fixture
def alice_headers(client, alice):
    return auth_header(client, alice.email)


@pytest.fixture
def make_task(db):
    def _make(*, assigned_to, created_by, title="Task", status=TaskStatus.PENDING):
        t = Task(
            title=title, status=status, assigned_to=assigned_to, created_by=created_by
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return t

    return _make


@pytest.fixture
def indexed_document(db, admin_user):
    """A document with chunks in MySQL and matching vectors in FAISS."""
    from app.services.ai.embedder import embed_texts
    from app.services.ai.vector_store import get_vector_store

    doc = Document(
        title="Expenses Policy",
        filename="expenses.txt",
        original_filename="expenses.txt",
        file_type=FileType.TXT,
        file_size=100,
        storage_path="uploads/expenses.txt",
        uploaded_by=admin_user.id,
        status=DocumentStatus.INDEXED,
    )
    db.add(doc)
    db.flush()

    contents = [
        "Employees may request reimbursement within 30 days of purchase. "
        "Receipts must be attached to every request.",
        "Hotel stays are capped at 180 GBP per night in London and 120 GBP "
        "elsewhere in the United Kingdom.",
    ]
    chunks = [
        DocumentChunk(document_id=doc.id, chunk_index=i, content=c, token_count=len(c.split()))
        for i, c in enumerate(contents)
    ]
    db.add_all(chunks)
    db.flush()

    doc.chunk_count = len(chunks)
    db.commit()

    store = get_vector_store()
    store.reset()
    store.add(embed_texts(contents), [c.id for c in chunks])

    yield doc

    store.reset()
