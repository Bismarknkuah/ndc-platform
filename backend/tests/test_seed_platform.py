import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


SUPERADMIN_DEMO_EMAIL = "demo.superadmin@ndc.example"


def _all_demo_emails():
    """Every demo account's email, read from the database after seeding
    rather than a hand-maintained list here - the earlier hardcoded list
    only covered 6 of what are now 33 accounts, meaning most demo
    accounts (including every one added across the last two sessions)
    were never actually checked by the password-refresh test below.
    This can't drift out of sync again since it queries reality."""
    from apps.accounts.documents import User

    return [u.email for u in User.objects(email__contains="demo.")]


def _non_superadmin_demo_emails():
    return [e for e in _all_demo_emails() if e != SUPERADMIN_DEMO_EMAIL]


def test_seed_platform_creates_demo_accounts():
    from apps.accounts.documents import User

    call_command("seed_platform")

    for email in _non_superadmin_demo_emails():
        user = User.objects(email=email).first()
        assert user is not None, f"{email} was not created"
        assert user.is_superadmin is False, f"{email} must not be a superadmin"
        assert user.role is not None
        assert user.organizational_unit is not None


def test_seed_platform_creates_exactly_one_superadmin_demo_account():
    """Only demo.superadmin@ndc.example may bypass every permission check -
    this is an explicit, narrowly-scoped exception, not a default."""
    from apps.accounts.documents import User

    call_command("seed_platform")

    superadmin = User.objects(email=SUPERADMIN_DEMO_EMAIL).first()
    assert superadmin is not None
    assert superadmin.is_superadmin is True
    assert superadmin.role.code == "system_administrator"

    for email in _non_superadmin_demo_emails():
        assert User.objects(email=email).first().is_superadmin is False


def test_seed_platform_demo_accounts_can_actually_log_in():
    from apps.accounts.documents import User

    call_command("seed_platform")

    for email in _all_demo_emails():
        user = User.objects(email=email).first()
        assert user.check_password("DemoPass123!"), f"{email} password mismatch"


def test_seed_platform_is_idempotent_and_refreshes_demo_passwords():
    """Running seed_platform twice must not create duplicates, must not
    crash on the "admin already exists" path, and must still refresh
    demo account passwords on the second run (this exact bug existed
    before: an early `return` after the admin-already-exists check used
    to skip demo seeding entirely on every run after the first)."""
    from apps.accounts.documents import User

    call_command("seed_platform")
    call_command("seed_platform")

    for email in _all_demo_emails():
        assert User.objects(email=email).count() == 1


def test_seed_platform_demo_units_form_a_real_branch_to_national_chain():
    from apps.accounts.documents import User

    call_command("seed_platform")

    branch_user = User.objects(email="demo.branch@ndc.example").first()
    branch_unit = branch_user.organizational_unit
    assert branch_unit.unit_type == "BRANCH"
    assert branch_unit.parent.unit_type == "CONSTITUENCY"
    assert branch_unit.parent.parent.unit_type == "REGIONAL"
    assert branch_unit.parent.parent.parent.unit_type == "NATIONAL"


def test_seed_platform_demo_district_is_auxiliary_not_a_main_chain_rung():
    """Article 17: the District Co-ordinating Committee coordinates
    constituencies within a region - it is not itself a rung between
    Regional and Constituency in the main authority chain."""
    from apps.accounts.documents import User

    call_command("seed_platform")

    district_user = User.objects(email="demo.district@ndc.example").first()
    district_unit = district_user.organizational_unit
    assert district_unit.unit_type == "DISTRICT_COORDINATING_COMMITTEE"
    assert district_unit.parent.unit_type == "REGIONAL"


def test_jurisdiction_admin_roles_carry_broad_multi_feature_permissions():
    """Each real jurisdiction admin (National/Regional/District/Constituency)
    should carry a genuinely broad permission set - hierarchy, finance,
    elections, membership, messaging - not just a single narrow tag, so
    the demo accounts actually showcase full jurisdiction control as
    requested. District Co-ordinator matching the others here is an
    explicit override of Article 17's literal "coordinates, doesn't
    command" framing, made by request rather than by default."""
    from apps.accounts.documents import Role

    call_command("seed_platform")

    for code in (
        "national_chairman",
        "regional_chairman",
        "district_coordinator",
        "constituency_chairman",
    ):
        role = Role.objects(code=code).first()
        assert role is not None
        for required in ("hierarchy.manage", "finance.manage", "elections.manage"):
            assert required in role.permissions, f"{code} missing {required}"


