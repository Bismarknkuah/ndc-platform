from unittest.mock import MagicMock, patch

import pytest
from django.core import mail

pytestmark = pytest.mark.django_db


def test_send_email_noop_without_configuration(settings):
    from apps.messaging.delivery import send_email

    settings.EMAIL_HOST_USER = ""
    result = send_email("someone@example.com", "Subject", "Body")
    assert result is False
    assert len(mail.outbox) == 0


def test_send_email_sends_via_configured_smtp(settings):
    from apps.messaging.delivery import send_email

    settings.EMAIL_HOST_USER = "bot@ndc.example"
    settings.DEFAULT_FROM_EMAIL = "bot@ndc.example"
    result = send_email("someone@example.com", "Subject", "Body text")
    assert result is True
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Subject"
    assert mail.outbox[0].to == ["someone@example.com"]


def test_send_sms_noop_without_configuration(settings):
    from apps.messaging.delivery import send_sms

    settings.TWILIO_ACCOUNT_SID = ""
    result = send_sms("+233244000000", "Test message")
    assert result is False


@patch("requests.post")
def test_send_sms_calls_twilio_when_configured(mock_post, settings):
    from apps.messaging.delivery import send_sms

    settings.TWILIO_ACCOUNT_SID = "AC_test"
    settings.TWILIO_AUTH_TOKEN = "test_token"
    settings.TWILIO_FROM_NUMBER = "+15005550006"
    mock_post.return_value = MagicMock(status_code=201, raise_for_status=lambda: None)

    result = send_sms("+233244000000", "Test message")
    assert result is True
    mock_post.assert_called_once()
    call_args = mock_post.call_args
    assert "api.twilio.com" in call_args[0][0]
    assert call_args[1]["data"]["To"] == "+233244000000"
    assert call_args[1]["data"]["Body"] == "Test message"


@patch("requests.post")
def test_send_sms_returns_false_on_provider_error(mock_post, settings):
    from apps.messaging.delivery import send_sms

    settings.TWILIO_ACCOUNT_SID = "AC_test"
    settings.TWILIO_AUTH_TOKEN = "test_token"
    settings.TWILIO_FROM_NUMBER = "+15005550006"

    def raise_error():
        raise Exception("Twilio 400")

    mock_post.return_value = MagicMock(raise_for_status=raise_error)

    result = send_sms("+233244000000", "Test message")
    assert result is False


def test_send_push_noop_without_configuration(settings):
    from apps.messaging.delivery import send_push

    settings.FCM_SERVER_KEY = ""
    result = send_push("some-token", "Title", "Body")
    assert result is False


@patch("requests.post")
def test_send_push_calls_fcm_when_configured(mock_post, settings):
    from apps.messaging.delivery import send_push

    settings.FCM_SERVER_KEY = "test-server-key"
    mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)

    result = send_push("device-token-123", "Meeting reminder", "Starts in 10 minutes")
    assert result is True
    call_args = mock_post.call_args
    assert "fcm.googleapis.com" in call_args[0][0]
    assert call_args[1]["json"]["to"] == "device-token-123"


def test_dispatch_external_respects_preferences(member_user, settings):
    from apps.messaging.delivery import dispatch_external
    from apps.messaging.documents import NotificationPreference

    settings.EMAIL_HOST_USER = "bot@ndc.example"
    NotificationPreference.objects.create(
        user=member_user, email_enabled=False, sms_enabled=False, push_enabled=False
    )

    dispatch_external(member_user, "Title", "Body")
    assert len(mail.outbox) == 0


def test_dispatch_external_sends_email_when_enabled(member_user, settings):
    from apps.messaging.delivery import dispatch_external
    from apps.messaging.documents import NotificationPreference

    settings.EMAIL_HOST_USER = "bot@ndc.example"
    settings.DEFAULT_FROM_EMAIL = "bot@ndc.example"
    NotificationPreference.objects.create(user=member_user, email_enabled=True)

    dispatch_external(member_user, "Title", "Body")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [member_user.email]


def test_dispatch_external_defaults_to_email_enabled_when_no_preference_exists(
    member_user, settings
):
    from apps.messaging.delivery import dispatch_external

    settings.EMAIL_HOST_USER = "bot@ndc.example"
    settings.DEFAULT_FROM_EMAIL = "bot@ndc.example"

    dispatch_external(member_user, "Title", "Body")
    assert len(mail.outbox) == 1


def test_notify_triggers_external_dispatch(member_user, settings):
    settings.EMAIL_HOST_USER = "bot@ndc.example"
    settings.DEFAULT_FROM_EMAIL = "bot@ndc.example"

    from apps.messaging.services import notify

    notify(member_user, "BROADCAST", "New Directive", "Please review.")
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "New Directive"


def test_member_can_view_own_preferences(auth_client):
    response = auth_client.get("/api/v1/messaging/notification-preferences/")
    assert response.status_code == 200
    assert response.json()["email_enabled"] is True
    assert response.json()["sms_enabled"] is False


def test_member_can_update_own_preferences(auth_client):
    response = auth_client.put(
        "/api/v1/messaging/notification-preferences/",
        {"sms_enabled": True, "push_enabled": True, "push_token": "device-abc"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json()["sms_enabled"] is True
    assert response.json()["push_token"] == "device-abc"


def test_preferences_require_authentication(api_client):
    response = api_client.get("/api/v1/messaging/notification-preferences/")
    assert response.status_code == 401
