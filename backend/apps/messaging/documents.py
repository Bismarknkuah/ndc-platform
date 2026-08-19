import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    EmbeddedDocument,
    EmbeddedDocumentListField,
    ListField,
    ReferenceField,
    StringField,
)

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.departments.documents import Department
from apps.hierarchy.documents import OrganizationalUnit
from apps.messaging.constants import (
    BROADCAST_KIND_CHOICES,
    MEETING_STATUS_CHOICES,
    MEETING_TYPE_CHOICES,
    NOTIFICATION_TYPE_CHOICES,
    PRIORITY_CHOICES,
    REPORT_STATUS_CHOICES,
    RSVP_STATUS_CHOICES,
)


class Broadcast(TimestampedDocument):
    """
    A downward communication from `issued_by` to every member in
    `target_unit`'s subtree - National -> Branch. `kind` distinguishes an
    action-required DIRECTIVE from a purely informational ANNOUNCEMENT;
    both share the same delivery/acknowledgement machinery.
    """

    title = StringField(required=True, max_length=200)
    body = StringField(required=True)
    kind = StringField(required=True, choices=BROADCAST_KIND_CHOICES)
    priority = StringField(choices=PRIORITY_CHOICES, default="NORMAL")

    issued_by = ReferenceField(User, required=True)
    target_unit = ReferenceField(OrganizationalUnit, required=True)
    requires_acknowledgement = BooleanField(default=False)

    meta = {
        "collection": "broadcasts",
        "indexes": ["target_unit", "issued_by", "-created_at"],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"[{self.kind}] {self.title}"


class BroadcastAcknowledgement(TimestampedDocument):
    broadcast = ReferenceField(Broadcast, required=True)
    user = ReferenceField(User, required=True)
    acknowledged_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "broadcast_acknowledgements",
        "indexes": [{"fields": ["broadcast", "user"], "unique": True}],
    }


