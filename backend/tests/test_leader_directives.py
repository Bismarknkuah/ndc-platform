import pytest

pytestmark = pytest.mark.django_db


def test_leader_can_assign_a_directive_to_a_regional_executive(
    chairman_client, regional_unit
):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User

    regional_role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_directive_test",
        scope="REGIONAL",
        is_executive=True,
        permissions=["hierarchy.manage"],
    )
    regional_exec = User(
        email="regional-exec@example.com",
        phone_number="0244000097",
        first_name="Regional",
        last_name="Exec",
        membership_id="NDC-TEST-000097",
        organizational_unit=regional_unit,
        role=regional_role,
    )
    regional_exec.set_password("StrongPass123!")
    regional_exec.save()

    response = chairman_client.post(
        "/api/v1/executive-ai/directives/",
        {
            "assigned_to_id": str(regional_exec.id),
            "title": "Prepare Ashanti Region for the campaign launch",
            "description": "Coordinate with constituency chairmen on logistics.",
        },
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["assigned_to"]["id"] == str(regional_exec.id)
    assert body["assigned_by"]["id"] is not None

    tokens = issue_token_pair(regional_exec)
    from rest_framework.test import APIClient

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    my_directives = client.get("/api/v1/executive-ai/directives/")
    assert my_directives.status_code == 200
    assert my_directives.json()["count"] == 1


def test_ordinary_executive_cannot_assign_directives(auth_client):
    response = auth_client.post(
        "/api/v1/executive-ai/directives/",
        {"assigned_to_id": "000000000000000000000000", "title": "Test"},
        format="json",
    )
    assert response.status_code == 403


def test_cannot_assign_a_directive_to_a_branch_level_executive(
    chairman_client, branch_unit
):
    from apps.accounts.documents import Role, User

    branch_role = Role.objects.create(
        name="Branch Secretary",
        code="branch_secretary_directive_test",
        scope="BRANCH",
        is_executive=True,
        permissions=["messaging.report.upward"],
    )
    branch_exec = User(
        email="branch-exec@example.com",
        phone_number="0244000096",
        first_name="Branch",
        last_name="Exec",
        membership_id="NDC-TEST-000096",
        organizational_unit=branch_unit,
        role=branch_role,
    )
    branch_exec.set_password("StrongPass123!")
    branch_exec.save()

    response = chairman_client.post(
        "/api/v1/executive-ai/directives/",
        {"assigned_to_id": str(branch_exec.id), "title": "Test"},
        format="json",
    )
    assert response.status_code == 400


def test_cannot_assign_a_directive_to_an_ordinary_member(chairman_client, member_user):
    response = chairman_client.post(
        "/api/v1/executive-ai/directives/",
        {"assigned_to_id": str(member_user.id), "title": "Test"},
        format="json",
    )
    assert response.status_code == 400


def test_assigned_executive_can_acknowledge_and_complete_their_own_directive(
    chairman_client, regional_unit
):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_ack_test",
        scope="REGIONAL",
        is_executive=True,
        permissions=["hierarchy.manage"],
    )
    regional_exec = User(
        email="regional-ack@example.com",
        phone_number="0244000095",
        first_name="Regional",
        last_name="Ack",
        membership_id="NDC-TEST-000095",
        organizational_unit=regional_unit,
        role=role,
    )
    regional_exec.set_password("StrongPass123!")
    regional_exec.save()

    create_response = chairman_client.post(
        "/api/v1/executive-ai/directives/",
        {"assigned_to_id": str(regional_exec.id), "title": "Test directive"},
        format="json",
    )
    directive_id = create_response.json()["id"]

    tokens = issue_token_pair(regional_exec)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    ack_response = client.post(
        f"/api/v1/executive-ai/directives/{directive_id}/acknowledge/"
    )
    assert ack_response.status_code == 200
    assert ack_response.json()["status"] == "ACKNOWLEDGED"

    complete_response = client.post(
        f"/api/v1/executive-ai/directives/{directive_id}/complete/"
    )
    assert complete_response.status_code == 200
    assert complete_response.json()["status"] == "COMPLETED"


def test_cannot_acknowledge_someone_elses_directive(
    chairman_client, regional_unit, auth_client
):
    from apps.accounts.documents import Role, User

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_other_test",
        scope="REGIONAL",
        is_executive=True,
        permissions=["hierarchy.manage"],
    )
    regional_exec = User(
        email="regional-other@example.com",
        phone_number="0244000094",
        first_name="Regional",
        last_name="Other",
        membership_id="NDC-TEST-000094",
        organizational_unit=regional_unit,
        role=role,
    )
    regional_exec.set_password("StrongPass123!")
    regional_exec.save()

    create_response = chairman_client.post(
        "/api/v1/executive-ai/directives/",
        {"assigned_to_id": str(regional_exec.id), "title": "Test"},
        format="json",
    )
    directive_id = create_response.json()["id"]

    response = auth_client.post(
        f"/api/v1/executive-ai/directives/{directive_id}/acknowledge/"
    )
    assert response.status_code == 403


def test_leader_can_see_directives_they_have_issued(chairman_client, regional_unit):
    from apps.accounts.documents import Role, User

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_issued_test",
        scope="REGIONAL",
        is_executive=True,
        permissions=["hierarchy.manage"],
    )
    regional_exec = User(
        email="regional-issued@example.com",
        phone_number="0244000093",
        first_name="Regional",
        last_name="Issued",
        membership_id="NDC-TEST-000093",
        organizational_unit=regional_unit,
        role=role,
    )
    regional_exec.set_password("StrongPass123!")
    regional_exec.save()

    chairman_client.post(
        "/api/v1/executive-ai/directives/",
        {"assigned_to_id": str(regional_exec.id), "title": "Test"},
        format="json",
    )

    response = chairman_client.get("/api/v1/executive-ai/directives/issued/")
    assert response.status_code == 200
    assert response.json()["count"] == 1
