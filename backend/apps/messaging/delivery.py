"""
External notification delivery: email (SMTP, via Django's real mail
backend), SMS (Twilio's REST API), and push (Firebase Cloud Messaging's
legacy HTTP API). Every function here makes a real, correctly-formed call
to the actual provider - there is no simulated/fake success path. Without
credentials configured (via environment variables - see .env.example),
each channel logs a clear warning and no-ops rather than crashing the
request or pretending to have sent something.

Swap providers by editing only this file - callers (apps.messaging.
services.notify/notify_many) never know which provider is behind
send_email/send_sms/send_push.

Production note: these calls are currently synchronous (they block the
request they're called from). A production deployment should offload
them to a background task queue (Celery, RQ, Django-Q) rather than
making the API response wait on a third-party HTTP round-trip - that's
an infrastructure addition outside this phase's scope, but the function
boundaries here are exactly where a `.delay()` call would go.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail as django_send_mail

logger = logging.getLogger("ndc")


def send_email(to_email: str, subject: str, body: str) -> bool:
    """Real SMTP send via Django's mail backend. Configure EMAIL_HOST /
    EMAIL_HOST_USER / EMAIL_HOST_PASSWORD (see .env.example) - works with
    any SMTP provider (SendGrid, Mailgun, AWS SES SMTP, etc.)."""
    if not settings.EMAIL_HOST_USER:
        logger.info(
            "Email delivery skipped (EMAIL_HOST_USER not configured): to=%s subject=%s",
            to_email,
            subject,
        )
        return False
    try:
        django_send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Email delivery failed: to=%s subject=%s", to_email, subject)
        return False


def send_sms(to_phone: str, body: str) -> bool:
    """Real Twilio REST API call. Configure TWILIO_ACCOUNT_SID /
    TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER (see .env.example)."""
    if not (
        settings.TWILIO_ACCOUNT_SID
        and settings.TWILIO_AUTH_TOKEN
        and settings.TWILIO_FROM_NUMBER
    ):
        logger.info("SMS delivery skipped (Twilio not configured): to=%s", to_phone)
        return False
    try:
        import requests

        response = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            data={"To": to_phone, "From": settings.TWILIO_FROM_NUMBER, "Body": body},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        logger.exception("SMS delivery failed: to=%s", to_phone)
        return False


def send_push(push_token: str, title: str, body: str) -> bool:
    """
    Real FCM legacy HTTP API call. Configure FCM_SERVER_KEY (see
    .env.example). Note: Google has deprecated the legacy API in favor of
    the HTTP v1 API (which requires OAuth2 service-account credentials,
    more setup than a single server key) - this is a working starting
    point; migrate to HTTP v1 before the legacy endpoint's retirement.
    """
    if not settings.FCM_SERVER_KEY:
        logger.info(
            "Push delivery skipped (FCM_SERVER_KEY not configured): token=%s...",
            push_token[:12],
        )
        return False
    try:
        import requests

        response = requests.post(
            "https://fcm.googleapis.com/fcm/send",
            headers={
                "Authorization": f"key={settings.FCM_SERVER_KEY}",
                "Content-Type": "application/json",
            },
            json={"to": push_token, "notification": {"title": title, "body": body}},
            timeout=10,
        )
        response.raise_for_status()
        return True
    except Exception:
        logger.exception("Push delivery failed: token=%s...", push_token[:12])
        return False


def dispatch_external(user, title: str, body: str):
    """
    Checks the user's NotificationPreference and attempts each enabled
    channel. Each channel's failure is isolated - one failing channel
    (e.g. bad phone number) never blocks the others or the caller.
    """
    from apps.messaging.documents import NotificationPreference

    preference = NotificationPreference.objects(user=user).first()
    if preference is None:
        preference = NotificationPreference(
            user=user
        )  # defaults: email on, sms/push off

    if preference.email_enabled and user.email:
        try:
            send_email(user.email, title, body)
        except Exception:
            logger.exception("Unexpected error dispatching email to %s", user.email)

    if preference.sms_enabled and user.phone_number:
        try:
            send_sms(user.phone_number, f"{title}: {body}")
        except Exception:
            logger.exception(
                "Unexpected error dispatching SMS to %s", user.phone_number
            )

    if preference.push_enabled and preference.push_token:
        try:
            send_push(preference.push_token, title, body)
        except Exception:
            logger.exception("Unexpected error dispatching push to user %s", user.id)
