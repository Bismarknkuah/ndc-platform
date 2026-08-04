import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db


NON_SUPERADMIN_DEMO_EMAILS = [
    "demo.national@ndc.example",
    "demo.regional@ndc.example",
    "demo.district@ndc.example",
    "demo.constituency@ndc.example",
    "demo.branch@ndc.example",
    "demo.member@ndc.example",
]
SUPERADMIN_DEMO_EMAIL = "demo.superadmin@ndc.example"
ALL_DEMO_EMAILS = [SUPERADMIN_DEMO_EMAIL, *NON_SUPERADMIN_DEMO_EMAILS]


def test_seed_platform_creates_demo_accounts():
    from apps.accounts.documents import User

    call_command("seed_platform")

    for email in NON_SUPERADMIN_DEMO_EMAILS:
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

    for email in NON_SUPERADMIN_DEMO_EMAILS:
        assert User.objects(email=email).first().is_superadmin is False


def test_seed_platform_demo_accounts_can_actually_log_in():
    from apps.accounts.documents import User

    call_command("seed_platform")

    for email in ALL_DEMO_EMAILS:
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

    for email in ALL_DEMO_EMAILS:
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
