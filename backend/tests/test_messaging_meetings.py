import datetime

import pytest

pytestmark = pytest.mark.django_db


def _future_window():
    start = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    end = start + datetime.timedelta(hours=1)
    return start.isoformat() + "Z", end.isoformat() + "Z"


def test_national_director_can_call_department_meeting_for_national_team(
    national_comms_director_client, communications_department, national_unit
):
    start, end = _future_window()
    response = national_comms_director_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "National Comms Weekly Sync",
            "meeting_type": "MEETING",
            "department_id": str(communications_department.id),
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["meeting_url"].startswith("https://meet.jit.si/")


def test_national_director_can_call_department_meeting_reaching_regional_team(
    national_comms_director_client, communications_department, regional_unit
):
    """'national can call regional or district' - department authority cascades down the tree."""
    start, end = _future_window()
    response = national_comms_director_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Regional Comms Training",
            "meeting_type": "WORKSHOP",
            "department_id": str(communications_department.id),
            "target_unit_id": str(regional_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["meeting_type"] == "WORKSHOP"


def test_unrelated_member_cannot_call_department_meeting(
    auth_client, communications_department, national_unit
):
    start, end = _future_window()
    response = auth_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Should fail",
            "meeting_type": "MEETING",
            "department_id": str(communications_department.id),
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 403


def test_regional_chairman_can_call_general_regional_meeting(regional_unit):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_meeting_test",
        scope="REGIONAL",
        permissions=["hierarchy.manage", "messaging.broadcast.downward"],
    )
    chairman = User(
        email="regchair@example.com",
        phone_number="0244000100",
        first_name="Regional",
        last_name="Chairman",
        membership_id="NDC-TEST-000100",
        organizational_unit=regional_unit,
        role=role,
    )
    chairman.set_password("StrongPass123!")
    chairman.save()

    client = APIClient()
    tokens = issue_token_pair(chairman)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    start, end = _future_window()
    response = client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Regional General Meeting",
            "meeting_type": "MEETING",
            "target_unit_id": str(regional_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201


def test_only_chairman_or_secretary_can_call_all_members_meeting(
    chairman_client, national_unit
):
    start, end = _future_window()
    response = chairman_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Emergency Party Congress",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201


def test_regional_chairman_cannot_call_all_members_meeting(
    regional_unit, national_unit
):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_allmembers_test",
        scope="REGIONAL",
        permissions=["hierarchy.manage", "messaging.broadcast.downward"],
    )
    chairman = User(
        email="regchair2@example.com",
        phone_number="0244000101",
        first_name="Regional",
        last_name="Chairman",
        membership_id="NDC-TEST-000101",
        organizational_unit=regional_unit,
        role=role,
    )
    chairman.set_password("StrongPass123!")
    chairman.save()

    client = APIClient()
    tokens = issue_token_pair(chairman)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    start, end = _future_window()
    response = client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Should fail - not chairman/secretary",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 403


