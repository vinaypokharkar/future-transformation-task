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
    assert tasks[0]["title"] == "Alice's"
    assert all(alice.id in [a["user_id"] for a in t["assignees"]] for t in tasks)


def test_shared_task_is_visible_to_every_assignee(
    client, alice_headers, alice, bob, admin_user, make_task
):
    """A task on both of them shows up for both, without leaking the other's."""
    make_task(assigned_to=[alice.id, bob.id], created_by=admin_user.id, title="Shared")
    make_task(assigned_to=bob.id, created_by=admin_user.id, title="Bob only")

    tasks = client.get(f"{P}/tasks", headers=alice_headers).json()
    titles = {t["title"] for t in tasks}
    assert titles == {"Shared"}, "Alice should see the shared task and nothing else"

    shared = tasks[0]
    assert shared["assignee_count"] == 2
    assert {a["user_id"] for a in shared["assignees"]} == {alice.id, bob.id}


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
    body = r.json()
    assert body["my_status"] == "completed"
    assert body["status"] == "completed"  # sole assignee, so the task is done


def test_completing_one_assignee_does_not_complete_the_task(
    client, alice_headers, alice, bob, admin_user, make_task
):
    """The whole point of per-assignee status.

    Alice finishing must not finish it for Bob, and the task itself is only
    done when nobody is still pending.
    """
    t = make_task(assigned_to=[alice.id, bob.id], created_by=admin_user.id)

    r = client.patch(
        f"{P}/tasks/{t.id}/status", headers=alice_headers, json={"status": "completed"}
    )
    assert r.status_code == 200
    body = r.json()

    assert body["my_status"] == "completed"
    assert body["completed_count"] == 1
    assert body["assignee_count"] == 2
    assert body["status"] == "pending", "task must stay pending while Bob has not finished"

    bobs = next(a for a in body["assignees"] if a["user_id"] == bob.id)
    assert bobs["status"] == "pending", "Alice's update must not touch Bob's row"


def test_task_completes_when_every_assignee_finishes(
    client, alice_headers, alice, bob, admin_user, make_task
):
    t = make_task(
        assigned_to=[alice.id, bob.id],
        created_by=admin_user.id,
        statuses={bob.id: TaskStatus.COMPLETED},
    )
    r = client.patch(
        f"{P}/tasks/{t.id}/status", headers=alice_headers, json={"status": "completed"}
    )
    body = r.json()
    assert body["completed_count"] == 2
    assert body["status"] == "completed"


def test_admin_can_update_another_users_assignment(
    client, admin_headers, alice, bob, admin_user, make_task
):
    """An admin who is not on the task can still correct it, by naming the user."""
    t = make_task(assigned_to=[alice.id, bob.id], created_by=admin_user.id)

    r = client.patch(
        f"{P}/tasks/{t.id}/status",
        headers=admin_headers,
        json={"status": "completed", "user_id": alice.id},
    )
    assert r.status_code == 200
    alices = next(a for a in r.json()["assignees"] if a["user_id"] == alice.id)
    assert alices["status"] == "completed"


def test_user_cannot_update_another_assignees_status(
    client, alice_headers, alice, bob, admin_user, make_task
):
    """Being on the same task does not make Bob's row Alice's to change."""
    t = make_task(assigned_to=[alice.id, bob.id], created_by=admin_user.id)

    r = client.patch(
        f"{P}/tasks/{t.id}/status",
        headers=alice_headers,
        json={"status": "completed", "user_id": bob.id},
    )
    assert r.status_code == 404

    # And Bob's row is untouched — the request must not have silently been
    # applied to Alice instead.
    fresh = client.get(f"{P}/tasks/{t.id}", headers=alice_headers).json()
    assert all(a["status"] == "pending" for a in fresh["assignees"])


