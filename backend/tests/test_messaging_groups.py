import pytest

pytestmark = pytest.mark.django_db


def test_create_group_auto_adds_creator(auth_client, member_user):
    response = auth_client.post(
        "/api/v1/messaging/groups/",
        {"name": "Comms Strategy", "description": "Planning."},
        format="json",
    )
    assert response.status_code == 201
    member_ids = [m["id"] for m in response.json()["members"]]
    assert str(member_user.id) in member_ids


def test_creator_can_add_member(auth_client, national_chairman_user):
    group = auth_client.post(
        "/api/v1/messaging/groups/", {"name": "Comms Strategy"}, format="json"
    ).json()
    response = auth_client.post(
        f"/api/v1/messaging/groups/{group['id']}/members/",
        {"user_id": str(national_chairman_user.id)},
    )
    assert response.status_code == 200
    member_ids = [m["id"] for m in response.json()["members"]]
    assert str(national_chairman_user.id) in member_ids


def test_non_creator_cannot_add_member(
    auth_client, national_chairman_user, chairman_client
):
    group = auth_client.post(
        "/api/v1/messaging/groups/", {"name": "Comms Strategy"}, format="json"
    ).json()
    response = chairman_client.post(
        f"/api/v1/messaging/groups/{group['id']}/members/",
        {"user_id": str(national_chairman_user.id)},
    )
    assert response.status_code == 403


def test_member_can_post_and_read_messages(auth_client):
    group = auth_client.post(
        "/api/v1/messaging/groups/", {"name": "Comms Strategy"}, format="json"
    ).json()
    post = auth_client.post(
        f"/api/v1/messaging/groups/{group['id']}/messages/",
        {"body": "Let's align on messaging."},
        format="json",
    )
    assert post.status_code == 201

    listing = auth_client.get(f"/api/v1/messaging/groups/{group['id']}/messages/")
    assert listing.status_code == 200
    assert listing.json()["count"] == 1


def test_non_member_cannot_post_message(auth_client, chairman_client):
    group = auth_client.post(
        "/api/v1/messaging/groups/", {"name": "Comms Strategy"}, format="json"
    ).json()
    response = chairman_client.post(
        f"/api/v1/messaging/groups/{group['id']}/messages/",
        {"body": "Sneaking in."},
        format="json",
    )
    assert response.status_code == 403


def test_group_message_notifies_other_members(
    auth_client, chairman_client, national_chairman_user
):
    group = auth_client.post(
        "/api/v1/messaging/groups/", {"name": "Comms Strategy"}, format="json"
    ).json()
    auth_client.post(
        f"/api/v1/messaging/groups/{group['id']}/members/",
        {"user_id": str(national_chairman_user.id)},
    )
    auth_client.post(
        f"/api/v1/messaging/groups/{group['id']}/messages/",
        {"body": "Update for the team."},
        format="json",
    )

    notifications = chairman_client.get("/api/v1/messaging/notifications/")
    assert any(
        n["notification_type"] == "GROUP_MESSAGE"
        for n in notifications.json()["results"]
    )


def test_creator_can_remove_member(auth_client, national_chairman_user):
    group = auth_client.post(
        "/api/v1/messaging/groups/", {"name": "Comms Strategy"}, format="json"
    ).json()
    auth_client.post(
        f"/api/v1/messaging/groups/{group['id']}/members/",
        {"user_id": str(national_chairman_user.id)},
    )
    response = auth_client.delete(
        f"/api/v1/messaging/groups/{group['id']}/members/",
        {"user_id": str(national_chairman_user.id)},
        format="json",
    )
    assert response.status_code == 200
    member_ids = [m["id"] for m in response.json()["members"]]
    assert str(national_chairman_user.id) not in member_ids
