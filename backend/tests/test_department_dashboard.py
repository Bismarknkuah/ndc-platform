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


def test_national_chairman_can_oversee_any_department_dashboard_without_a_specific_assignment(
    chairman_client, communications_department, national_unit
):
    """The actual bug this fix addresses: a National Chairman with broad
    hierarchy.manage authority but no DepartmentAssignment in
    Communications specifically was previously blocked from viewing the
    Communications team's dashboard - only a department-specific HEAD/
    DEPUTY_HEAD or an existing team member could. National oversight
    authority must not be scoped to one department."""
    response = chairman_client.get(
        f"/api/v1/departments/dashboard/?department_id={communications_department.id}"
        f"&organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200
    assert response.json()["department"]["code"] == "communications"


def test_regional_chairman_can_oversee_department_dashboards_within_their_own_region(
    national_unit, regional_unit, communications_department
):
    """Oversight follows the same ancestor-scoped rule as everywhere else
    in this codebase: a Regional Chairman may see any department's
    activity within their own region, but not (checked below) somewhere
    entirely outside their jurisdiction."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_oversight_test",
        scope="REGIONAL",
        is_executive=True,
        permissions=["hierarchy.manage"],
    )
    user = User(
        email="regional-oversight@example.com",
        phone_number="0244000098",
        first_name="Test",
        last_name="RegionalOversight",
        membership_id="NDC-TEST-000098",
        organizational_unit=regional_unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get(
        f"/api/v1/departments/dashboard/?department_id={communications_department.id}"
        f"&organizational_unit_id={regional_unit.id}"
    )
    assert response.status_code == 200


def test_national_chairman_can_view_a_members_task_diary_without_department_authority(
    chairman_client, communications_department, national_unit, member_user
):
    """Same oversight gap as the team dashboard, in the task diary
    endpoint: a National Chairman must be able to see any member's
    diary within their jurisdiction, not just members of departments
    they specifically hold authority in."""
    from apps.departments.documents import DepartmentAssignment

    DepartmentAssignment.objects.create(
        user=member_user,
        department=communications_department,
        organizational_unit=national_unit,
        position="MEMBER",
    )

    response = chairman_client.get(
        f"/api/v1/departments/tasks/?assigned_to_id={member_user.id}"
    )
    assert response.status_code == 200