def test_invitee_can_rsvp(chairman_client, auth_client, national_unit):
    start, end = _future_window()
    created = chairman_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "All-hands (national scope)",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()

    response = auth_client.post(
        f"/api/v1/messaging/meetings/{created['id']}/rsvp/",
        {"status": "ATTENDING"},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "ATTENDING"


def test_general_meeting_for_entire_party_requires_call_all_members_permission(
    national_broadcaster_client, national_unit
):
    """Targeting the National root (i.e. "all members") always requires
    meetings.call_all_members, regardless of any other permission held."""
    start, end = _future_window()
    response = national_broadcaster_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Should fail",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 403


def test_host_can_view_rsvp_summary(chairman_client, national_unit, auth_client):
    start, end = _future_window()
    created = chairman_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Party Congress",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()

    rsvp = auth_client.post(
        f"/api/v1/messaging/meetings/{created['id']}/rsvp/",
        {"status": "ATTENDING"},
        format="json",
    )
    assert rsvp.status_code == 201

    summary = chairman_client.get(f"/api/v1/messaging/meetings/{created['id']}/rsvps/")
    assert summary.status_code == 200
    assert summary.json()["attending_count"] == 1


def test_non_host_cannot_view_rsvp_summary(chairman_client, national_unit, auth_client):
    start, end = _future_window()
    created = chairman_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Party Congress",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()
    response = auth_client.get(f"/api/v1/messaging/meetings/{created['id']}/rsvps/")
    assert response.status_code == 403


def test_host_can_mark_meeting_live_then_completed(chairman_client, national_unit):
    start, end = _future_window()
    created = chairman_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Party Congress",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()

    live = chairman_client.patch(
        f"/api/v1/messaging/meetings/{created['id']}/",
        {"status": "LIVE"},
        format="json",
    )
    assert live.json()["status"] == "LIVE"

    done = chairman_client.patch(
        f"/api/v1/messaging/meetings/{created['id']}/",
        {"status": "COMPLETED"},
        format="json",
    )
    assert done.json()["status"] == "COMPLETED"


def test_non_host_cannot_change_meeting_status(
    chairman_client, national_unit, auth_client
):
    start, end = _future_window()
    created = chairman_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Party Congress",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    ).json()
    response = auth_client.patch(
        f"/api/v1/messaging/meetings/{created['id']}/",
        {"status": "CANCELLED"},
        format="json",
    )
    assert response.status_code == 403


def test_scheduled_end_must_be_after_start(chairman_client, national_unit):
    start, end = _future_window()
    response = chairman_client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Bad timing",
            "meeting_type": "MEETING",
            "target_unit_id": str(national_unit.id),
            "scheduled_start": end,  # swapped
            "scheduled_end": start,
        },
        format="json",
    )
    assert response.status_code == 400


def test_meeting_invitee_receives_notification(
    chairman_client, national_unit, auth_client
):
    start, end = _future_window()
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
    response = auth_client.get("/api/v1/messaging/notifications/")
    assert any(n["notification_type"] == "MEETING" for n in response.json()["results"])


# ---------------------------------------------------------------------------
# Jurisdiction-based authority: Regional/District Chairman & Secretary can
# call general meetings under their own jurisdiction; jurisdiction
# executives (not just department heads) can also call department
# meetings under their jurisdiction.
# ---------------------------------------------------------------------------


