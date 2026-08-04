import datetime

import pytest

pytestmark = pytest.mark.django_db


def _window():
    start = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=2)).isoformat() + "Z"
    return start, end


def test_member_can_opt_in_as_volunteer(auth_client):
    response = auth_client.put(
        "/api/v1/volunteers/profile/",
        {"skills": ["Driving", "First Aid"], "availability_notes": "Weekends only"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["skills"] == ["Driving", "First Aid"]


def test_no_profile_returns_404(auth_client):
    response = auth_client.get("/api/v1/volunteers/profile/")
    assert response.status_code == 404


def test_authorized_officer_can_create_opportunity(chairman_client, national_unit):
    start, end = _window()
    response = chairman_client.post(
        "/api/v1/volunteers/opportunities/",
        {
            "title": "Ushers needed",
            "target_unit_id": str(national_unit.id),
            "needed_count": 5,
            "location": "Independence Square",
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["needed_count"] == 5
    assert response.json()["filled_count"] == 0


def test_ordinary_member_cannot_create_opportunity(auth_client, national_unit):
    start, end = _window()
    response = auth_client.post(
        "/api/v1/volunteers/opportunities/",
        {
            "title": "Should fail",
            "target_unit_id": str(national_unit.id),
            "needed_count": 1,
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 403


@pytest.fixture
def opportunity(chairman_client, national_unit):
    start, end = _window()
    return chairman_client.post(
        "/api/v1/volunteers/opportunities/",
        {
            "title": "Ushers needed",
            "target_unit_id": str(national_unit.id),
            "needed_count": 2,
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()


def test_member_can_sign_up(auth_client, opportunity):
    response = auth_client.post(
        f"/api/v1/volunteers/opportunities/{opportunity['id']}/signup/"
    )
    assert response.status_code == 201
    assert response.json()["status"] == "SIGNED_UP"


def test_signup_auto_creates_volunteer_profile(auth_client, opportunity, member_user):
    auth_client.post(f"/api/v1/volunteers/opportunities/{opportunity['id']}/signup/")
    from apps.volunteers.documents import VolunteerProfile

    assert VolunteerProfile.objects(user=member_user).count() == 1


def test_cannot_sign_up_twice(auth_client, opportunity):
    auth_client.post(f"/api/v1/volunteers/opportunities/{opportunity['id']}/signup/")
    response = auth_client.post(
        f"/api/v1/volunteers/opportunities/{opportunity['id']}/signup/"
    )
    assert response.status_code == 409


def test_opportunity_marked_filled_when_capacity_reached(
    auth_client, chairman_client, opportunity, national_chairman_user
):
    auth_client.post(f"/api/v1/volunteers/opportunities/{opportunity['id']}/signup/")
    chairman_client.post(
        f"/api/v1/volunteers/opportunities/{opportunity['id']}/signup/"
    )

    response = chairman_client.get(
        f"/api/v1/volunteers/opportunities/{opportunity['id']}/"
    )
    assert response.json()["filled_count"] == 2
    assert response.json()["status"] == "FILLED"


def test_organizer_can_view_signup_roster(chairman_client, auth_client, opportunity):
    auth_client.post(f"/api/v1/volunteers/opportunities/{opportunity['id']}/signup/")
    response = chairman_client.get(
        f"/api/v1/volunteers/opportunities/{opportunity['id']}/signups/"
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_non_organizer_cannot_view_roster(auth_client, opportunity):
    response = auth_client.get(
        f"/api/v1/volunteers/opportunities/{opportunity['id']}/signups/"
    )
    assert response.status_code == 403


def test_volunteer_opportunity_creation_notifies_subtree(
    chairman_client, auth_client, national_unit
):
    start, end = _window()
    chairman_client.post(
        "/api/v1/volunteers/opportunities/",
        {
            "title": "Notify Test",
            "target_unit_id": str(national_unit.id),
            "needed_count": 1,
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    response = auth_client.get("/api/v1/messaging/notifications/")
    assert any("Notify Test" in n["title"] for n in response.json()["results"])
