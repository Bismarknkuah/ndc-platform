import pytest

pytestmark = pytest.mark.django_db


def test_member_can_submit_welfare_request(auth_client):
    response = auth_client.post(
        "/api/v1/welfare/requests/",
        {
            "category": "BEREAVEMENT",
            "description": "Loss of a parent, requesting party support for funeral costs.",
            "amount_requested": "500.00",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "SUBMITTED"


def test_member_can_view_own_requests(auth_client):
    auth_client.post(
        "/api/v1/welfare/requests/",
        {
            "category": "MEDICAL",
            "description": "Hospital bill support.",
            "amount_requested": "300.00",
        },
        format="json",
    )
    response = auth_client.get("/api/v1/welfare/requests/")
    assert response.status_code == 200
    assert response.json()["count"] == 1


@pytest.fixture
def treasurer_client(national_unit):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="National Treasurer",
        code="welfare_treasurer_test",
        scope="NATIONAL",
        permissions=["finance.manage"],
    )
    treasurer = User(
        email="welfare-treasurer@example.com",
        phone_number="0244000900",
        first_name="Welfare",
        last_name="Treasurer",
        membership_id="NDC-TEST-000900",
        organizational_unit=national_unit,
        role=role,
    )
    treasurer.set_password("StrongPass123!")
    treasurer.save()
    client = APIClient()
    tokens = issue_token_pair(treasurer)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def test_treasurer_can_approve_request(treasurer_client, auth_client):
    created = auth_client.post(
        "/api/v1/welfare/requests/",
        {
            "category": "EMERGENCY",
            "description": "Emergency support needed.",
            "amount_requested": "200.00",
        },
        format="json",
    ).json()
    response = treasurer_client.patch(
        f"/api/v1/welfare/requests/{created['id']}/",
        {"status": "APPROVED"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"


def test_disbursement_creates_finance_record(
    treasurer_client, auth_client, national_unit
):
    created = auth_client.post(
        "/api/v1/welfare/requests/",
        {
            "category": "EDUCATIONAL",
            "description": "School fees support.",
            "amount_requested": "400.00",
        },
        format="json",
    ).json()
    treasurer_client.patch(
        f"/api/v1/welfare/requests/{created['id']}/",
        {"status": "APPROVED"},
        format="json",
    )
    response = treasurer_client.patch(
        f"/api/v1/welfare/requests/{created['id']}/",
        {"status": "DISBURSED"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["finance_record_id"] is not None

    from apps.finance.documents import FinanceRecord

    record = FinanceRecord.objects.get(id=response.json()["finance_record_id"])
    assert record.record_type == "EXPENSE"
    assert record.category == "Welfare Support"
    assert str(record.amount) == "400.00"
    assert record.status == "APPROVED"


def test_requester_cannot_approve_own_request(auth_client):
    created = auth_client.post(
        "/api/v1/welfare/requests/",
        {"category": "OTHER", "description": "Something.", "amount_requested": "50.00"},
        format="json",
    ).json()
    response = auth_client.patch(
        f"/api/v1/welfare/requests/{created['id']}/",
        {"status": "APPROVED"},
        format="json",
    )
    assert response.status_code == 403


def test_unrelated_member_cannot_view_others_request(
    auth_client, national_unit, ordinary_role
):
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import User
    from rest_framework.test import APIClient

    other_member = User(
        email="other-member@example.com",
        phone_number="0244000901",
        first_name="Other",
        last_name="Member",
        membership_id="NDC-TEST-000901",
        organizational_unit=national_unit,
        role=ordinary_role,
    )
    other_member.set_password("StrongPass123!")
    other_member.save()

    tokens = issue_token_pair(other_member)
    other_client = APIClient()
    other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    created = auth_client.post(
        "/api/v1/welfare/requests/",
        {
            "category": "OTHER",
            "description": "Private matter.",
            "amount_requested": "50.00",
        },
        format="json",
    ).json()
    response = other_client.get(f"/api/v1/welfare/requests/{created['id']}/")
    assert response.status_code == 403


def test_oversized_supporting_document_rejected(auth_client):
    response = auth_client.post(
        "/api/v1/welfare/requests/",
        {
            "category": "MEDICAL",
            "description": "Test",
            "amount_requested": "100.00",
            "supporting_document_base64": "A" * 3_000_000,
        },
        format="json",
    )
    assert response.status_code == 400


def test_treasurer_can_list_requests_by_jurisdiction(
    treasurer_client, auth_client, national_unit
):
    auth_client.post(
        "/api/v1/welfare/requests/",
        {"category": "MEDICAL", "description": "Test", "amount_requested": "100.00"},
        format="json",
    )
    response = treasurer_client.get(
        f"/api/v1/welfare/requests/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1