def _make_client(email, phone, membership_id, unit, role):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import User
    from rest_framework.test import APIClient

    user = User(
        email=email,
        phone_number=phone,
        first_name="Test",
        last_name="User",
        membership_id=membership_id,
        organizational_unit=unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client, user


def _role(code, scope, permissions):
    from apps.accounts.documents import Role

    return Role.objects.create(
        name=code.replace("_", " ").title(),
        code=code,
        scope=scope,
        permissions=permissions,
    )


def test_regional_secretary_can_call_general_regional_meeting(regional_unit):
    role = _role(
        "regional_secretary_jurisdiction_test",
        "REGIONAL",
        ["hierarchy.manage", "messaging.report.upward"],
    )
    client, _ = _make_client(
        "regsec@example.com", "0244000110", "NDC-TEST-000110", regional_unit, role
    )
    start, end = _future_window()
    response = client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Regional Secretary's General Meeting",
            "meeting_type": "MEETING",
            "target_unit_id": str(regional_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201


def test_district_secretary_can_call_general_district_meeting(constituency_unit):
    """Previously impossible: Constituency Secretary lacked any
    meeting-calling permission. Now fixed via the dedicated
    "meetings.call" permission, without granting full hierarchy.manage."""
    role = _role(
        "constituency_secretary_jurisdiction_test",
        "CONSTITUENCY",
        ["messaging.report.upward", "meetings.call"],
    )
    client, user = _make_client(
        "distsec@example.com", "0244000111", "NDC-TEST-000111", constituency_unit, role
    )
    # Confirm this role deliberately does NOT carry hierarchy.manage.
    assert "hierarchy.manage" not in user.role.permissions

    start, end = _future_window()
    response = client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "District Secretary's General Meeting",
            "meeting_type": "MEETING",
            "target_unit_id": str(constituency_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201


def test_district_secretary_still_cannot_manage_hierarchy(
    constituency_unit, regional_unit
):
    """meetings.call is deliberately narrower than hierarchy.manage - it
    grants meeting authority only, not org-unit/member-provisioning power."""
    role = _role(
        "constituency_secretary_scope_test",
        "CONSTITUENCY",
        ["messaging.report.upward", "meetings.call"],
    )
    client, _ = _make_client(
        "distsec2@example.com", "0244000112", "NDC-TEST-000112", constituency_unit, role
    )
    response = client.post(
        "/api/v1/hierarchy/units/",
        {
            "name": "Sneaky Branch",
            "code": "sneaky-branch",
            "unit_type": "BRANCH",
            "parent_id": str(constituency_unit.id),
        },
        format="json",
    )
    assert response.status_code == 403


def test_district_chairman_can_call_departmental_meeting_without_being_department_head(
    constituency_unit, branch_unit, communications_department
):
    """'district executive can call for departmental meetings under their
    jurisdiction' - a Constituency Chairman convenes a Communications
    meeting even though they hold no Communications DepartmentAssignment
    at all."""
    role = _role(
        "constituency_chairman_jurisdiction_test",
        "CONSTITUENCY",
        ["hierarchy.manage", "messaging.broadcast.downward"],
    )
    client, user = _make_client(
        "distchair@example.com",
        "0244000113",
        "NDC-TEST-000113",
        constituency_unit,
        role,
    )
    from apps.departments.documents import DepartmentAssignment

    assert DepartmentAssignment.objects(user=user).count() == 0

    start, end = _future_window()
    response = client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "District Communications Check-in",
            "meeting_type": "MEETING",
            "department_id": str(communications_department.id),
            "target_unit_id": str(constituency_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201


def test_district_secretary_can_call_departmental_meeting_under_jurisdiction(
    constituency_unit, communications_department
):
    role = _role(
        "constituency_secretary_dept_meeting_test",
        "CONSTITUENCY",
        ["messaging.report.upward", "meetings.call"],
    )
    client, _ = _make_client(
        "distsec3@example.com", "0244000114", "NDC-TEST-000114", constituency_unit, role
    )
    start, end = _future_window()
    response = client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "District Communications Sync",
            "meeting_type": "MEETING",
            "department_id": str(communications_department.id),
            "target_unit_id": str(constituency_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201


def test_jurisdiction_executive_cannot_call_departmental_meeting_outside_their_turf(
    constituency_unit, national_unit, communications_department
):
    from apps.hierarchy.documents import OrganizationalUnit

    other_region = OrganizationalUnit.objects.create(
        name="Volta Region",
        code="ndc-volta-jurisdiction-test",
        unit_type="REGIONAL",
        parent=national_unit,
    )
    role = _role(
        "constituency_chairman_outside_test",
        "CONSTITUENCY",
        ["hierarchy.manage", "messaging.broadcast.downward"],
    )
    client, _ = _make_client(
        "distchair2@example.com",
        "0244000115",
        "NDC-TEST-000115",
        constituency_unit,
        role,
    )
    start, end = _future_window()
    response = client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Should fail - outside jurisdiction",
            "meeting_type": "MEETING",
            "department_id": str(communications_department.id),
            "target_unit_id": str(other_region.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 403


def test_regional_department_head_can_call_meeting_for_own_region(
    regional_unit, communications_department
):
    """'all regional heads can call for departmental meetings' - a Regional
    Communications Director (department HEAD at their own region, not
    National) can call their own regional team's meeting."""
    role = _role("regional_officer_dept_head_test", "REGIONAL", [])
    client, user = _make_client(
        "regdirector@example.com", "0244000116", "NDC-TEST-000116", regional_unit, role
    )
    from apps.departments.documents import DepartmentAssignment

    DepartmentAssignment.objects.create(
        user=user,
        department=communications_department,
        organizational_unit=regional_unit,
        position="HEAD",
    )

    start, end = _future_window()
    response = client.post(
        "/api/v1/messaging/meetings/",
        {
            "title": "Regional Comms Team Meeting",
            "meeting_type": "MEETING",
            "department_id": str(communications_department.id),
            "target_unit_id": str(regional_unit.id),
            "scheduled_start": start,
            "scheduled_end": end,
        },
        format="json",
    )
    assert response.status_code == 201
