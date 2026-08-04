import hashlib
import hmac
import json
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


def _mock_response(json_body, status_code=200):
    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: (
        None if status_code < 400 else (_ for _ in ()).throw(Exception("HTTP error"))
    )
    mock_response.json.return_value = json_body
    return mock_response


@patch("requests.post")
def test_initialize_creates_pending_payment_and_returns_checkout_url(
    mock_post, settings, auth_client
):
    settings.PAYSTACK_SECRET_KEY = "sk_test_123"
    mock_post.return_value = _mock_response(
        {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/abc123",
                "access_code": "abc123",
            },
        }
    )

    response = auth_client.post(
        "/api/v1/dues/initialize/", {"amount": "50.00"}, format="json"
    )
    assert response.status_code == 200
    assert (
        response.json()["authorization_url"] == "https://checkout.paystack.com/abc123"
    )
    assert response.json()["reference"].startswith("NDC-DUES-")

    from apps.dues.documents import DuesPayment

    payment = DuesPayment.objects.first()
    assert payment.status == "PENDING"
    assert str(payment.amount) == "50.00"


def test_initialize_returns_503_when_unconfigured(settings, auth_client):
    settings.PAYSTACK_SECRET_KEY = ""
    response = auth_client.post(
        "/api/v1/dues/initialize/", {"amount": "50.00"}, format="json"
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "payment_unavailable"


@patch("requests.get")
@patch("requests.post")
def test_verify_updates_status_and_creates_finance_record_on_success(
    mock_post, mock_get, settings, auth_client, member_user
):
    settings.PAYSTACK_SECRET_KEY = "sk_test_123"
    mock_post.return_value = _mock_response(
        {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/xyz",
                "access_code": "xyz",
            },
        }
    )
    init_response = auth_client.post(
        "/api/v1/dues/initialize/",
        {"amount": "25.00", "period": "2026-08"},
        format="json",
    )
    reference = init_response.json()["reference"]

    mock_get.return_value = _mock_response(
        {
            "status": True,
            "data": {
                "status": "success",
                "channel": "mobile_money",
                "amount": 2500,
                "paid_at": "2026-08-01T10:00:00Z",
            },
        }
    )

    response = auth_client.get(f"/api/v1/dues/verify/{reference}/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "SUCCESS"
    assert body["payment_method"] == "mobile_money"

    from apps.dues.documents import DuesPayment
    from apps.finance.documents import FinanceRecord

    payment = DuesPayment.objects.get(paystack_reference=reference)
    assert payment.finance_record is not None
    finance_record = FinanceRecord.objects.get(id=payment.finance_record.id)
    assert finance_record.category == "Membership Dues"
    assert finance_record.status == "APPROVED"
    assert str(finance_record.amount) == "25.00"


def test_verify_is_forbidden_for_someone_elses_payment(
    auth_client, chairman_client, settings
):
    settings.PAYSTACK_SECRET_KEY = "sk_test_123"
    with patch("requests.post") as mock_post:
        mock_post.return_value = _mock_response(
            {
                "status": True,
                "data": {"authorization_url": "https://x", "access_code": "x"},
            }
        )
        init_response = auth_client.post(
            "/api/v1/dues/initialize/", {"amount": "10.00"}, format="json"
        )
    reference = init_response.json()["reference"]

    response = chairman_client.get(f"/api/v1/dues/verify/{reference}/")
    assert response.status_code == 403


@patch("requests.get")
def test_webhook_rejects_invalid_signature(mock_get, settings, api_client):
    settings.PAYSTACK_SECRET_KEY = "sk_test_123"
    response = api_client.post(
        "/api/v1/dues/webhook/",
        data=json.dumps({"event": "charge.success", "data": {"reference": "x"}}),
        content_type="application/json",
        HTTP_X_PAYSTACK_SIGNATURE="not-the-real-signature",
    )
    assert response.status_code == 401
    mock_get.assert_not_called()


@patch("requests.get")
@patch("requests.post")
def test_webhook_with_valid_signature_updates_payment(
    mock_post, mock_get, settings, auth_client, api_client
):
    settings.PAYSTACK_SECRET_KEY = "sk_test_123"
    mock_post.return_value = _mock_response(
        {
            "status": True,
            "data": {"authorization_url": "https://x", "access_code": "x"},
        }
    )
    init_response = auth_client.post(
        "/api/v1/dues/initialize/", {"amount": "15.00"}, format="json"
    )
    reference = init_response.json()["reference"]

    mock_get.return_value = _mock_response(
        {
            "status": True,
            "data": {
                "status": "success",
                "channel": "card",
                "amount": 1500,
                "paid_at": "2026-08-01T10:00:00Z",
            },
        }
    )

    body_dict = {"event": "charge.success", "data": {"reference": reference}}
    raw_body = json.dumps(body_dict).encode("utf-8")
    signature = hmac.new(b"sk_test_123", raw_body, hashlib.sha512).hexdigest()

    response = api_client.post(
        "/api/v1/dues/webhook/",
        data=raw_body,
        content_type="application/json",
        HTTP_X_PAYSTACK_SIGNATURE=signature,
    )
    assert response.status_code == 200

    from apps.dues.documents import DuesPayment

    payment = DuesPayment.objects.get(paystack_reference=reference)
    assert payment.status == "SUCCESS"


def test_history_only_shows_the_callers_own_payments(
    auth_client, chairman_client, settings
):
    settings.PAYSTACK_SECRET_KEY = "sk_test_123"
    with patch("requests.post") as mock_post:
        mock_post.return_value = _mock_response(
            {
                "status": True,
                "data": {"authorization_url": "https://x", "access_code": "x"},
            }
        )
        auth_client.post("/api/v1/dues/initialize/", {"amount": "5.00"}, format="json")

    member_history = auth_client.get("/api/v1/dues/history/")
    assert member_history.json()["count"] == 1

    chairman_history = chairman_client.get("/api/v1/dues/history/")
    assert chairman_history.json()["count"] == 0
