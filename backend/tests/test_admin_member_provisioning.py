import pytest

pytestmark = pytest.mark.django_db


def _required_fields(suffix="000"):
    """The demographic/contact fields AdminCreateMemberSerializer now
    requires for proper voter/member data quality."""
    return {
        "gender": "FEMALE",
        "date_of_birth": "1990-05-15T00:00:00Z",
        "national_id_number": f"GHA-{suffix}",
        "residential_address": "12 Liberation Road, Accra",
        "emergency_contact_name": "Kofi Emergency",
        "emergency_contact_phone": "0209990000",
    }


@pytest.fixture
def constituency_chairman_role():
    from apps.accounts.documents import Role

    return Role.objects.create(
        name="Constituency Chairman",
        code="constituency_chairman_test",
        scope="CONSTITUENCY",
        permissions=[
            "hierarchy.manage",
            "messaging.broadcast.downward",
            "messaging.report.upward",
        ],
    )


@pytest.fixture
def constituency_chairman_user(constituency_unit, constituency_chairman_role):
    from apps.accounts.documents import User

    user = User(
        email="constituency-chair@example.com",
        phone_number="0244000070",
        first_name="Kwabena",
        last_name="Chairman",
        membership_id="NDC-TEST-000070",
        organizational_unit=constituency_unit,
        role=constituency_chairman_role,
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


@pytest.fixture
def constituency_chairman_client(constituency_chairman_user):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(constituency_chairman_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def test_district_exec_can_create_branch_executive(
    constituency_chairman_client, branch_unit
):
    response = constituency_chairman_client.post(
        "/api/v1/auth/members/",
        {
            "email": "branchexec@example.com",
            "phone_number": "0244000080",
            "first_name": "Yaa",
            "last_name": "Branchy",
            "organizational_unit_id": str(branch_unit.id),
            **_required_fields("080"),
        },
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "branchexec@example.com"
    assert "temporary_password" in body
    assert len(body["temporary_password"]) >= 8


def test_created_member_must_change_password(constituency_chairman_client, branch_unit):
    response = constituency_chairman_client.post(
        "/api/v1/auth/members/",
        {
            "email": "branchexec2@example.com",
            "phone_number": "0244000081",
            "first_name": "Yaa",
            "last_name": "Branchy",
            "organizational_unit_id": str(branch_unit.id),
            **_required_fields("081"),
        },
        format="json",
    )
    assert response.json()["user"]["email"] == "branchexec2@example.com"
    from apps.accounts.documents import User

    created = User.objects.get(email="branchexec2@example.com")
    assert created.must_change_password is True


def test_ordinary_member_cannot_provision_others(auth_client, branch_unit):
    response = auth_client.post(
        "/api/v1/auth/members/",
        {
            "email": "shouldfail@example.com",
            "phone_number": "0244000082",
            "first_name": "No",
            "last_name": "Auth",
            "organizational_unit_id": str(branch_unit.id),
            **_required_fields("082"),
        },
        format="json",
    )
    assert response.status_code == 403


def test_constituency_chairman_cannot_provision_outside_their_constituency(
    constituency_chairman_client, national_unit
):
    from apps.hierarchy.documents import OrganizationalUnit

    other_region = OrganizationalUnit.objects.create(
        name="Volta Region",
        code="ndc-volta-provision-test",
        unit_type="REGIONAL",
        parent=national_unit,
    )
    other_branch = OrganizationalUnit.objects.create(
        name="Other Branch",
        code="ndc-other-branch-test",
        unit_type="CONSTITUENCY",
        parent=other_region,
    )
    response = constituency_chairman_client.post(
        "/api/v1/auth/members/",
        {
            "email": "outside@example.com",
            "phone_number": "0244000083",
            "first_name": "Out",
            "last_name": "Sider",
            "organizational_unit_id": str(other_branch.id),
            **_required_fields("083"),
        },
        format="json",
    )
    assert response.status_code == 403


def test_create_member_with_department_assignment(
    constituency_chairman_client,
    constituency_chairman_user,
    constituency_unit,
    branch_unit,
    communications_department,
):
    from apps.departments.documents import DepartmentAssignment

    DepartmentAssignment.objects.create(
        user=constituency_chairman_user,
        department=communications_department,
        organizational_unit=constituency_unit,
        position="HEAD",
    )

    response = constituency_chairman_client.post(
        "/api/v1/auth/members/",
        {
            "email": "branchcomms@example.com",
            "phone_number": "0244000084",
            "first_name": "Comms",
            "last_name": "Person",
            "organizational_unit_id": str(branch_unit.id),
            "department_id": str(communications_department.id),
            "department_position": "MEMBER",
            **_required_fields("084"),
        },
        format="json",
    )
    assert response.status_code == 201
    from apps.accounts.documents import User

    created_user = User.objects.get(email="branchcomms@example.com")
    assert (
        DepartmentAssignment.objects(
            user=created_user, department=communications_department
        ).count()
        == 1
    )


def test_department_assignment_requires_department_authority(
    constituency_chairman_client, branch_unit, communications_department
):
    # The constituency chairman has hierarchy.manage but no Communications
    # department authority, so the combined member+department call fails.
    response = constituency_chairman_client.post(
        "/api/v1/auth/members/",
        {
            "email": "shouldfail2@example.com",
            "phone_number": "0244000085",
            "first_name": "No",
            "last_name": "DeptAuth",
            "organizational_unit_id": str(branch_unit.id),
            "department_id": str(communications_department.id),
            "department_position": "MEMBER",
            **_required_fields("085"),
        },
        format="json",
    )
    assert response.status_code == 403
    from apps.accounts.documents import User

    assert not User.objects(email="shouldfail2@example.com").first()


def test_bulk_create_branch_executives_for_every_branch(
    constituency_chairman_client, constituency_unit
):
    from apps.hierarchy.documents import OrganizationalUnit

    branch_a = OrganizationalUnit.objects.create(
        name="Branch A",
        code="ndc-bulk-branch-a",
        unit_type="BRANCH",
        parent=constituency_unit,
    )
    branch_b = OrganizationalUnit.objects.create(
        name="Branch B",
        code="ndc-bulk-branch-b",
        unit_type="BRANCH",
        parent=constituency_unit,
    )

    response = constituency_chairman_client.post(
        "/api/v1/auth/members/bulk/",
        {
            "members": [
                {
                    "email": "bulk1@example.com",
                    "phone_number": "0244000090",
                    "first_name": "Bulk",
                    "last_name": "One",
                    "organizational_unit_id": str(branch_a.id),
                    **_required_fields("090"),
                },
                {
                    "email": "bulk2@example.com",
                    "phone_number": "0244000091",
                    "first_name": "Bulk",
                    "last_name": "Two",
                    "organizational_unit_id": str(branch_b.id),
                    **_required_fields("091"),
                },
            ]
        },
        format="json",
    )
    assert response.status_code == 207
    body = response.json()
    assert len(body["created"]) == 2
    assert len(body["errors"]) == 0


def test_bulk_create_partial_failure_does_not_block_others(
    constituency_chairman_client, branch_unit, member_user
):
    response = constituency_chairman_client.post(
        "/api/v1/auth/members/bulk/",
        {
            "members": [
                {
                    "email": member_user.email,  # duplicate -> should fail
                    "phone_number": "0244000092",
                    "first_name": "Dup",
                    "last_name": "Licate",
                    "organizational_unit_id": str(branch_unit.id),
                    **_required_fields("092"),
                },
                {
                    "email": "bulkgood@example.com",
                    "phone_number": "0244000093",
                    "first_name": "Good",
                    "last_name": "One",
                    "organizational_unit_id": str(branch_unit.id),
                    **_required_fields("093"),
                },
            ]
        },
        format="json",
    )
    assert response.status_code == 207
    body = response.json()
    assert len(body["created"]) == 1
    assert len(body["errors"]) == 1
    assert body["errors"][0]["index"] == 0


# ---------------------------------------------------------------------------
# Branch executives registering voters/members in their own branch
# ---------------------------------------------------------------------------


@pytest.fixture
def branch_chairman_role():
    from apps.accounts.documents import Role

    return Role.objects.create(
        name="Branch Chairman",
        code="branch_chairman_test",
        scope="BRANCH",
        permissions=["messaging.report.upward", "membership.register"],
    )


@pytest.fixture
def branch_chairman_user(branch_unit, branch_chairman_role):
    from apps.accounts.documents import User

    user = User(
        email="branch-chair@example.com",
        phone_number="0244000200",
        first_name="Ama",
        last_name="BranchChair",
        membership_id="NDC-TEST-000200",
        organizational_unit=branch_unit,
        role=branch_chairman_role,
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


@pytest.fixture
def branch_chairman_client(branch_chairman_user):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(branch_chairman_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def test_branch_executive_can_register_member_in_own_branch(
    branch_chairman_client, branch_unit
):
    response = branch_chairman_client.post(
        "/api/v1/auth/members/",
        {
            "email": "voter1@example.com",
            "phone_number": "0244000201",
            "first_name": "New",
            "last_name": "Voter",
            "organizational_unit_id": str(branch_unit.id),
            **_required_fields("201"),
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["user"]["email"] == "voter1@example.com"


def test_branch_executive_cannot_register_outside_own_branch(
    branch_chairman_client, constituency_unit
):
    from apps.hierarchy.documents import OrganizationalUnit

    other_branch = OrganizationalUnit.objects.create(
        name="Other Branch",
        code="ndc-other-branch-jurisdiction-test",
        unit_type="BRANCH",
        parent=constituency_unit,
    )
    response = branch_chairman_client.post(
        "/api/v1/auth/members/",
        {
            "email": "voter2@example.com",
            "phone_number": "0244000202",
            "first_name": "New",
            "last_name": "Voter",
            "organizational_unit_id": str(other_branch.id),
            **_required_fields("202"),
        },
        format="json",
    )
    assert response.status_code == 403


def test_branch_executive_cannot_manage_hierarchy(branch_chairman_client, branch_unit):
    """membership.register is deliberately narrower than hierarchy.manage."""
    response = branch_chairman_client.post(
        "/api/v1/hierarchy/units/",
        {
            "name": "Sneaky Sub-branch",
            "code": "sneaky-sub-branch",
            "unit_type": "BRANCH",
            "parent_id": str(branch_unit.id),
        },
        format="json",
    )
    assert response.status_code == 403


def test_registration_requires_the_expanded_data_fields(
    branch_chairman_client, branch_unit
):
    response = branch_chairman_client.post(
        "/api/v1/auth/members/",
        {
            "email": "incomplete@example.com",
            "phone_number": "0244000203",
            "first_name": "Missing",
            "last_name": "Fields",
            "organizational_unit_id": str(branch_unit.id),
            # deliberately omit gender/date_of_birth/national_id_number/
            # residential_address/emergency_contact_*
        },
        format="json",
    )
    assert response.status_code == 400
    errors = response.json()["error"]["message"]
    for field in (
        "gender",
        "date_of_birth",
        "national_id_number",
        "residential_address",
        "emergency_contact_name",
        "emergency_contact_phone",
    ):
        assert field in errors


def test_registered_member_profile_reflects_full_data(
    branch_chairman_client, branch_unit
):
    response = branch_chairman_client.post(
        "/api/v1/auth/members/",
        {
            "email": "fulldata@example.com",
            "phone_number": "0244000204",
            "first_name": "Full",
            "last_name": "Data",
            "voter_id_number": "VOTER-204",
            "occupation": "Teacher",
            "marital_status": "MARRIED",
            "organizational_unit_id": str(branch_unit.id),
            **_required_fields("204"),
        },
        format="json",
    )
    assert response.status_code == 201
    user_data = response.json()["user"]
    assert user_data["national_id_number"] == "GHA-204"
    assert user_data["voter_id_number"] == "VOTER-204"
    assert user_data["occupation"] == "Teacher"
    assert user_data["marital_status"] == "MARRIED"
    assert user_data["residential_address"] == "12 Liberation Road, Accra"
    assert user_data["emergency_contact_name"] == "Kofi Emergency"


def test_duplicate_national_id_number_rejected(branch_chairman_client, branch_unit):
    payload = {
        "email": "dupnid1@example.com",
        "phone_number": "0244000205",
        "first_name": "First",
        "last_name": "Registrant",
        "organizational_unit_id": str(branch_unit.id),
        **_required_fields("SAME-ID"),
    }
    first = branch_chairman_client.post("/api/v1/auth/members/", payload, format="json")
    assert first.status_code == 201

    payload2 = dict(payload, email="dupnid2@example.com", phone_number="0244000206")
    second = branch_chairman_client.post(
        "/api/v1/auth/members/", payload2, format="json"
    )
    assert second.status_code == 400
    assert "national_id_number" in second.json()["error"]["message"]


def test_duplicate_voter_id_number_rejected(branch_chairman_client, branch_unit):
    payload = {
        "email": "dupvid1@example.com",
        "phone_number": "0244000207",
        "first_name": "First",
        "last_name": "Registrant",
        "voter_id_number": "SAME-VOTER-ID",
        "organizational_unit_id": str(branch_unit.id),
        **_required_fields("207"),
    }
    first = branch_chairman_client.post("/api/v1/auth/members/", payload, format="json")
    assert first.status_code == 201

    payload2 = dict(payload, email="dupvid2@example.com", phone_number="0244000208")
    payload2.update(_required_fields("208"))
    second = branch_chairman_client.post(
        "/api/v1/auth/members/", payload2, format="json"
    )
    assert second.status_code == 400
    assert "voter_id_number" in second.json()["error"]["message"]


def test_two_registrations_can_both_omit_optional_voter_id(
    branch_chairman_client, branch_unit
):
    """Two members with no voter_id_number supplied must NOT collide with
    each other under the sparse-unique index."""
    payload1 = {
        "email": "novid1@example.com",
        "phone_number": "0244000209",
        "first_name": "No",
        "last_name": "VoterIdOne",
        "organizational_unit_id": str(branch_unit.id),
        **_required_fields("209"),
    }
    payload2 = {
        "email": "novid2@example.com",
        "phone_number": "0244000210",
        "first_name": "No",
        "last_name": "VoterIdTwo",
        "organizational_unit_id": str(branch_unit.id),
        **_required_fields("210"),
    }
    first = branch_chairman_client.post(
        "/api/v1/auth/members/", payload1, format="json"
    )
    second = branch_chairman_client.post(
        "/api/v1/auth/members/", payload2, format="json"
    )
    assert first.status_code == 201
    assert second.status_code == 201


def test_branch_secretary_can_also_register_members(branch_unit):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Branch Secretary",
        code="branch_secretary_test",
        scope="BRANCH",
        permissions=["messaging.report.upward", "membership.register"],
    )
    secretary = User(
        email="branch-sec@example.com",
        phone_number="0244000211",
        first_name="Kofi",
        last_name="BranchSec",
        membership_id="NDC-TEST-000211",
        organizational_unit=branch_unit,
        role=role,
    )
    secretary.set_password("StrongPass123!")
    secretary.save()

    client = APIClient()
    tokens = issue_token_pair(secretary)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.post(
        "/api/v1/auth/members/",
        {
            "email": "voter3@example.com",
            "phone_number": "0244000212",
            "first_name": "Another",
            "last_name": "Voter",
            "organizational_unit_id": str(branch_unit.id),
            **_required_fields("212"),
        },
        format="json",
    )
    assert response.status_code == 201
