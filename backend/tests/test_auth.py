from app.core.config import settings

LOGIN = f"{settings.api_prefix}/auth/login"
ME = f"{settings.api_prefix}/auth/me"


def test_login_returns_token_and_role(client, admin_user):
    r = client.post(LOGIN, json={"email": admin_user.email, "password": "Secret@123"})
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["user"]["role"] == "admin"


def test_wrong_password_is_401(client, alice):
    r = client.post(LOGIN, json={"email": alice.email, "password": "WrongPassword"})
    assert r.status_code == 401


def test_no_user_enumeration(client, alice):
    """A wrong password and an unknown email must be indistinguishable.

    If they differ in status or body, the endpoint confirms which addresses are
    registered — an account-enumeration oracle. (The service also burns an
    equivalent hash verify on the unknown-email path so the two don't differ in
    timing either; that part isn't asserted here because timing is too flaky to
    gate CI on.)
    """
    # A real, well-formed address that simply isn't registered. Not a .test /
    # .invalid / .example domain — email-validator rejects RFC 2606 special-use
    # domains at the Pydantic layer with a 422, which never reaches the auth
    # service and so wouldn't test anything about enumeration.
    wrong_pw = client.post(LOGIN, json={"email": alice.email, "password": "WrongPassword"})
    no_user = client.post(LOGIN, json={"email": "ghost@nowhere.com", "password": "WrongPassword"})

    assert wrong_pw.status_code == no_user.status_code == 401
    assert wrong_pw.json() == no_user.json()


def test_no_token_is_401(client):
    assert client.get(ME).status_code == 401


def test_malformed_token_is_401(client):
    r = client.get(ME, headers={"Authorization": "Bearer not.a.real.token"})
    assert r.status_code == 401


def test_expired_token_is_401(client, alice):
    """Built with a negative lifetime rather than by waiting."""
    from datetime import UTC, datetime, timedelta

    import jwt

    expired = jwt.encode(
        {
            "sub": str(alice.id),
            "role": "user",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    r = client.get(ME, headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401


def test_login_writes_activity_log(client, db, alice):
    from app.models.activity_log import ActivityAction, ActivityLog

    client.post(LOGIN, json={"email": alice.email, "password": "Secret@123"})

    logs = db.query(ActivityLog).filter(ActivityLog.action == ActivityAction.LOGIN).all()
    assert len(logs) == 1
    assert logs[0].user_id == alice.id