class Report(TimestampedDocument):
    """
    An upward report - Branch -> National (or any ancestor in between).
    `submitting_unit` defaults to the submitter's own unit; `target_unit`
    must be that unit or an ancestor of it.
    """

    title = StringField(required=True, max_length=200)
    body = StringField(required=True)

    submitted_by = ReferenceField(User, required=True)
    submitting_unit = ReferenceField(OrganizationalUnit, required=True)
    target_unit = ReferenceField(OrganizationalUnit, required=True)

    status = StringField(choices=REPORT_STATUS_CHOICES, default="SUBMITTED")
    resolved_by = ReferenceField(User, null=True)
    resolution_notes = StringField(default="")

    meta = {
        "collection": "reports",
        "indexes": ["submitting_unit", "target_unit", "status", "-created_at"],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"{self.title} ({self.submitting_unit.name} -> {self.target_unit.name})"


class DiscussionGroup(TimestampedDocument):
    name = StringField(required=True, max_length=150)
    description = StringField(default="")
    organizational_unit = ReferenceField(OrganizationalUnit, null=True)
    created_by = ReferenceField(User, required=True)
    members = ListField(ReferenceField(User))
    is_active = BooleanField(default=True)

    meta = {
        "collection": "discussion_groups",
        "indexes": ["members", "organizational_unit"],
    }

    def __str__(self):
        return self.name


class GroupMessage(TimestampedDocument):
    group = ReferenceField(DiscussionGroup, required=True)
    sender = ReferenceField(User, required=True)
    body = StringField(required=True)

    meta = {
        "collection": "group_messages",
        "indexes": ["group", "-created_at"],
        "ordering": ["-created_at"],
    }


class DirectMessage(TimestampedDocument):
    sender = ReferenceField(User, required=True)
    recipient = ReferenceField(User, required=True)
    body = StringField(required=True)
    read_at = DateTimeField(null=True)

    meta = {
        "collection": "direct_messages",
        "indexes": ["sender", "recipient", "-created_at"],
        "ordering": ["-created_at"],
    }


class Notification(TimestampedDocument):
    user = ReferenceField(User, required=True)
    notification_type = StringField(required=True, choices=NOTIFICATION_TYPE_CHOICES)
    title = StringField(required=True, max_length=200)
    body = StringField(default="")
    target_type = StringField(null=True)
    target_id = StringField(null=True)
    is_read = BooleanField(default=False)
    read_at = DateTimeField(null=True)

    meta = {
        "collection": "notifications",
        "indexes": ["user", "is_read", "-created_at"],
        "ordering": ["-created_at"],
    }

    def mark_read(self):
        self.is_read = True
        self.read_at = datetime.datetime.utcnow()


class Meeting(TimestampedDocument):
    """
    A scheduled meeting or training workshop with a real, working video
    room link. Audience is computed the same way as broadcasts: everyone
    in `target_unit`'s subtree, or - if `department` is set - just that
    department's team members within the subtree (e.g. "the National
    Communications team meeting" vs. "a Regional general meeting").

    Live audio/video/screen-share is provided by generating a Jitsi Meet
    room (meet.jit.si) rather than building custom WebRTC infrastructure -
    that's a specialized media-server/TURN-server problem that belongs to
    a dedicated conferencing provider, not something to reimplement here.
    An Enterprise deployment can point `meeting_url` generation at a
    self-hosted Jitsi instance, or swap in Zoom/Google Meet, by changing
    one function (apps.messaging.services.generate_meeting_room_url).
    """

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    meeting_type = StringField(required=True, choices=MEETING_TYPE_CHOICES)

    department = ReferenceField(Department, null=True)
    target_unit = ReferenceField(OrganizationalUnit, required=True)
    host = ReferenceField(User, required=True)

    scheduled_start = DateTimeField(required=True)
    scheduled_end = DateTimeField(required=True)
    meeting_url = StringField(required=True)

    status = StringField(choices=MEETING_STATUS_CHOICES, default="SCHEDULED")

    meta = {
        "collection": "meetings",
        "indexes": ["target_unit", "department", "host", "-scheduled_start"],
        "ordering": ["-scheduled_start"],
    }

    def __str__(self):
        return (
            f"[{self.meeting_type}] {self.title} @ {self.scheduled_start.isoformat()}"
        )


class MeetingRSVP(TimestampedDocument):
    meeting = ReferenceField(Meeting, required=True)
    user = ReferenceField(User, required=True)
    status = StringField(required=True, choices=RSVP_STATUS_CHOICES)
    responded_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "meeting_rsvps",
        "indexes": [{"fields": ["meeting", "user"], "unique": True}],
    }


class ActionItem(EmbeddedDocument):
    description = StringField(required=True)
    assigned_to = ReferenceField(User, null=True)
    due_date = DateTimeField(null=True)
    is_done = BooleanField(default=False)


class MeetingMinutes(TimestampedDocument):
    """
    The official record of what happened in a Meeting - one set of minutes
    per meeting. Attendees default to everyone who RSVP'd ATTENDING, but
    can be overridden (e.g. someone attended without RSVPing).
    """

    meeting = ReferenceField(Meeting, required=True, unique=True)
    recorded_by = ReferenceField(User, required=True)
    summary = StringField(default="")
    decisions = StringField(default="")
    attendees = ListField(ReferenceField(User))
    action_items = EmbeddedDocumentListField(ActionItem)

    meta = {
        "collection": "meeting_minutes",
        "indexes": [{"fields": ["meeting"], "unique": True}],
    }

    def __str__(self):
        return f"Minutes for {self.meeting.title}"


class NotificationPreference(TimestampedDocument):
    """
    Per-user opt-in/out for external delivery channels. In-app
    notifications (the Notification model) are always created regardless
    of these settings - this only controls whether we *additionally* try
    to reach the member by email/SMS/push.
    """

    user = ReferenceField(User, required=True, unique=True)
    email_enabled = BooleanField(default=True)
    sms_enabled = BooleanField(default=False)
    push_enabled = BooleanField(default=False)
    push_token = StringField(null=True)

    meta = {
        "collection": "notification_preferences",
        "indexes": [{"fields": ["user"], "unique": True}],
    }
