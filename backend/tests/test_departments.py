import datetime

import pytest

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Department definitions
# ---------------------------------------------------------------------------


def test_national_officer_can_create_department(chairman_client):
    response = chairman_client.post(
        "/api/v1/departments/",
        {"name": "Finance", "code": "finance-2", "description": "Money stuff."},
        format="json",
    )
    assert response.status_code == 201


def test_ordinary_member_cannot_create_department(auth_client):
    response = auth_client.post(
        "/api/v1/departments/", {"name": "Finance", "code": "finance-3"}, format="json"
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Bootstrapping the first department head
# ---------------------------------------------------------------------------


def test_national_chairman_can_appoint_first_national_director(
    chairman_client, communications_department, national_unit, member_user
):
    response = chairman_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(member_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(national_unit.id),
            "position": "HEAD",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["position"] == "HEAD"


def test_ordinary_member_cannot_bootstrap_a_director(
    auth_client, communications_department, national_unit, member_user
):
    response = auth_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(member_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(national_unit.id),
            "position": "HEAD",
        },
        format="json",
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# National director delegating downward: national team + regional directors
# ---------------------------------------------------------------------------


def test_national_director_can_add_national_team_member(
    national_comms_director_client,
    communications_department,
    national_unit,
    member_user,
):
    response = national_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(member_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(national_unit.id),
            "position": "MEMBER",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["position"] == "MEMBER"


def test_national_director_can_appoint_regional_director(
    national_comms_director_client,
    communications_department,
    regional_unit,
    member_user,
):
    response = national_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(member_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(regional_unit.id),
            "position": "HEAD",
        },
        format="json",
    )
    assert response.status_code == 201


def test_national_director_can_remove_regional_director(
    national_comms_director_client,
    communications_department,
    regional_unit,
    member_user,
):
    create = national_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(member_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(regional_unit.id),
            "position": "HEAD",
        },
        format="json",
    ).json()
    response = national_comms_director_client.delete(
        f"/api/v1/departments/assignments/{create['id']}/"
    )
    assert response.status_code == 204


# ---------------------------------------------------------------------------
# Regional director's own authority is scoped to their region's subtree
# ---------------------------------------------------------------------------


@pytest.fixture
def regional_comms_director_client(
    national_comms_director_client,
    communications_department,
    regional_unit,
    member_user,
):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    national_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(member_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(regional_unit.id),
            "position": "HEAD",
        },
        format="json",
    )
    client = APIClient()
    tokens = issue_token_pair(member_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def test_regional_director_can_add_regional_team_member(
    regional_comms_director_client,
    communications_department,
    regional_unit,
    national_chairman_user,
):
    response = regional_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(national_chairman_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(regional_unit.id),
            "position": "OFFICER",
        },
        format="json",
    )
    assert response.status_code == 201


def test_regional_director_can_manage_branch_level_department_members(
    regional_comms_director_client,
    communications_department,
    branch_unit,
    national_chairman_user,
):
    # Regions are ancestors of their constituencies/branches, so a Regional
    # director can reach all the way down, same as National can.
    response = regional_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(national_chairman_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(branch_unit.id),
            "position": "MEMBER",
        },
        format="json",
    )
    assert response.status_code == 201


def test_regional_director_cannot_appoint_at_national_level(
    regional_comms_director_client,
    communications_department,
    national_unit,
    national_chairman_user,
):
    response = regional_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(national_chairman_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(national_unit.id),
            "position": "MEMBER",
        },
        format="json",
    )
    assert response.status_code == 403


def test_regional_director_cannot_appoint_in_a_different_region(
    regional_comms_director_client,
    communications_department,
    national_unit,
    national_chairman_user,
):
    from apps.hierarchy.documents import OrganizationalUnit

    other_region = OrganizationalUnit.objects.create(
        name="Volta Region",
        code="ndc-volta",
        unit_type="REGIONAL",
        parent=national_unit,
    )
    response = regional_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(national_chairman_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(other_region.id),
            "position": "OFFICER",
        },
        format="json",
    )
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Constituency/district-level: manage branch members within their department
# ---------------------------------------------------------------------------


def test_constituency_head_can_manage_branch_members_in_their_department(
    national_comms_director_client,
    communications_department,
    constituency_unit,
    branch_unit,
    national_chairman_user,
    api_client,
    ordinary_role,
):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import User

    district_officer = User(
        email="district@example.com",
        phone_number="0244000020",
        first_name="Abena",
        last_name="District",
        membership_id="NDC-TEST-000020",
        organizational_unit=constituency_unit,
        role=ordinary_role,
    )
    district_officer.set_password("StrongPass123!")
    district_officer.save()

    # National director appoints the constituency-level head.
    appoint = national_comms_director_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(district_officer.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(constituency_unit.id),
            "position": "HEAD",
        },
        format="json",
    )
    assert appoint.status_code == 201

    tokens = issue_token_pair(district_officer)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post(
        "/api/v1/departments/assignments/",
        {
            "user_id": str(national_chairman_user.id),
            "department_id": str(communications_department.id),
            "organizational_unit_id": str(branch_unit.id),
            "position": "MEMBER",
        },
        format="json",
    )
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# Diary / task assignments
# ---------------------------------------------------------------------------


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


