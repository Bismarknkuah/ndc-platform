import pytest

pytestmark = pytest.mark.django_db


def test_authorized_officer_can_issue_directive(
    national_broadcaster_client, national_unit
):
    response = national_broadcaster_client.post(
        "/api/v1/messaging/broadcasts/",
        {
            "title": "Election readiness",
            "body": "All branches must submit readiness reports by Friday.",
            "kind": "DIRECTIVE",
            "target_unit_id": str(national_unit.id),
            "requires_acknowledgement": True,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["kind"] == "DIRECTIVE"


def test_ordinary_member_cannot_issue_directive(auth_client, national_unit):
    response = auth_client.post(
        "/api/v1/messaging/broadcasts/",
        {
            "title": "Election readiness",
            "body": "Body text.",
            "kind": "DIRECTIVE",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 403


def test_broadcast_recipient_sees_it_in_their_feed(
    national_broadcaster_client, auth_client, national_unit, member_user
):
    national_broadcaster_client.post(
        "/api/v1/messaging/broadcasts/",
        {
            "title": "Nationwide announcement",
            "body": "Party congress moved to next month.",
            "kind": "ANNOUNCEMENT",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    )
    response = auth_client.get("/api/v1/messaging/broadcasts/")
    assert response.status_code == 200
    titles = [b["title"] for b in response.json()["results"]]
    assert "Nationwide announcement" in titles


def test_broadcast_recipient_gets_a_notification(
    national_broadcaster_client, auth_client, national_unit
):
    national_broadcaster_client.post(
        "/api/v1/messaging/broadcasts/",
        {
            "title": "Nationwide announcement",
            "body": "Party congress moved to next month.",
            "kind": "ANNOUNCEMENT",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    )
    response = auth_client.get("/api/v1/messaging/notifications/")
    assert response.status_code == 200
    assert any(
        n["notification_type"] == "BROADCAST" for n in response.json()["results"]
    )


def test_recipient_can_acknowledge_directive(
    national_broadcaster_client, auth_client, national_unit
):
    created = national_broadcaster_client.post(
        "/api/v1/messaging/broadcasts/",
        {
            "title": "Mandatory training",
            "body": "All officers must attend.",
            "kind": "DIRECTIVE",
            "target_unit_id": str(national_unit.id),
            "requires_acknowledgement": True,
        },
        format="json",
    ).json()

    ack = auth_client.post(f"/api/v1/messaging/broadcasts/{created['id']}/acknowledge/")
    assert ack.status_code == 201


def test_issuer_can_view_acknowledgement_stats(
    national_broadcaster_client, auth_client, national_unit
):
    created = national_broadcaster_client.post(
        "/api/v1/messaging/broadcasts/",
        {
            "title": "Mandatory training",
            "body": "All officers must attend.",
            "kind": "DIRECTIVE",
            "target_unit_id": str(national_unit.id),
            "requires_acknowledgement": True,
        },
        format="json",
    ).json()
    auth_client.post(f"/api/v1/messaging/broadcasts/{created['id']}/acknowledge/")

    stats = national_broadcaster_client.get(
        f"/api/v1/messaging/broadcasts/{created['id']}/acknowledgements/"
    )
    assert stats.status_code == 200
    body = stats.json()
    assert body["acknowledged_count"] == 1
    assert body["total_recipients"] >= 1


def test_non_issuer_cannot_view_acknowledgement_stats(
    national_broadcaster_client, auth_client, national_unit
):
    created = national_broadcaster_client.post(
        "/api/v1/messaging/broadcasts/",
        {
            "title": "Mandatory training",
            "body": "All officers must attend.",
            "kind": "DIRECTIVE",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    response = auth_client.get(
        f"/api/v1/messaging/broadcasts/{created['id']}/acknowledgements/"
    )
    assert response.status_code == 403


def test_regional_officer_cannot_broadcast_to_national(national_unit, regional_unit):
    """A broadcaster whose own unit is Regional cannot target the National unit (not a descendant)."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Regional Organizer",
        code="regional_organizer_test",
        scope="REGIONAL",
        permissions=["messaging.broadcast.downward"],
    )
    user = User(
        email="regorganizer@example.com",
        phone_number="0244000050",
        first_name="Yaw",
        last_name="Organizer",
        membership_id="NDC-TEST-000050",
        organizational_unit=regional_unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.post(
        "/api/v1/messaging/broadcasts/",
        {
            "title": "Should fail",
            "body": "Trying to broadcast upward.",
            "kind": "ANNOUNCEMENT",
            "target_unit_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 403


def test_regional_officer_can_broadcast_to_own_region(regional_unit):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Regional Organizer",
        code="regional_organizer_test2",
        scope="REGIONAL",
        permissions=["messaging.broadcast.downward"],
    )
    user = User(
        email="regorganizer2@example.com",
        phone_number="0244000051",
        first_name="Yaw",
        last_name="Organizer",
        membership_id="NDC-TEST-000051",
        organizational_unit=regional_unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.post(
        "/api/v1/messaging/broadcasts/",
        {
            "title": "Regional meeting",
            "body": "All constituencies to attend.",
            "kind": "DIRECTIVE",
            "target_unit_id": str(regional_unit.id),
        },
        format="json",
    )
    assert response.status_code == 201
