import datetime

import pytest

pytestmark = pytest.mark.django_db


def _window():
    start = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat() + "Z"
    return start, end


def test_authorized_officer_can_create_campaign(chairman_client, national_unit):
    start, end = _window()
    response = chairman_client.post(
        "/api/v1/events/campaigns/",
        {
            "title": "2028 GOTV Drive",
            "goal_description": "Register 1M new voters",
            "target_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "PLANNING"


def test_ordinary_member_cannot_create_campaign(auth_client, national_unit):
    start, end = _window()
    response = auth_client.post(
        "/api/v1/events/campaigns/",
        {
            "title": "Should fail",
            "target_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    )
    assert response.status_code == 403


def test_campaign_status_can_be_updated(chairman_client, national_unit):
    start, end = _window()
    created = chairman_client.post(
        "/api/v1/events/campaigns/",
        {
            "title": "Campaign",
            "target_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()
    response = chairman_client.patch(
        f"/api/v1/events/campaigns/{created['id']}/",
        {"status": "ACTIVE"},
        format="json",
    )
    assert response.json()["status"] == "ACTIVE"


def test_authorized_officer_can_create_standalone_event(chairman_client, national_unit):
    start, end = _window()
    response = chairman_client.post(
        "/api/v1/events/",
        {
            "title": "National Rally",
            "event_type": "RALLY",
            "target_unit_id": str(national_unit.id),
            "location": "Independence Square, Accra",
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["event_type"] == "RALLY"


def test_event_can_be_linked_to_campaign(chairman_client, national_unit):
    start, end = _window()
    campaign = chairman_client.post(
        "/api/v1/events/campaigns/",
        {
            "title": "GOTV Drive",
            "target_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()
    response = chairman_client.post(
        "/api/v1/events/",
        {
            "title": "Registration Booth Day",
            "event_type": "COMMUNITY_OUTREACH",
            "campaign_id": campaign["id"],
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["campaign"]["id"] == campaign["id"]


def test_ordinary_member_cannot_create_event(auth_client, national_unit):
    start, end = _window()
    response = auth_client.post(
        "/api/v1/events/",
        {
            "title": "Should fail",
            "event_type": "RALLY",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 403


def test_event_end_must_be_after_start(chairman_client, national_unit):
    start, end = _window()
    response = chairman_client.post(
        "/api/v1/events/",
        {
            "title": "Bad timing",
            "event_type": "RALLY",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": end,
            "scheduled_end": start,
        },
        format="json",
    )
    assert response.status_code == 400


def test_member_can_rsvp_to_event(chairman_client, auth_client, national_unit):
    start, end = _window()
    event = chairman_client.post(
        "/api/v1/events/",
        {
            "title": "Town Hall",
            "event_type": "TOWN_HALL",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()
    response = auth_client.post(
        f"/api/v1/events/{event['id']}/rsvp/", {"status": "ATTENDING"}, format="json"
    )
    assert response.status_code == 201


def test_organizer_can_view_rsvp_summary(chairman_client, auth_client, national_unit):
    start, end = _window()
    event = chairman_client.post(
        "/api/v1/events/",
        {
            "title": "Town Hall",
            "event_type": "TOWN_HALL",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()
    auth_client.post(
        f"/api/v1/events/{event['id']}/rsvp/", {"status": "ATTENDING"}, format="json"
    )
    response = chairman_client.get(f"/api/v1/events/{event['id']}/rsvps/")
    assert response.status_code == 200
    assert response.json()["attending_count"] == 1


def test_non_organizer_cannot_view_rsvp_summary(
    chairman_client, auth_client, national_unit
):
    start, end = _window()
    event = chairman_client.post(
        "/api/v1/events/",
        {
            "title": "Town Hall",
            "event_type": "TOWN_HALL",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()
    response = auth_client.get(f"/api/v1/events/{event['id']}/rsvps/")
    assert response.status_code == 403


def test_event_creation_notifies_subtree(chairman_client, auth_client, national_unit):
    start, end = _window()
    chairman_client.post(
        "/api/v1/events/",
        {
            "title": "Notify Test",
            "event_type": "RALLY",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    response = auth_client.get("/api/v1/messaging/notifications/")
    assert any(n["notification_type"] == "EVENT" for n in response.json()["results"])


def test_constituency_officer_cannot_organize_national_event(
    constituency_unit, national_unit
):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Constituency Chairman",
        code="const_chair_event_test",
        scope="CONSTITUENCY",
        permissions=["hierarchy.manage"],
    )
    user = User(
        email="constchair-event@example.com",
        phone_number="0244000600",
        first_name="Const",
        last_name="Chair",
        membership_id="NDC-TEST-000600",
        organizational_unit=constituency_unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()
    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    start, end = _window()
    response = client.post(
        "/api/v1/events/",
        {
            "title": "Should fail",
            "event_type": "RALLY",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 403
