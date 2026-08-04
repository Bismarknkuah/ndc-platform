import datetime

import pytest

pytestmark = pytest.mark.django_db


def test_dashboard_returns_profile_and_unread_count(auth_client, member_user):
    response = auth_client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["email"] == member_user.email
    assert body["unread_notification_count"] == 0


def test_dashboard_shows_upcoming_meeting(chairman_client, auth_client, national_unit):
    start = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat() + "Z"
    end = (
        datetime.datetime.utcnow() + datetime.timedelta(days=1, hours=1)
    ).isoformat() + "Z"
    chairman_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Party Congress",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    response = auth_client.get("/api/v1/dashboard/")
    titles = [m["title"] for m in response.json()["upcoming_meetings"]]
    assert "Party Congress" in titles


def test_dashboard_shows_pending_task_for_department_member(
    national_comms_director_client,
    auth_client,
    communications_department,
    national_unit,
    national_chairman_user,
):
    import datetime as dt

    national_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(national_chairman_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(national_unit.id),
            "position": "MEMBER",
        },
        format="json",
    )
    national_comms_director_client.post(
        "/api/v1/departments/tasks/",
        {
            "department_id": str(communications_department.id),
            "assigned_to_id": str(national_chairman_user.id),
            "title": "Radio interview",
            "engagement_type": "RADIO",
            "scheduled_at": (dt.datetime.utcnow() + dt.timedelta(days=1)).isoformat()
            + "Z",
        },
        format="json",
    )

    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(national_chairman_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get("/api/v1/dashboard/")
    titles = [t["title"] for t in response.json()["pending_tasks"]]
    assert "Radio interview" in titles


def test_dashboard_shows_teams_led_for_department_head(national_comms_director_client):
    response = national_comms_director_client.get("/api/v1/dashboard/")
    body = response.json()
    assert "teams_led" in body
    assert body["teams_led"][0]["department"]["name"] == "Communications"


def test_dashboard_omits_teams_led_for_ordinary_member(auth_client):
    response = auth_client.get("/api/v1/dashboard/")
    assert "teams_led" not in response.json()


def test_dashboard_shows_active_elections_for_director(
    election_it_director_client, national_unit
):
    start = datetime.datetime.utcnow().isoformat() + "Z"
    end = (datetime.datetime.utcnow() + datetime.timedelta(days=7)).isoformat() + "Z"
    created = election_it_director_client.post(
        "/api/v1/elections/",
        {
            "title": "Dashboard Test Election",
            "election_type": "POLL",
            "scope_unit_id": str(national_unit.id),
            "start_date": start,
            "end_date": end,
        },
        format="json",
    ).json()
    election_it_director_client.patch(
        f"/api/v1/elections/{created['id']}/", {"status": "OPEN"}, format="json"
    )

    response = election_it_director_client.get("/api/v1/dashboard/")
    titles = [e["title"] for e in response.json().get("active_elections", [])]
    assert "Dashboard Test Election" in titles


def test_dashboard_omits_active_elections_for_ordinary_member(auth_client):
    response = auth_client.get("/api/v1/dashboard/")
    assert "active_elections" not in response.json()


def test_dashboard_shows_finance_summary_for_treasurer(national_unit):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="National Treasurer",
        code="national_treasurer_dashboard_test",
        scope="NATIONAL",
        permissions=["finance.manage", "finance.view"],
    )
    treasurer = User(
        email="dashboard-treasurer@example.com",
        phone_number="0244000800",
        first_name="Dash",
        last_name="Treasurer",
        membership_id="NDC-TEST-000800",
        organizational_unit=national_unit,
        role=role,
    )
    treasurer.set_password("StrongPass123!")
    treasurer.save()

    client = APIClient()
    tokens = issue_token_pair(treasurer)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get("/api/v1/dashboard/")
    assert "finance_summary" in response.json()


def test_dashboard_omits_finance_summary_for_ordinary_member(auth_client):
    response = auth_client.get("/api/v1/dashboard/")
    assert "finance_summary" not in response.json()


def test_dashboard_shows_jurisdiction_summary_for_real_executive(
    chairman_client, national_unit
):
    response = chairman_client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    summary = response.json()["jurisdiction_summary"]
    assert summary["organizational_unit"]["id"] == str(national_unit.id)
    assert "total_members" in summary
    assert "pending_complaints" in summary
    assert "pending_discipline_cases" in summary
    assert "pending_welfare_requests" in summary
    assert "requires_attention" in summary


def test_dashboard_omits_jurisdiction_summary_for_ordinary_member(auth_client):
    response = auth_client.get("/api/v1/dashboard/")
    assert "jurisdiction_summary" not in response.json()


def test_dashboard_requires_authentication(api_client):
    response = api_client.get("/api/v1/dashboard/")
    assert response.status_code == 401
