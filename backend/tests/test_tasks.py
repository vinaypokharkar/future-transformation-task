from app.core.config import settings
from app.models.task import TaskStatus

P = settings.api_prefix


def test_user_cannot_see_others_tasks(client, alice_headers, alice, bob, admin_user, make_task):
    """The scoping test a reviewer will actually try.

    Alice asks for Bob's tasks by ID. The service overwrites assigned_to with
    her own ID, so she gets her own list back — not a 403, because the request
    is legitimate; its scope simply isn't hers to choose.
    """
    make_task(assigned_to=alice.id, created_by=admin_user.id, title="Alice's")
    make_task(assigned_to=bob.id, created_by=admin_user.id, title="Bob's")

    r = client.get(f"{P}/tasks?assigned_to={bob.id}", headers=alice_headers)
    assert r.status_code == 200

    tasks = r.json()
    assert len(tasks) == 1
    assert all(t["assigned_to"] == alice.id for t in tasks)
    assert all(t["title"] != "Bob's" for t in tasks)


def test_reading_others_task_is_404_not_403(client, alice_headers, bob, admin_user, make_task):
    """403 would confirm the row exists, letting an attacker map IDs by probing."""
    bobs = make_task(assigned_to=bob.id, created_by=admin_user.id)
    assert client.get(f"{P}/tasks/{bobs.id}", headers=alice_headers).status_code == 404


def test_patching_others_task_is_404(client, alice_headers, bob, admin_user, make_task):
    bobs = make_task(assigned_to=bob.id, created_by=admin_user.id)
    r = client.patch(
        f"{P}/tasks/{bobs.id}/status", headers=alice_headers, json={"status": "completed"}
    )
    assert r.status_code == 404


def test_assignee_can_complete_own_task(client, alice_headers, alice, admin_user, make_task):
    t = make_task(assigned_to=alice.id, created_by=admin_user.id)
    r = client.patch(
        f"{P}/tasks/{t.id}/status", headers=alice_headers, json={"status": "completed"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


def test_filter_composition(client, admin_headers, alice, bob, admin_user, make_task):
    """Each filter alone, and both together."""
    make_task(assigned_to=alice.id, created_by=admin_user.id, status=TaskStatus.COMPLETED)
    make_task(assigned_to=alice.id, created_by=admin_user.id, status=TaskStatus.PENDING)
    make_task(assigned_to=bob.id, created_by=admin_user.id, status=TaskStatus.COMPLETED)

    def ids(url):
        r = client.get(url, headers=admin_headers)
        assert r.status_code == 200
        return r.json()

    assert len(ids(f"{P}/tasks")) == 3
    assert len(ids(f"{P}/tasks?status=completed")) == 2
    assert len(ids(f"{P}/tasks?status=pending")) == 1
    assert len(ids(f"{P}/tasks?assigned_to={alice.id}")) == 2
    # Composed: only Alice's completed one.
    both = ids(f"{P}/tasks?status=completed&assigned_to={alice.id}")
    assert len(both) == 1
    assert both[0]["assigned_to"] == alice.id
    assert both[0]["status"] == "completed"


def test_status_change_writes_activity_log(client, db, alice_headers, alice, admin_user, make_task):
    from app.models.activity_log import ActivityAction, ActivityLog

    t = make_task(assigned_to=alice.id, created_by=admin_user.id)
    client.patch(f"{P}/tasks/{t.id}/status", headers=alice_headers, json={"status": "completed"})

    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.action == ActivityAction.TASK_UPDATE, ActivityLog.entity_id == t.id)
        .all()
    )
    assert len(logs) == 1
    assert logs[0].detail["from"] == "pending"
    assert logs[0].detail["to"] == "completed"