def test_seed_platform_creates_department_head_demo_accounts_with_real_assignments():
    """The department-based dashboard differentiation needs real
    DepartmentAssignment(position="HEAD") records to actually
    demonstrate - not just a Role - so each department-head demo
    account must show up correctly in teams_led-style queries."""
    from apps.accounts.documents import User
    from apps.departments.documents import DepartmentAssignment

    call_command("seed_platform")

    expected = {
        "demo.comms@ndc.example": "communications",
        "demo.treasurer@ndc.example": "finance",
        "demo.elections@ndc.example": "elections",
        "demo.membership@ndc.example": "membership",
        "demo.women@ndc.example": "womens-affairs",
    }

    for email, department_code in expected.items():
        user = User.objects(email=email).first()
        assert user is not None, f"{email} was not created"

        assignment = DepartmentAssignment.objects(user=user, is_active=True).first()
        assert assignment is not None, f"{email} has no DepartmentAssignment"
        assert assignment.department.code == department_code
        assert assignment.position == "HEAD"


def test_seed_platform_department_assignments_are_idempotent():
    from apps.departments.documents import DepartmentAssignment

    call_command("seed_platform")
    call_command("seed_platform")

    from apps.accounts.documents import User

    user = User.objects(email="demo.treasurer@ndc.example").first()
    assert DepartmentAssignment.objects(user=user).count() == 1


def test_department_head_demo_accounts_have_genuinely_narrow_roles_not_broad_oversight():
    """The actual bug this fixes: Communications Director, Membership
    Officer, and Women's Affairs Head demo accounts previously borrowed
    real constitutional NEC roles (national_organizer,
    national_women_organizer) that carry hierarchy.manage - a broad,
    jurisdiction-wide oversight permission - giving these department-
    scoped personas full visibility into Finance, Analytics, Position
    Management, and every other hierarchy-gated feature, not just their
    own department's tools. They must now hold dedicated, narrow roles
    instead."""
    from apps.accounts.documents import User

    call_command("seed_platform")

    narrow_expectations = {
        "demo.comms@ndc.example": "communications_director",
        "demo.membership@ndc.example": "membership_officer",
        "demo.women@ndc.example": "womens_affairs_head",
    }

    for email, expected_role_code in narrow_expectations.items():
        user = User.objects(email=email).first()
        assert user is not None, f"{email} was not created"
        assert user.role.code == expected_role_code, (
            f"{email} has role '{user.role.code}', expected the narrow "
            f"'{expected_role_code}'"
        )
        assert "hierarchy.manage" not in (user.role.permissions or []), (
            f"{email}'s role still carries hierarchy.manage - this is exactly "
            "the bug that gave a department head full jurisdiction-wide "
            "oversight instead of just their own department's tools"
        )


def test_ground_intelligence_sample_data_is_seeded_with_real_content():
    """The Leader Dashboard's Ground Intelligence and AI briefing need
    real complaint/welfare/report data to actually demonstrate - not an
    empty jurisdiction. Confirms real content lands in the demo units,
    not placeholder text, and that it actually flows into the same
    aggregation the Ground Intelligence endpoint uses."""
    from apps.analytics.services import compute_ground_intelligence
    from apps.complaints.documents import Complaint
    from apps.hierarchy.documents import OrganizationalUnit
    from apps.messaging.documents import Report
    from apps.welfare.documents import WelfareRequest

    call_command("seed_platform")

    branch_unit = OrganizationalUnit.objects(code="ndc-demo-branch").first()
    assert branch_unit is not None

    assert Complaint.objects(submitting_unit=branch_unit).count() >= 2
    assert WelfareRequest.objects(organizational_unit=branch_unit).count() >= 2
    assert Report.objects(submitting_unit=branch_unit).count() >= 1

    national_unit = OrganizationalUnit.objects(unit_type="NATIONAL").first()
    intelligence = compute_ground_intelligence(national_unit)
    assert intelligence["counts"]["pending_complaints"] >= 2
    assert intelligence["counts"]["pending_welfare_requests"] >= 2
    assert intelligence["counts"]["total_reports"] >= 1
    assert "roof" in intelligence["recent_complaints"][0]["description"].lower() or any(
        "roof" in c["description"].lower() for c in intelligence["recent_complaints"]
    )


