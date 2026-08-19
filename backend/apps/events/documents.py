import datetime

from mongoengine import DateTimeField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.events.constants import (
    CAMPAIGN_STATUS_CHOICES,
    EVENT_STATUS_CHOICES,
    EVENT_TYPE_CHOICES,
    RSVP_STATUS_CHOICES,
)
from apps.hierarchy.documents import OrganizationalUnit


class Campaign(TimestampedDocument):
    """
    An umbrella container for a set of Events working toward a shared goal
    - a get-out-the-vote drive, a membership registration push, a
    fundraising campaign. Events don't need a Campaign (a one-off rally
    doesn't need one), but grouping related events under one lets a
    Region/Constituency track a coordinated push as a whole.
    """

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    goal_description = StringField(default="")
    target_unit = ReferenceField(OrganizationalUnit, required=True)
    organized_by = ReferenceField(User, required=True)
    status = StringField(choices=CAMPAIGN_STATUS_CHOICES, default="PLANNING")
    start_date = DateTimeField(required=True)
    end_date = DateTimeField(required=True)

    meta = {
        "collection": "campaigns",
        "indexes": ["target_unit", "status", "-created_at"],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return self.title


class Event(TimestampedDocument):
    """A scheduled event - a rally, town hall, fundraiser, or other
    on-the-ground activity, optionally part of a Campaign."""

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    event_type = StringField(required=True, choices=EVENT_TYPE_CHOICES)
    campaign = ReferenceField(Campaign, null=True)
    target_unit = ReferenceField(OrganizationalUnit, required=True)
    organizer = ReferenceField(User, required=True)
    location = StringField(default="", max_length=255)
    scheduled_start = DateTimeField(required=True)
    scheduled_end = DateTimeField(required=True)
    status = StringField(choices=EVENT_STATUS_CHOICES, default="SCHEDULED")

    meta = {
        "collection": "events",
        "indexes": ["target_unit", "campaign", "status", "-scheduled_start"],
        "ordering": ["-scheduled_start"],
    }

    def __str__(self):
        return f"{self.title} @ {self.scheduled_start.isoformat()}"


class EventRSVP(TimestampedDocument):
    event = ReferenceField(Event, required=True)
    user = ReferenceField(User, required=True)
    status = StringField(required=True, choices=RSVP_STATUS_CHOICES)
    responded_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "event_rsvps",
        "indexes": [{"fields": ["event", "user"], "unique": True}],
    }
