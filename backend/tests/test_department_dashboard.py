import datetime

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def national_team_member(
    national_comms_director_client,
    communications_department,
    national_unit,
    national_chairman_user,
):
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
    return national_chairman_user


def test_director_can_view_own_team_dashboard(
    national_comms_director_client,
    communications_department,
    national_unit,
    national_team_member,
):
    response = national_comms_director_client.get(
        f"/api/v1/departments/dashboard/?department_id={communications_department.id}"
        f"&organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["department"]["code"] == "communications"
    assert body["team_size"] >= 1


def test_team_member_can_view_their_own_teams_dashboard(
    national_comms_director_client,
    communications_department,
    national_unit,
    national_team_member,
    api_client,
):
    from apps.accounts.authentication import issue_token_pair

    tokens = issue_token_pair(national_team_member)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.get(
        f"/api/v1/departments/dashboard/?department_id={communications_department.id}"
        f"&organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200


def test_unrelated_member_cannot_view_team_dashboard(
    auth_client, communications_department, national_unit
):
    response = auth_client.get(
        f"/api/v1/departments/dashboard/?department_id={communications_department.id}"
        f"&organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 403


def test_dashboard_shows_upcoming_tasks(
    national_comms_director_client,
    communications_department,
    national_unit,
    national_team_member,
):
    national_comms_director_client.post(
        "/api/v1/departments/tasks/",
        {
            "department_id": str(communications_department.id),
            "assigned_to_id": str(national_team_member.id),
            "title": "Evening news slot",
            "engagement_type": "TV",
            "platform_name": "GTV",
            "scheduled_at": (
                datetime.datetime.utcnow() + datetime.timedelta(days=2)
            ).isoformat()
            + "Z",
        },
        format="json",
    )
    response = national_comms_director_client.get(
        f"/api/v1/departments/dashboard/?department_id={communications_department.id}"
        f"&organizational_unit_id={national_unit.id}"
    )
    body = response.json()
    assert body["total_pending_tasks"] == 1
    assert len(body["upcoming_tasks"]) == 1
    assert body["upcoming_tasks"][0]["platform_name"] == "GTV"


def test_dashboard_requires_both_query_params(
    national_comms_director_client, communications_department
):
    response = national_comms_director_client.get(
        f"/api/v1/departments/dashboard/?department_id={communications_department.id}"
    )
    assert response.status_code == 400
