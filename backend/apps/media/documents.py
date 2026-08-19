from mongoengine import BooleanField, ListField, ReferenceField, StringField, URLField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.events.documents import Event
from apps.hierarchy.documents import OrganizationalUnit
from apps.media.constants import MEDIA_TYPE_CHOICES


class MediaAsset(TimestampedDocument):
    """
    A photo, video, audio clip, or press clipping. Small photos can be
    stored directly (base64-in-Mongo, capped ~5MB, same pattern used
    throughout); video/audio and anything larger is referenced by
    `external_url` (YouTube, Vimeo, an S3 bucket, ...) rather than stored
    here - a full media/CDN pipeline is a separate infrastructure decision
    outside this phase's scope, same honest boundary as document storage.
    Exactly one of file_base64 / external_url is required.
    """

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    media_type = StringField(required=True, choices=MEDIA_TYPE_CHOICES)
    tags = ListField(StringField(max_length=50), default=list)

    organizational_unit = ReferenceField(OrganizationalUnit, required=True)
    uploaded_by = ReferenceField(User, required=True)
    event = ReferenceField(Event, null=True)

    file_base64 = StringField(null=True)
    external_url = URLField(null=True)

    is_public_within_party = BooleanField(default=False)
    is_active = BooleanField(default=True)

    meta = {
        "collection": "media_assets",
        "indexes": [
            "organizational_unit",
            "media_type",
            "event",
            "is_public_within_party",
            "-created_at",
        ],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"{self.title} ({self.media_type})"
