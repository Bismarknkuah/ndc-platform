from apps.accounts.documents import User
from apps.messaging.documents import Notification


def generate_meeting_room_url(title: str) -> str:
    """
    Generates a real, working video-conferencing room link - no API key or
    signup required (meet.jit.si is Jitsi's free public instance). Swap
    this one function to point at a self-hosted Jitsi instance, or a
    Zoom/Google Meet integration, without touching any calling code.
    """
    import re
    import secrets

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-")[:40] or "NDC-Meeting"
    return f"https://meet.jit.si/NDC-{slug}-{secrets.token_urlsafe(6)}"


def units_in_subtree(unit):
    """The unit itself plus every descendant - used to resolve a broadcast's audience."""
    return [unit] + unit.get_descendants()


def users_in_subtree(unit, exclude_user=None):
    unit_ids = [u.id for u in units_in_subtree(unit)]
    qs = User.objects(organizational_unit__in=unit_ids, is_active=True)
    if exclude_user is not None:
        qs = qs.filter(id__ne=exclude_user.id)
    return list(qs)


def notify(user, notification_type, title, body="", target=None):
    Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        body=body,
        target_type=target.__class__.__name__ if target is not None else None,
        target_id=str(target.id) if target is not None else None,
    )

    from apps.messaging.delivery import dispatch_external

    try:
        dispatch_external(user, title, body)
    except Exception:
        # External delivery is best-effort and must never break the
        # in-app notification, which has already been saved above.
        import logging

        logging.getLogger("ndc").exception(
            "dispatch_external failed for user %s", user.id
        )


def notify_many(users, notification_type, title, body="", target=None):
    for user in users:
        notify(user, notification_type, title, body=body, target=target)
