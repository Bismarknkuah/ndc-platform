import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture
def treasurer_role():
    from apps.accounts.documents import Role

    return Role.objects.create(
        name="National Treasurer",
        code="national_treasurer_test",
        scope="NATIONAL",
        permissions=["finance.manage", "finance.view"],
    )


@pytest.fixture
def treasurer_user(national_unit, treasurer_role):
    from apps.accounts.documents import User

    user = User(
        email="treasurer@example.com",
        phone_number="0244000700",
        first_name="National",
        last_name="Treasurer",
        membership_id="NDC-TEST-000700",
        organizational_unit=national_unit,
        role=treasurer_role,
    )
    user.set_password("StrongPass123!")
    user.save()
    return user


@pytest.fixture
def treasurer_client(treasurer_user):
    from apps.accounts.authentication import issue_token_pair
    from rest_framework.test import APIClient

    client = APIClient()
    tokens = issue_token_pair(treasurer_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    return client


def test_treasurer_can_record_income(treasurer_client, national_unit):
    response = treasurer_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "INCOME",
            "category": "Membership Dues",
            "amount": "500.00",
            "organizational_unit_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "PENDING"
    assert response.json()["amount"] == "500.00"


def test_ordinary_member_cannot_record_finance(auth_client, national_unit):
    response = auth_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "EXPENSE",
            "category": "Event Costs",
            "amount": "100.00",
            "organizational_unit_id": str(national_unit.id),
        },
        format="json",
    )
    assert response.status_code == 403


def test_treasurer_can_approve_record(treasurer_client, national_unit):
    created = treasurer_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "INCOME",
            "category": "Donations",
            "amount": "1000.00",
            "organizational_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    response = treasurer_client.patch(
        f"/api/v1/finance/records/{created['id']}/",
        {"status": "APPROVED"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    assert response.json()["approved_by"] is not None


def test_unrelated_user_cannot_approve_record(
    treasurer_client, auth_client, national_unit
):
    created = treasurer_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "INCOME",
            "category": "Donations",
            "amount": "1000.00",
            "organizational_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    response = auth_client.patch(
        f"/api/v1/finance/records/{created['id']}/",
        {"status": "APPROVED"},
        format="json",
    )
    assert response.status_code == 403


def test_finance_summary_aggregates_approved_income_and_expense(
    treasurer_client, national_unit
):
    income = treasurer_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "INCOME",
            "category": "Membership Dues",
            "amount": "800.00",
            "organizational_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    expense = treasurer_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "EXPENSE",
            "category": "Event Costs",
            "amount": "300.00",
            "organizational_unit_id": str(national_unit.id),
        },
        format="json",
    ).json()
    treasurer_client.patch(
        f"/api/v1/finance/records/{income['id']}/",
        {"status": "APPROVED"},
        format="json",
    )
    treasurer_client.patch(
        f"/api/v1/finance/records/{expense['id']}/",
        {"status": "APPROVED"},
        format="json",
    )

    response = treasurer_client.get(
        f"/api/v1/finance/summary/?organizational_unit_id={national_unit.id}"
    )
    body = response.json()
    assert body["total_income"] == "800.00"
    assert body["total_expense"] == "300.00"
    assert body["net_balance"] == "500.00"


def test_finance_summary_excludes_pending_by_default(treasurer_client, national_unit):
    treasurer_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "INCOME",
            "category": "Donations",
            "amount": "500.00",
            "organizational_unit_id": str(national_unit.id),
        },
        format="json",
    )
    response = treasurer_client.get(
        f"/api/v1/finance/summary/?organizational_unit_id={national_unit.id}"
    )
    assert response.json()["total_income"] == "0"


def test_finance_summary_all_status_includes_pending(treasurer_client, national_unit):
    treasurer_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "INCOME",
            "category": "Donations",
            "amount": "500.00",
            "organizational_unit_id": str(national_unit.id),
        },
        format="json",
    )
    response = treasurer_client.get(
        f"/api/v1/finance/summary/?organizational_unit_id={national_unit.id}&status=ALL"
    )
    assert response.json()["total_income"] == "500.00"


def test_finance_summary_rolls_up_subtree(
    treasurer_client, national_unit, regional_unit
):
    record = treasurer_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "INCOME",
            "category": "Membership Dues",
            "amount": "250.00",
            "organizational_unit_id": str(regional_unit.id),
        },
        format="json",
    ).json()
    treasurer_client.patch(
        f"/api/v1/finance/records/{record['id']}/",
        {"status": "APPROVED"},
        format="json",
    )

    national_summary = treasurer_client.get(
        f"/api/v1/finance/summary/?organizational_unit_id={national_unit.id}"
    )
    assert national_summary.json()["total_income"] == "250.00"


def test_ordinary_member_cannot_view_finance_records(auth_client, national_unit):
    response = auth_client.get(
        f"/api/v1/finance/records/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 403


def test_receipt_photo_can_be_attached(treasurer_client, national_unit):
    import base64

    photo = base64.b64encode(b"receipt-bytes").decode("ascii")
    response = treasurer_client.post(
        "/api/v1/finance/records/",
        {
            "record_type": "EXPENSE",
            "category": "Campaign Materials",
            "amount": "150.00",
            "organizational_unit_id": str(national_unit.id),
            "receipt_photo_base64": photo,
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["receipt_photo_base64"] == photo
