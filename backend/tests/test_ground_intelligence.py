from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


def _make_complaint(user, unit, subject="Bad road conditions"):
    from apps.complaints.documents import Complaint

    return Complaint.objects.create(
        submitted_by=user,
        submitting_unit=unit,
        target_unit=unit,
        complaint_type="COMPLAINT",
        subject=subject,
        description="The main road to the branch office has been unusable for months.",
    )


def test_ground_intelligence_returns_real_complaint_data(
    chairman_client, member_user, branch_unit, national_unit
):
    _make_complaint(member_user, branch_unit)

    response = chairman_client.get(
        f"/api/v1/analytics/ground-intelligence/{national_unit.id}/"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["counts"]["pending_complaints"] == 1
    assert body["recent_complaints"][0]["subject"] == "Bad road conditions"
    assert "unusable for months" in body["recent_complaints"][0]["description"]


def test_ground_intelligence_forbidden_for_ordinary_member(auth_client, national_unit):
    response = auth_client.get(
        f"/api/v1/analytics/ground-intelligence/{national_unit.id}/"
    )
    assert response.status_code == 403


def test_ground_intelligence_forbidden_for_regular_department_head(
    national_unit, communications_department
):
    """A department head or regular executive without the specific
    analytics.ground_intelligence permission must not get this - it is
    a materially broader view than their own jurisdiction rollup."""
    from apps.accounts.authentication import issue_token_pair
    from apps.accounts.documents import Role, User
    from rest_framework.test import APIClient

    role = Role.objects.create(
        name="Regional Chairman",
        code="regional_chairman_test",
        scope="REGIONAL",
        is_executive=True,
        permissions=["hierarchy.manage", "finance.manage"],
    )
    user = User(
        email="regional@example.com",
        phone_number="0244000099",
        first_name="Test",
        last_name="Regional",
        membership_id="NDC-TEST-000099",
        organizational_unit=national_unit,
        role=role,
    )
    user.set_password("StrongPass123!")
    user.save()

    client = APIClient()
    tokens = issue_token_pair(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = client.get(f"/api/v1/analytics/ground-intelligence/{national_unit.id}/")
    assert response.status_code == 403


@patch("requests.post")
def test_ground_briefing_uses_real_server_side_data_not_client_input(
    mock_post, settings, chairman_client, member_user, branch_unit, national_unit
):
    """The briefing endpoint must fetch real data itself - confirmed here
    by creating a real complaint and checking its actual content reaches
    the AI call, without the client ever sending it."""
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    _make_complaint(member_user, branch_unit, subject="Water shortage in the district")

    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Water shortage needs urgent attention."}]
    }
    mock_post.return_value = mock_response

    response = chairman_client.post(
        f"/api/v1/executive-ai/ground-briefing/{national_unit.id}/"
    )
    assert response.status_code == 200
    assert "Water shortage" in response.json()["briefing"]

    # Confirm the real complaint text was actually sent to the model,
    # not fabricated or omitted.
    sent_payload = mock_post.call_args.kwargs["json"]
    sent_text = str(sent_payload)
    assert "unusable for months" in sent_text


def test_ground_briefing_forbidden_for_ordinary_member(
    settings, auth_client, national_unit
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    response = auth_client.post(
        f"/api/v1/executive-ai/ground-briefing/{national_unit.id}/"
    )
    assert response.status_code == 403
