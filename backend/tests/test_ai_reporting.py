from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


def test_generate_summary_noop_without_configuration(settings):
    from apps.analytics.ai_reporting import generate_summary

    settings.ANTHROPIC_API_KEY = ""
    result = generate_summary("MEMBERSHIP", {"total_members": 10})
    assert result is None


@patch("requests.post")
def test_generate_summary_calls_anthropic_when_configured(mock_post, settings):
    from apps.analytics.ai_reporting import generate_summary

    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Membership grew steadily this quarter."}]
    }
    mock_post.return_value = mock_response

    result = generate_summary("MEMBERSHIP", {"total_members": 500})
    assert result == "Membership grew steadily this quarter."
    call_args = mock_post.call_args
    assert "api.anthropic.com" in call_args[0][0]
    assert call_args[1]["headers"]["x-api-key"] == "sk-ant-test"


@patch("requests.post")
def test_generate_summary_returns_none_on_api_error(mock_post, settings):
    from apps.analytics.ai_reporting import generate_summary

    settings.ANTHROPIC_API_KEY = "sk-ant-test"

    def raise_error():
        raise Exception("500 error")

    mock_post.return_value = MagicMock(raise_for_status=raise_error)
    result = generate_summary("MEMBERSHIP", {"total_members": 500})
    assert result is None


def test_ai_report_endpoint_returns_503_when_unconfigured(
    chairman_client, national_unit, settings
):
    settings.ANTHROPIC_API_KEY = ""
    response = chairman_client.post(
        "/api/v1/analytics/ai-report/",
        {"report_type": "MEMBERSHIP", "organizational_unit_id": str(national_unit.id)},
        format="json",
    )
    assert response.status_code == 503


@patch("requests.post")
def test_ai_report_endpoint_generates_and_stores_report(
    mock_post, chairman_client, national_unit, settings
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Solid membership base."}]
    }
    mock_post.return_value = mock_response

    response = chairman_client.post(
        "/api/v1/analytics/ai-report/",
        {"report_type": "MEMBERSHIP", "organizational_unit_id": str(national_unit.id)},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["summary_text"] == "Solid membership base."
    assert "total_members" in response.json()["source_data"]


def test_ordinary_member_cannot_generate_ai_report(
    auth_client, national_unit, settings
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    response = auth_client.post(
        "/api/v1/analytics/ai-report/",
        {"report_type": "MEMBERSHIP", "organizational_unit_id": str(national_unit.id)},
        format="json",
    )
    assert response.status_code == 403


@patch("requests.post")
def test_ai_report_history_is_listed(
    mock_post, chairman_client, national_unit, settings
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Summary text."}]
    }
    mock_post.return_value = mock_response

    chairman_client.post(
        "/api/v1/analytics/ai-report/",
        {"report_type": "MEMBERSHIP", "organizational_unit_id": str(national_unit.id)},
        format="json",
    )
    response = chairman_client.get(
        f"/api/v1/analytics/ai-report/?organizational_unit_id={national_unit.id}"
    )
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_department_report_requires_department_id(
    chairman_client, national_unit, settings
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    response = chairman_client.post(
        "/api/v1/analytics/ai-report/",
        {"report_type": "DEPARTMENT", "organizational_unit_id": str(national_unit.id)},
        format="json",
    )
    assert response.status_code == 400


@patch("requests.post")
def test_finance_report_uses_real_finance_summary(
    mock_post, chairman_client, national_unit, settings
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "Finances look healthy."}]
    }
    mock_post.return_value = mock_response

    response = chairman_client.post(
        "/api/v1/analytics/ai-report/",
        {"report_type": "FINANCE", "organizational_unit_id": str(national_unit.id)},
        format="json",
    )
    assert response.status_code == 201
    assert "total_income" in response.json()["source_data"]
