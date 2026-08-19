import datetime

from mongoengine import (
    BooleanField,
    DateTimeField,
    IntField,
    ListField,
    ReferenceField,
    StringField,
)

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.events.documents import Event
from apps.hierarchy.documents import OrganizationalUnit
from apps.volunteers.constants import OPPORTUNITY_STATUS_CHOICES, SIGNUP_STATUS_CHOICES


class VolunteerProfile(TimestampedDocument):
    """A member's opt-in volunteer registry entry - skills and general
    availability, independent of any specific opportunity."""

    user = ReferenceField(User, required=True, unique=True)
    skills = ListField(StringField(), default=list)
    availability_notes = StringField(default="")
    is_active = BooleanField(default=True)

    meta = {
        "collection": "volunteer_profiles",
        "indexes": [{"fields": ["user"], "unique": True}],
    }

    def __str__(self):
        return f"Volunteer profile: {self.user.full_name}"


class VolunteerOpportunity(TimestampedDocument):
    """A specific need for volunteers - optionally tied to an Event
    (e.g. "10 ushers needed for the National Rally")."""

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    event = ReferenceField(Event, null=True)
    target_unit = ReferenceField(OrganizationalUnit, required=True)
    organizer = ReferenceField(User, required=True)
    needed_count = IntField(required=True, min_value=1)
    location = StringField(default="", max_length=255)
    scheduled_start = DateTimeField(required=True)
    scheduled_end = DateTimeField(required=True)
    status = StringField(choices=OPPORTUNITY_STATUS_CHOICES, default="OPEN")

    meta = {
        "collection": "volunteer_opportunities",
        "indexes": ["target_unit", "event", "status", "-scheduled_start"],
        "ordering": ["-scheduled_start"],
    }

    def __str__(self):
        return f"{self.title} ({self.needed_count} needed)"


class VolunteerSignup(TimestampedDocument):
    opportunity = ReferenceField(VolunteerOpportunity, required=True)
    volunteer = ReferenceField(User, required=True)
    status = StringField(choices=SIGNUP_STATUS_CHOICES, default="SIGNED_UP")
    signed_up_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {
        "collection": "volunteer_signups",
        "indexes": [{"fields": ["opportunity", "volunteer"], "unique": True}],
    }
