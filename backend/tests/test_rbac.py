import io

from app.core.config import settings

P = settings.api_prefix


def test_user_cannot_upload(client, alice_headers):
    r = client.post(
        f"{P}/documents",
        headers=alice_headers,
        files={"file": ("x.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert r.status_code == 403


def test_user_cannot_create_task(client, alice_headers, alice):
    r = client.post(
        f"{P}/tasks", headers=alice_headers, json={"title": "x", "assigned_to": alice.id}
    )
    assert r.status_code == 403


def test_user_cannot_read_analytics(client, alice_headers):
    assert client.get(f"{P}/analytics", headers=alice_headers).status_code == 403


def test_user_cannot_list_users(client, alice_headers):
    """A full roster is what credential stuffing wants."""
    assert client.get(f"{P}/users", headers=alice_headers).status_code == 403


def test_admin_can_read_analytics(client, admin_headers):
    assert client.get(f"{P}/analytics", headers=admin_headers).status_code == 200
