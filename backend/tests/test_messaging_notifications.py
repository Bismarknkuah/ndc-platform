import pytest

pytestmark = pytest.mark.django_db


def test_unread_count_increments_and_mark_read_decrements(
    auth_client, chairman_client, national_chairman_user
):
    auth_client.post(
        "/api/v1/messaging/direct-messages/",
        {"recipient_id": str(national_chairman_user.id), "body": "Ping."},
        format="json",
    )
    count_response = chairman_client.get(
        "/api/v1/messaging/notifications/unread-count/"
    )
    assert count_response.json()["unread_count"] == 1

    notification_id = chairman_client.get("/api/v1/messaging/notifications/").json()[
        "results"
    ][0]["id"]
    mark = chairman_client.post(
        f"/api/v1/messaging/notifications/{notification_id}/read/"
    )
    assert mark.status_code == 200
    assert mark.json()["is_read"] is True

    count_after = chairman_client.get("/api/v1/messaging/notifications/unread-count/")
    assert count_after.json()["unread_count"] == 0


def test_mark_all_read(auth_client, chairman_client, national_chairman_user):
    for i in range(3):
        auth_client.post(
            "/api/v1/messaging/direct-messages/",
            {"recipient_id": str(national_chairman_user.id), "body": f"Message {i}"},
            format="json",
        )
    assert (
        chairman_client.get("/api/v1/messaging/notifications/unread-count/").json()[
            "unread_count"
        ]
        == 3
    )

    response = chairman_client.post("/api/v1/messaging/notifications/mark-all-read/")
    assert response.status_code == 200
    assert response.json()["marked_read"] == 3
    assert (
        chairman_client.get("/api/v1/messaging/notifications/unread-count/").json()[
            "unread_count"
        ]
        == 0
    )


def test_unread_filter(auth_client, chairman_client, national_chairman_user):
    auth_client.post(
        "/api/v1/messaging/direct-messages/",
        {"recipient_id": str(national_chairman_user.id), "body": "Unread one."},
        format="json",
    )
    chairman_client.post("/api/v1/messaging/notifications/mark-all-read/")
    auth_client.post(
        "/api/v1/messaging/direct-messages/",
        {"recipient_id": str(national_chairman_user.id), "body": "Unread two."},
        format="json",
    )
    response = chairman_client.get("/api/v1/messaging/notifications/?unread=true")
    assert response.json()["count"] == 1


def test_cannot_mark_someone_elses_notification_read(
    auth_client, chairman_client, national_chairman_user
):
    auth_client.post(
        "/api/v1/messaging/direct-messages/",
        {"recipient_id": str(national_chairman_user.id), "body": "Not for you."},
        format="json",
    )
    chairman_notification_id = chairman_client.get(
        "/api/v1/messaging/notifications/"
    ).json()["results"][0]["id"]
    response = auth_client.post(
        f"/api/v1/messaging/notifications/{chairman_notification_id}/read/"
    )
    assert response.status_code == 404