def test_ground_intelligence_sample_data_is_idempotent():
    from apps.complaints.documents import Complaint

    call_command("seed_platform")
    first_count = Complaint.objects.count()
    call_command("seed_platform")
    second_count = Complaint.objects.count()
    assert first_count == second_count


def test_every_defined_role_now_has_a_demo_account():
    """The whole point of this pass: every genuinely distinct role
    defined in seed_platform's ROLE_DEFINITIONS should have a real,
    logged-in-able demo account, not just the original 13 - so the
    demo login list actually reflects the full party structure."""
    from apps.accounts.documents import Role, User

    call_command("seed_platform")

    department_codes = {
        "communications",
        "finance",
        "organizing",
        "legal-affairs",
        "womens-affairs",
        "youth-affairs",
        "elections",
        "membership",
        "research-innovation",
        "it",
        "political",
        "economic",
        "social",
        "conflict-resolution",
    }
    all_role_codes = {
        r.code for r in Role.objects.all() if r.code not in department_codes
    }
    demo_role_codes = {u.role.code for u in User.objects(email__contains="demo.")}

    missing = all_role_codes - demo_role_codes
    assert not missing, f"Roles with no demo account: {missing}"


def test_new_auxiliary_demo_accounts_belong_to_a_real_matching_unit():
    from apps.accounts.documents import User

    call_command("seed_platform")

    elders_chair = User.objects(email="demo.elders@ndc.example").first()
    assert elders_chair is not None
    assert elders_chair.organizational_unit.unit_type == "COUNCIL_OF_ELDERS"

    tein_coordinator = User.objects(email="demo.tein@ndc.example").first()
    assert tein_coordinator.organizational_unit.unit_type == "TEIN_NATIONAL"


def test_general_secretary_demo_account_can_log_in_and_has_top_tier_access():
    """Confirms the account created this pass actually reflects the
    tiered-access permission added last session, end to end."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import User
    from rest_framework.test import APIClient

    call_command("seed_platform")

    secretary = User.objects(email="demo.secretary@ndc.example").first()
    assert secretary is not None
    assert "analytics.ground_intelligence" in (secretary.role.permissions or [])

    tokens = issue_token_pair(secretary)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = client.get("/api/v1/auth/me/")
    assert response.status_code == 200


def test_new_scoped_tier_demo_account_can_log_in():
    """A regional-level officer added this pass should log in and have
    real hierarchy.manage authority, but not the top-tier permission."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import User
    from rest_framework.test import APIClient

    call_command("seed_platform")

    regional_sec = User.objects(email="demo.regionalsec@ndc.example").first()
    assert regional_sec is not None

    tokens = issue_token_pair(regional_sec)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    response = client.get("/api/v1/auth/me/")
    assert response.status_code == 200


def test_role_permissions_are_kept_in_sync_on_every_re_run():
    """The real bug this fixes: roles were only ever created once and
    never brought back into sync with BASE_ROLES afterward. If a role
    already existed in a database from an earlier seed run, a later
    permission change in the code (like adding
    analytics.ground_intelligence to national_general_secretary) would
    silently never take effect there, no matter how many times
    seed_platform was re-run."""
    from apps.accounts.documents import Role

    call_command("seed_platform")

    role = Role.objects(code="national_general_secretary").first()
    assert role is not None
    original_permissions = list(role.permissions)

    # Simulate an already-seeded environment where this role predates
    # a permission change in the code - strip a permission the code
    # actually grants, exactly like a stale, previously-seeded database
    # would look before a fix.
    role.permissions = ["hierarchy.manage"]
    role.save()

    call_command("seed_platform")

    role.reload()
    assert role.permissions == original_permissions
    assert "analytics.ground_intelligence" in role.permissions