def test_director_can_assign_diary_task_to_team_member(
    national_comms_director_client, communications_department, national_team_member
):
    response = national_comms_director_client.post(
        "/api/v1/departments/tasks/",
        {
            "department_id": str(communications_department.id),
            "assigned_to_id": str(national_team_member.id),
            "title": "Morning show appearance",
            "engagement_type": "RADIO",
            "platform_name": "Joy FM",
            "scheduled_at": (
                datetime.datetime.utcnow() + datetime.timedelta(days=1)
            ).isoformat()
            + "Z",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["platform_name"] == "Joy FM"
    assert response.json()["status"] == "PENDING"


def test_cannot_assign_task_to_non_department_member(
    national_comms_director_client, communications_department, member_user
):
    response = national_comms_director_client.post(
        "/api/v1/departments/tasks/",
        {
            "department_id": str(communications_department.id),
            "assigned_to_id": str(member_user.id),
            "title": "Morning show appearance",
            "engagement_type": "RADIO",
            "scheduled_at": (
                datetime.datetime.utcnow() + datetime.timedelta(days=1)
            ).isoformat()
            + "Z",
        },
        format="json",
    )
    assert response.status_code == 400


def test_assignee_can_acknowledge_own_task(
    api_client,
    national_comms_director_client,
    communications_department,
    national_team_member,
):
    from apps.accounts.authentication import issue_token_pair

    created = national_comms_director_client.post(
        "/api/v1/departments/tasks/",
        {
            "department_id": str(communications_department.id),
            "assigned_to_id": str(national_team_member.id),
            "title": "Morning show appearance",
            "engagement_type": "RADIO",
            "scheduled_at": (
                datetime.datetime.utcnow() + datetime.timedelta(days=1)
            ).isoformat()
            + "Z",
        },
        format="json",
    ).json()

    tokens = issue_token_pair(national_team_member)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = api_client.patch(
        f"/api/v1/departments/tasks/{created['id']}/",
        {"status": "ACKNOWLEDGED"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ACKNOWLEDGED"


def test_assignee_cannot_cancel_own_task(
    api_client,
    national_comms_director_client,
    communications_department,
    national_team_member,
):
    from apps.accounts.authentication import issue_token_pair

    created = national_comms_director_client.post(
        "/api/v1/departments/tasks/",
        {
            "department_id": str(communications_department.id),
            "assigned_to_id": str(national_team_member.id),
            "title": "Morning show appearance",
            "engagement_type": "RADIO",
            "scheduled_at": (
                datetime.datetime.utcnow() + datetime.timedelta(days=1)
            ).isoformat()
            + "Z",
        },
        format="json",
    ).json()

    tokens = issue_token_pair(national_team_member)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = api_client.patch(
        f"/api/v1/departments/tasks/{created['id']}/",
        {"status": "CANCELLED"},
        format="json",
    )
    assert response.status_code == 403


def test_director_can_cancel_task(
    national_comms_director_client, communications_department, national_team_member
):
    created = national_comms_director_client.post(
        "/api/v1/departments/tasks/",
        {
            "department_id": str(communications_department.id),
            "assigned_to_id": str(national_team_member.id),
            "title": "Morning show appearance",
            "engagement_type": "RADIO",
            "scheduled_at": (
                datetime.datetime.utcnow() + datetime.timedelta(days=1)
            ).isoformat()
            + "Z",
        },
        format="json",
    ).json()
    response = national_comms_director_client.patch(
        f"/api/v1/departments/tasks/{created['id']}/",
        {"status": "CANCELLED"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"


def test_unrelated_member_cannot_assign_tasks(
    auth_client, communications_department, national_team_member
):
    response = auth_client.post(
        "/api/v1/departments/tasks/",
        {
            "department_id": str(communications_department.id),
            "assigned_to_id": str(national_team_member.id),
            "title": "Morning show appearance",
            "engagement_type": "RADIO",
            "scheduled_at": (
                datetime.datetime.utcnow() + datetime.timedelta(days=1)
            ).isoformat()
            + "Z",
        },
        format="json",
    )
    assert response.status_code == 403


def test_my_assignments_endpoint_returns_own_roles(
    national_comms_director_client, communications_department
):
    response = national_comms_director_client.get("/api/v1/departments/my-assignments/")
    assert response.status_code == 200
    assert any(a["department"]["code"] == "communications" for a in response.json())
