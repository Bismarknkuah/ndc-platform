import pytest

pytestmark = pytest.mark.django_db


def test_send_direct_message(auth_client, national_chairman_user):
    response = auth_client.post(
        "/api/v1/messaging/direct-messages/",
        {
            "recipient_id": str(national_chairman_user.id),
            "body": "Please review the draft.",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["recipient"]["id"] == str(national_chairman_user.id)


def test_cannot_message_self(auth_client, member_user):
    response = auth_client.post(
        "/api/v1/messaging/direct-messages/",
        {"recipient_id": str(member_user.id), "body": "Talking to myself."},
        format="json",
    )
    assert response.status_code == 400


def test_recipient_gets_notified(auth_client, chairman_client, national_chairman_user):
    auth_client.post(
        "/api/v1/messaging/direct-messages/",
        {"recipient_id": str(national_chairman_user.id), "body": "Hello chairman."},
        format="json",
    )
    response = chairman_client.get("/api/v1/messaging/notifications/")
    assert any(
        n["notification_type"] == "DIRECT_MESSAGE" for n in response.json()["results"]
    )


def test_conversation_filter_returns_only_that_thread(
    auth_client, chairman_client, member_user, national_chairman_user
):
    auth_client.post(
        "/api/v1/messaging/direct-messages/",
        {"recipient_id": str(national_chairman_user.id), "body": "Message one."},
        format="json",
    )
    response = auth_client.get(
        f"/api/v1/messaging/direct-messages/?with={national_chairman_user.id}"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_only_recipient_can_mark_read(
    auth_client, chairman_client, national_chairman_user
):
    created = auth_client.post(
        "/api/v1/messaging/direct-messages/",
        {"recipient_id": str(national_chairman_user.id), "body": "Please confirm."},
        format="json",
    ).json()

    denied = auth_client.post(
        f"/api/v1/messaging/direct-messages/{created['id']}/read/"
    )
    assert denied.status_code == 403

    allowed = chairman_client.post(
        f"/api/v1/messaging/direct-messages/{created['id']}/read/"
    )
    assert allowed.status_code == 200
    assert allowed.json()["read_at"] is not None