def test_admin_creates_task_for_multiple_users(client, admin_headers, alice, bob):
    r = client.post(
        f"{P}/tasks",
        headers=admin_headers,
        json={"title": "Read the security policy", "assignee_ids": [alice.id, bob.id]},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["assignee_count"] == 2
    assert body["status"] == "pending"


def test_duplicate_assignees_are_deduplicated(client, admin_headers, alice):
    """Assigning the same person twice would double-count them everywhere."""
    r = client.post(
        f"{P}/tasks",
        headers=admin_headers,
        json={"title": "Dupe", "assignee_ids": [alice.id, alice.id, alice.id]},
    )
    assert r.status_code == 201
    assert r.json()["assignee_count"] == 1


def test_task_requires_at_least_one_assignee(client, admin_headers):
    """An unassigned task has nobody to complete it and is permanently pending."""
    r = client.post(f"{P}/tasks", headers=admin_headers, json={"title": "Nobody", "assignee_ids": []})
    assert r.status_code == 422


def test_unknown_assignee_rejected(client, admin_headers, alice):
    r = client.post(
        f"{P}/tasks",
        headers=admin_headers,
        json={"title": "Ghost", "assignee_ids": [alice.id, 999999]},
    )
    assert r.status_code == 422
    assert "999999" in r.json()["detail"]


def test_filter_composition(client, admin_headers, alice, bob, admin_user, make_task):
    """Each filter alone, and both together.

    Task-level status means completed only when every assignee is done, so the
    two-assignee task below is pending despite Alice having finished it.
    """
    make_task(assigned_to=alice.id, created_by=admin_user.id, status=TaskStatus.COMPLETED)
    make_task(assigned_to=alice.id, created_by=admin_user.id, status=TaskStatus.PENDING)
    make_task(assigned_to=bob.id, created_by=admin_user.id, status=TaskStatus.COMPLETED)
    make_task(
        assigned_to=[alice.id, bob.id],
        created_by=admin_user.id,
        statuses={alice.id: TaskStatus.COMPLETED, bob.id: TaskStatus.PENDING},
    )

    def get(url):
        r = client.get(url, headers=admin_headers)
        assert r.status_code == 200, r.text
        return r.json()

    assert len(get(f"{P}/tasks")) == 4
    # Two fully-done tasks; the shared one is not, because Bob is still pending.
    assert len(get(f"{P}/tasks?status=completed")) == 2
    assert len(get(f"{P}/tasks?status=pending")) == 2
    # Alice is on three of them.
    assert len(get(f"{P}/tasks?assigned_to={alice.id}")) == 3

    # Composed and scoped: "Alice's completed" means the ones *she* finished,
    # including the shared task Bob has not.
    both = get(f"{P}/tasks?status=completed&assigned_to={alice.id}")
    assert len(both) == 2
    for t in both:
        alices = next(a for a in t["assignees"] if a["user_id"] == alice.id)
        assert alices["status"] == "completed"


def test_pagination_not_multiplied_by_assignees(client, admin_headers, alice, bob, admin_user, make_task):
    """A many-to-many JOIN would return a task once per assignee.

    Three tasks, each on two people, would come back as six rows — and LIMIT
    would then count duplicates rather than tasks, silently short-paging.
    """
    for i in range(3):
        make_task(assigned_to=[alice.id, bob.id], created_by=admin_user.id, title=f"T{i}")

    tasks = client.get(f"{P}/tasks?limit=3", headers=admin_headers).json()
    assert len(tasks) == 3
    assert len({t["id"] for t in tasks}) == 3, "duplicate tasks in the page"


def test_status_change_writes_activity_log(client, db, alice_headers, alice, bob, admin_user, make_task):
    from app.models.activity_log import ActivityAction, ActivityLog

    t = make_task(assigned_to=[alice.id, bob.id], created_by=admin_user.id)
    client.patch(f"{P}/tasks/{t.id}/status", headers=alice_headers, json={"status": "completed"})

    logs = (
        db.query(ActivityLog)
        .filter(ActivityLog.action == ActivityAction.TASK_UPDATE, ActivityLog.entity_id == t.id)
        .all()
    )
    assert len(logs) == 1
    detail = logs[0].detail
    assert detail["from"] == "pending"
    assert detail["to"] == "completed"
    assert detail["assignee_id"] == alice.id
    # The rollup answers "when did the task actually finish?" without replaying
    # every assignment row.
    assert detail["task_status"] == "pending"
