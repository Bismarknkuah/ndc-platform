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


def test_dashboard_teams_led_includes_real_finance_insight_for_finance_department(
    national_unit, national_chairman_user
):
    """The dashboard's department insight system: a Finance department
    head sees real Finance numbers in their team-led card, not a
    generic placeholder - confirming the department-code-to-insight
    mapping actually reaches the API response."""
    from apps.accounts.authentication import issue_token_pair
    from apps.departments.documents import Department, DepartmentAssignment
    from apps.finance.documents import FinanceRecord
    from rest_framework.test import APIClient

    finance_department = Department.objects.create(name="Finance", code="finance")
    DepartmentAssignment.objects.create(
        user=national_chairman_user,
        department=finance_department,
        organizational_unit=national_unit,
        position="HEAD",
    )
    FinanceRecord.objects.create(
        record_type="INCOME",
        category="Membership Dues",
        amount=500,
        organizational_unit=national_unit,
        recorded_by=national_chairman_user,
        status="APPROVED",
    )

    tokens = issue_token_pair(national_chairman_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    team = response.json()["teams_led"][0]
    assert team["insight"]["widget"] == "finance"
    stat_labels = [s["label"] for s in team["insight"]["stats"]]
    assert "Net Balance" in stat_labels


def test_dashboard_teams_led_falls_back_to_generic_insight_for_unmapped_department(
    national_unit, national_chairman_user
):
    """A department with no bespoke insight builder (e.g. Organizing)
    still gets a real, working insight - team size and pending tasks -
    rather than an error or nothing at all."""
    from apps.accounts.authentication import issue_token_pair
    from apps.departments.documents import Department, DepartmentAssignment
    from rest_framework.test import APIClient

    organizing_department = Department.objects.create(
        name="Organizing", code="organizing"
    )
    DepartmentAssignment.objects.create(
        user=national_chairman_user,
        department=organizing_department,
        organizational_unit=national_unit,
        position="HEAD",
    )

    tokens = issue_token_pair(national_chairman_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    team = response.json()["teams_led"][0]
    assert team["insight"]["widget"] == "generic"
    stat_labels = [s["label"] for s in team["insight"]["stats"]]
    assert "Team Size" in stat_labels


def test_secretary_gets_real_meetings_and_reports_insight_not_jurisdiction_rollup(
    branch_unit,
):
    """The actual bug this addresses: Secretary is meant to be the
    administrative engine (recording minutes, correspondence), not
    political leadership - they must not get the full jurisdiction
    rollup a Chairman gets, but they also should not get nothing. This
    confirms they get their own real, narrow widget instead."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.messaging.documents import Meeting
    from rest_framework.test import APIClient
    import datetime

    role = Role.objects.create(
        name="Branch Secretary",
        code="branch_secretary",
        scope="BRANCH",
        is_executive=True,
        permissions=["messaging.report.upward", "meetings.call"],
    )
    secretary = User(
        email="secretary-dashboard@example.com",
        phone_number="0244000090",
        first_name="Test",
        last_name="Secretary",
        membership_id="NDC-TEST-000090",
        organizational_unit=branch_unit,
        role=role,
    )
    secretary.set_password("StrongPass123!")
    secretary.save()

    Meeting.objects.create(
        title="Branch Executive Meeting",
        meeting_type="MEETING",
        target_unit=branch_unit,
        host=secretary,
        scheduled_start=datetime.datetime.utcnow() + datetime.timedelta(days=2),
        scheduled_end=datetime.datetime.utcnow() + datetime.timedelta(days=2, hours=1),
        meeting_url="https://meet.jit.si/test",
    )

    client = APIClient()
    tokens = issue_token_pair(secretary)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    body = response.json()
    assert "jurisdiction_summary" not in body
    assert body["role_insight"]["widget"] == "secretary"
    assert body["role_insight"]["stats"][0]["value"] == 1
    assert (
        body["role_insight"]["upcoming_meetings"][0]["title"]
        == "Branch Executive Meeting"
    )


def test_regional_secretary_no_longer_gets_broad_jurisdiction_oversight(
    regional_unit,
):
    """Confirms the actual permission fix: regional_secretary previously
    carried hierarchy.manage (inconsistent with constituency_secretary
    and branch_secretary, both correctly narrow), which meant a
    Regional Secretary got the full jurisdiction rollup a Regional
    Chairman gets. This role must now match the other Secretary levels."""
    from apps.core.management.commands.seed_platform import BASE_ROLES

    regional_secretary_def = next(
        r for r in BASE_ROLES if r["code"] == "regional_secretary"
    )
    assert "hierarchy.manage" not in regional_secretary_def["permissions"]


def test_youth_wing_organizer_gets_real_wing_insight_not_jurisdiction_rollup():
    """National Youth Organizer's unit is the Youth Wing auxiliary
    structure, not the geographic chain - confirms they get a real,
    honestly-scoped wing widget rather than an empty or misleading
    jurisdiction rollup."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.hierarchy.documents import OrganizationalUnit
    from rest_framework.test import APIClient

    national_unit = OrganizationalUnit.objects.create(
        name="National Test", code="ndc-national-wing-test", unit_type="NATIONAL"
    )
    youth_wing = OrganizationalUnit.objects.create(
        name="Youth Wing Test",
        code="ndc-youth-wing-test",
        unit_type="YOUTH_WING",
        parent=national_unit,
    )
    role = Role.objects.create(
        name="National Youth Organizer",
        code="national_youth_organizer",
        scope="YOUTH_WING",
        is_executive=True,
        permissions=["hierarchy.manage", "messaging.broadcast.downward"],
    )
    organizer = User(
        email="youth-organizer-test@example.com",
        phone_number="0244000089",
        first_name="Test",
        last_name="Youth",
        membership_id="NDC-TEST-000089",
        organizational_unit=youth_wing,
        role=role,
    )
    organizer.set_password("StrongPass123!")
    organizer.save()

    client = APIClient()
    tokens = issue_token_pair(organizer)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    body = response.json()
    assert body["role_insight"]["widget"] == "wing"
    assert body["role_insight"]["title"] == "Youth Wing Overview"


def test_ordinary_member_and_broad_executive_get_no_role_insight_clutter():
    """A Chairman already gets the richer jurisdiction rollup - the
    role_insight widget must not also appear and clutter their
    dashboard with something narrower and less useful."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.hierarchy.documents import OrganizationalUnit
    from rest_framework.test import APIClient

    unit = OrganizationalUnit.objects.create(
        name="Chairman Test Unit",
        code="ndc-chairman-insight-test",
        unit_type="NATIONAL",
    )
    role = Role.objects.create(
        name="National Chairman",
        code="national_chairman_insight_test",
        scope="NATIONAL",
        is_executive=True,
        permissions=["hierarchy.manage"],
    )
    chairman = User(
        email="chairman-insight-test@example.com",
        phone_number="0244000088",
        first_name="Test",
        last_name="Chairman",
        membership_id="NDC-TEST-000088",
        organizational_unit=unit,
        role=role,
    )
    chairman.set_password("StrongPass123!")
    chairman.save()

    client = APIClient()
    tokens = issue_token_pair(chairman)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    body = response.json()
    assert "jurisdiction_summary" in body
    assert "role_insight" not in body


def test_internal_auditor_gets_real_audit_widget_not_jurisdiction_rollup():
    """Internal Auditor has no hierarchy.manage, so unlike a Treasurer
    they never get the jurisdiction rollup - confirms they get a real,
    genuinely relevant audit-activity widget instead of nothing."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from apps.core.audit import log_action
    from apps.hierarchy.documents import OrganizationalUnit
    from rest_framework.test import APIClient

    unit = OrganizationalUnit.objects.create(
        name="National Test Auditor",
        code="ndc-national-auditor-test",
        unit_type="NATIONAL",
    )
    role = Role.objects.create(
        name="Internal Auditor",
        code="internal_auditor",
        scope="NATIONAL",
        is_executive=True,
        permissions=["finance.view", "audit.view"],
    )
    auditor = User(
        email="auditor-dashboard-test@example.com",
        phone_number="0244000087",
        first_name="Test",
        last_name="Auditor",
        membership_id="NDC-TEST-000087",
        organizational_unit=unit,
        role=role,
    )
    auditor.set_password("StrongPass123!")
    auditor.save()
    log_action(auditor, "test.action.for_dashboard")

    client = APIClient()
    tokens = issue_token_pair(auditor)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get("/api/v1/dashboard/")
    assert response.status_code == 200
    body = response.json()
    assert "jurisdiction_summary" not in body
    assert body["role_insight"]["widget"] == "auditor"
    assert body["role_insight"]["stats"][1]["value"] >= 1


def test_election_it_director_gets_real_elections_insight_not_generic_fallback(
    national_unit,
):
    """The IT department code now maps to the real elections insight
    (the role is literally "Election and IT Director"), rather than the
    generic team-size fallback every other unmapped department gets."""
    from apps.departments.documents import Department
    from apps.dashboard.department_insights import compute_department_insight

    it_department = Department.objects.create(name="IT", code="it")
    insight = compute_department_insight(it_department, national_unit)
    assert insight["widget"] == "elections"
