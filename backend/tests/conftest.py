import os

# config.settings auto-detects pytest ("pytest" in sys.modules) and
# switches Mongo/cache to dependency-free backends (mongomock / locmem)
# on its own. We still pin these explicitly for reproducibility across
# environments and to avoid accidentally hitting a real SECRET_KEY.
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("DEBUG", "True")

import pytest  # noqa: E402
from rest_framework.test import APIClient  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_mongo_between_tests():
    """
    Ensures every test starts with an empty MongoDB (mongomock) state.

    Deliberately uses delete_many({}) rather than drop_collection(): dropping
    a collection also destroys its indexes, and MongoEngine only calls
    ensure_indexes() once per process (per Document class) - it does not
    notice the collection (and its unique indexes) got recreated from
    scratch. That silently disables uniqueness constraints in whichever
    test happens to run after a collection's first drop, in an
    order-dependent way. Clearing documents instead of dropping the
    collection keeps indexes intact across the whole test session.
    """
    yield
    import mongoengine

    db = mongoengine.connection.get_db()
    for collection_name in db.list_collection_names():
        db[collection_name].delete_many({})


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def national_unit():
    from apps.hierarchy.documents import OrganizationalUnit

    return OrganizationalUnit.objects.create(
        name="National Democratic Congress - National",
        code="ndc-national",
        unit_type="NATIONAL",
    )


@pytest.fixture
def regional_unit(national_unit):
    from apps.hierarchy.documents import OrganizationalUnit

    return OrganizationalUnit.objects.create(
        name="Ashanti Region",
        code="ndc-ashanti",
        unit_type="REGIONAL",
        parent=national_unit,
    )


@pytest.fixture
def constituency_unit(regional_unit):
    from apps.hierarchy.documents import OrganizationalUnit

    return OrganizationalUnit.objects.create(
        name="Kumasi Central",
        code="ndc-kumasi-central",
        unit_type="CONSTITUENCY",
        parent=regional_unit,
    )


@pytest.fixture
def branch_unit(constituency_unit):
    from apps.hierarchy.documents import OrganizationalUnit

    return OrganizationalUnit.objects.create(
        name="Adum Polling Station A",
        code="ndc-adum-branch-a",
        unit_type="BRANCH",
        parent=constituency_unit,
    )


@pytest.fixture
def ordinary_role():
    from apps.accounts.documents import Role

    return Role.objects.create(
        name="Ordinary Member",
        code="ordinary_member",
        scope="BRANCH",
        is_executive=False,
        permissions=["profile.manage_own"],
    )


@pytest.fixture
def national_chairman_role():
    from apps.accounts.documents import Role

    return Role.objects.create(
        name="National Chairman",
        code="national_chairman",
        scope="NATIONAL",
        is_executive=True,
        permissions=[
            "hierarchy.manage",
            "hierarchy.manage_roles",
            "audit.view",
            "meetings.call_all_members",
        ],
    )


@pytest.fixture
def member_user(branch_unit, ordinary_role):
    from apps.accounts.documents import User

    user = User(
        email="member@example.com",
        phone_number="0244000001",
        first_name="Kofi",
        last_name="Mensah",
        membership_id="NDC-TEST-000001",
        organizational_unit=branch_unit,
        role=ordinary_role,
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


@pytest.fixture
def national_chairman_user(national_unit, national_chairman_role):
    from apps.accounts.documents import User

    user = User(
        email="chairman@example.com",
        phone_number="0244000002",
        first_name="Ama",
        last_name="Boateng",
        membership_id="NDC-TEST-000002",
        organizational_unit=national_unit,
        role=national_chairman_role,
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


@pytest.fixture
def auth_client(member_user):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(member_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


@pytest.fixture
def chairman_client(national_chairman_user):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(national_chairman_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


@pytest.fixture
def communications_department():
    from apps.departments.documents import Department

    return Department.objects.create(
        code="communications", name="Communications", description="Media & broadcast."
    )


@pytest.fixture
def elections_department():
    from apps.departments.documents import Department

    return Department.objects.create(
        code="elections", name="Elections", description="Election-day operations."
    )


@pytest.fixture
def national_comms_director(
    national_unit, ordinary_role, communications_department, national_chairman_user
):
    """A user appointed as National Communications Director (HEAD @ NATIONAL)."""
    from apps.accounts.documents import User
    from apps.departments.documents import DepartmentAssignment

    user = User(
        email="director@example.com",
        phone_number="0244000010",
        first_name="Kwame",
        last_name="Director",
        membership_id="NDC-TEST-000010",
        organizational_unit=national_unit,
        role=ordinary_role,
    )
    user.set_password("StrongPass123!")
    user.save()
    DepartmentAssignment.objects.create(
        user=user,
        department=communications_department,
        organizational_unit=national_unit,
        position="HEAD",
        appointed_by=national_chairman_user,
    )
    return user


@pytest.fixture
def national_comms_director_client(national_comms_director):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(national_comms_director)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


# ---------------------------------------------------------------------------
# Elections fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def election_it_director_role():
    from apps.accounts.documents import Role

    return Role.objects.create(
        name="Election and IT Director",
        code="election_it_director_test",
        scope="NATIONAL",
        permissions=["elections.manage", "messaging.broadcast.downward"],
    )


@pytest.fixture
def election_it_director_user(national_unit, election_it_director_role):
    from apps.accounts.documents import User

    user = User(
        email="election-director@example.com",
        phone_number="0244000300",
        first_name="Nana",
        last_name="Director",
        membership_id="NDC-TEST-000300",
        organizational_unit=national_unit,
        role=election_it_director_role,
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


@pytest.fixture
def election_it_director_client(election_it_director_user):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(election_it_director_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


# ---------------------------------------------------------------------------
# Messaging fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def broadcaster_role():
    from apps.accounts.documents import Role

    return Role.objects.create(
        name="National Organizer",
        code="national_organizer_test",
        scope="NATIONAL",
        is_executive=True,
        permissions=["messaging.broadcast.downward"],
    )


@pytest.fixture
def reporter_role():
    from apps.accounts.documents import Role

    return Role.objects.create(
        name="Branch Secretary",
        code="branch_secretary_test",
        scope="BRANCH",
        is_executive=True,
        permissions=["messaging.report.upward"],
    )


@pytest.fixture
def national_broadcaster_user(national_unit, broadcaster_role):
    from apps.accounts.documents import User

    user = User(
        email="organizer@example.com",
        phone_number="0244000030",
        first_name="Kojo",
        last_name="Organizer",
        membership_id="NDC-TEST-000030",
        organizational_unit=national_unit,
        role=broadcaster_role,
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


@pytest.fixture
def national_broadcaster_client(national_broadcaster_user):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(national_broadcaster_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


@pytest.fixture
def branch_reporter_user(branch_unit, reporter_role):
    from apps.accounts.documents import User

    user = User(
        email="secretary@example.com",
        phone_number="0244000040",
        first_name="Adjoa",
        last_name="Secretary",
        membership_id="NDC-TEST-000040",
        organizational_unit=branch_unit,
        role=reporter_role,
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


@pytest.fixture
def branch_reporter_client(branch_reporter_user):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(branch_reporter_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client
