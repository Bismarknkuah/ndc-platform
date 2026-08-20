from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


def _mock_claude_response(text):
    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {"content": [{"type": "text", "text": text}]}
    return mock_response


@patch("requests.post")
def test_draft_broadcast_returns_ai_generated_text(
    mock_post, settings, chairman_client
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    mock_post.return_value = _mock_claude_response(
        "Fellow members, join us this Saturday..."
    )

    response = chairman_client.post(
        "/api/v1/executive-ai/draft-broadcast/",
        {"topic": "Upcoming membership drive", "tone": "formal"},
        format="json",
    )
    assert response.status_code == 200
    assert "Saturday" in response.json()["draft"]


@patch("requests.post")
def test_draft_broadcast_forbidden_for_ordinary_member(
    mock_post, settings, auth_client
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    response = auth_client.post(
        "/api/v1/executive-ai/draft-broadcast/", {"topic": "Test"}, format="json"
    )
    assert response.status_code == 403
    mock_post.assert_not_called()


def test_draft_broadcast_falls_back_to_rule_based_when_unconfigured(
    settings, chairman_client
):
    """The real change: this used to return 503 when no API key was
    configured. It now falls back to a genuine, working rule-based
    draft instead, clearly labeled with source="rule_based" so the
    caller can distinguish it from real AI output - it works out of
    the box with zero external dependency."""
    settings.ANTHROPIC_API_KEY = ""
    response = chairman_client.post(
        "/api/v1/executive-ai/draft-broadcast/",
        {"topic": "Annual General Meeting on Saturday"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "rule_based"
    assert "Annual General Meeting on Saturday" in body["draft"]


@patch("requests.post")
def test_summarize_pending_items_returns_ai_generated_summary(
    mock_post, settings, chairman_client
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    mock_post.return_value = _mock_claude_response(
        "Prioritize the 3 pending complaints first, then the welfare requests."
    )

    response = chairman_client.post(
        "/api/v1/executive-ai/summarize-pending/",
        {
            "jurisdiction_summary": {
                "organizational_unit": {"name": "National"},
                "pending_complaints": 3,
                "pending_discipline_cases": 0,
                "pending_welfare_requests": 2,
                "total_members": 500,
            }
        },
        format="json",
    )
    assert response.status_code == 200
    assert "complaints" in response.json()["summary"]


def test_summarize_pending_items_requires_the_summary_payload(chairman_client):
    response = chairman_client.post(
        "/api/v1/executive-ai/summarize-pending/", {}, format="json"
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_input"


@patch("requests.post")
def test_generate_meeting_agenda_returns_ai_generated_agenda(
    mock_post, settings, chairman_client
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    mock_post.return_value = _mock_claude_response(
        "1. Welcome (5 min)\n2. Budget review (30 min)\n3. AOB (10 min)"
    )

    response = chairman_client.post(
        "/api/v1/executive-ai/meeting-agenda/",
        {"meeting_topic": "Quarterly budget review"},
        format="json",
    )
    assert response.status_code == 200
    assert "Budget review" in response.json()["agenda"]


@patch("requests.post")
def test_meeting_agenda_forbidden_for_ordinary_member(mock_post, settings, auth_client):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    response = auth_client.post(
        "/api/v1/executive-ai/meeting-agenda/",
        {"meeting_topic": "Test"},
        format="json",
    )
    assert response.status_code == 403
    mock_post.assert_not_called()


def test_summarize_pending_items_falls_back_to_rule_based_when_unconfigured(
    settings, chairman_client
):
    settings.ANTHROPIC_API_KEY = ""
    response = chairman_client.post(
        "/api/v1/executive-ai/summarize-pending/",
        {
            "jurisdiction_summary": {
                "organizational_unit": {"name": "Test Region"},
                "pending_complaints": 3,
                "pending_discipline_cases": 1,
                "pending_welfare_requests": 2,
                "total_members": 500,
            }
        },
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "rule_based"
    assert "Test Region" in body["summary"]
    assert "3" in body["summary"]


def test_meeting_agenda_falls_back_to_rule_based_when_unconfigured(
    settings, chairman_client
):
    settings.ANTHROPIC_API_KEY = ""
    response = chairman_client.post(
        "/api/v1/executive-ai/meeting-agenda/",
        {"meeting_topic": "Budget Review"},
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "rule_based"
    assert "Budget Review" in body["agenda"]
