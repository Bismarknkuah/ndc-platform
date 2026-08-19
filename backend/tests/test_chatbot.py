from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


# ---- Service layer ----


def test_generate_chat_reply_noop_without_configuration(settings, member_user):
    from apps.chatbot.services import generate_chat_reply

    settings.ANTHROPIC_API_KEY = ""
    result = generate_chat_reply(member_user, [{"role": "USER", "body": "Hi"}])
    assert result is None


@patch("requests.post")
def test_generate_chat_reply_calls_anthropic_when_configured(
    mock_post, settings, member_user
):
    from apps.chatbot.services import generate_chat_reply

    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [{"type": "text", "text": "You can find that under Analytics."}]
    }
    mock_post.return_value = mock_response

    result = generate_chat_reply(
        member_user, [{"role": "USER", "body": "Where do I see membership growth?"}]
    )
    assert result == "You can find that under Analytics."

    call_kwargs = mock_post.call_args[1]
    assert call_kwargs["headers"]["x-api-key"] == "sk-ant-test"
    assert call_kwargs["json"]["messages"][-1] == {
        "role": "user",
        "content": "Where do I see membership growth?",
    }
    # The system prompt must be personalized with the real caller's name,
    # not a generic placeholder.
    assert member_user.full_name in call_kwargs["json"]["system"]


@patch("requests.post")
def test_generate_chat_reply_returns_none_on_api_error(
    mock_post, settings, member_user
):
    from apps.chatbot.services import generate_chat_reply

    settings.ANTHROPIC_API_KEY = "sk-ant-test"

    def raise_error():
        raise Exception("500 error")

    mock_post.return_value = MagicMock(raise_for_status=raise_error)
    result = generate_chat_reply(member_user, [{"role": "USER", "body": "Hello"}])
    assert result is None


def test_generate_chat_reply_refuses_history_not_ending_on_user_turn(
    settings, member_user
):
    from apps.chatbot.services import generate_chat_reply

    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    result = generate_chat_reply(
        member_user, [{"role": "ASSISTANT", "body": "Hi there"}]
    )
    assert result is None


# ---- Endpoints ----


def test_any_authenticated_member_can_start_a_conversation(auth_client):
    """No permission gate on this feature - an ordinary member must be
    able to use it, matching the "available to every type of user"
    requirement."""
    response = auth_client.post("/api/v1/chatbot/conversations/", {}, format="json")
    assert response.status_code == 201
    assert response.data["title"] == "New conversation"


def test_conversation_list_only_shows_the_caller_s_own(auth_client, chairman_client):
    auth_client.post("/api/v1/chatbot/conversations/", {}, format="json")
    response = chairman_client.get("/api/v1/chatbot/conversations/")
    assert response.status_code == 200
    assert response.data["count"] == 0


@patch("requests.post")
def test_send_message_returns_both_messages_on_success(
    mock_post, settings, auth_client
):
    settings.ANTHROPIC_API_KEY = "sk-ant-test"
    mock_response = MagicMock()
    mock_response.raise_for_status = lambda: None
    mock_response.json.return_value = {
        "content": [
            {"type": "text", "text": "Head to the Elections tab to see live results."}
        ]
    }
    mock_post.return_value = mock_response

    create_response = auth_client.post(
        "/api/v1/chatbot/conversations/", {}, format="json"
    )
    conversation_id = create_response.data["id"]

    response = auth_client.post(
        f"/api/v1/chatbot/conversations/{conversation_id}/messages/",
        {"body": "How do I see election results?"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["user_message"]["role"] == "USER"
    assert response.data["user_message"]["body"] == "How do I see election results?"
    assert response.data["assistant_message"]["role"] == "ASSISTANT"
    assert "Elections tab" in response.data["assistant_message"]["body"]


def test_send_message_returns_503_when_unconfigured_but_still_saves_the_users_message(
    settings, auth_client
):
    settings.ANTHROPIC_API_KEY = ""
    create_response = auth_client.post(
        "/api/v1/chatbot/conversations/", {}, format="json"
    )
    conversation_id = create_response.data["id"]

    response = auth_client.post(
        f"/api/v1/chatbot/conversations/{conversation_id}/messages/",
        {"body": "Hello?"},
        format="json",
    )
    assert response.status_code == 503

    from apps.chatbot.documents import ChatMessage

    saved = ChatMessage.objects(role="USER")
    assert saved.count() == 1
    assert saved.first().body == "Hello?"


def test_cannot_read_someone_elses_conversation(auth_client, chairman_client):
    create_response = auth_client.post(
        "/api/v1/chatbot/conversations/", {}, format="json"
    )
    conversation_id = create_response.data["id"]

    response = chairman_client.get(
        f"/api/v1/chatbot/conversations/{conversation_id}/messages/"
    )
    assert response.status_code == 403


def test_archiving_a_conversation_hides_it_from_the_list(auth_client):
    create_response = auth_client.post(
        "/api/v1/chatbot/conversations/", {}, format="json"
    )
    conversation_id = create_response.data["id"]

    delete_response = auth_client.delete(
        f"/api/v1/chatbot/conversations/{conversation_id}/"
    )
    assert delete_response.status_code == 204

    list_response = auth_client.get("/api/v1/chatbot/conversations/")
    assert list_response.data["count"] == 0
