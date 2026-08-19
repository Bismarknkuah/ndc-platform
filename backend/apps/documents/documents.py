from mongoengine import BooleanField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.documents.constants import DOCUMENT_CATEGORY_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


class PartyDocument(TimestampedDocument):
    """
    A stored file - constitution, minutes, forms, policies, financial
    reports. Small operational documents (forms, short policies, single
    meeting minutes) are stored directly as base64 (capped ~5MB by the
    serializer); this is not meant for large media libraries - that needs
    real object storage (S3-compatible), which is a separate
    infrastructure decision. `organizational_unit` scopes visibility: the
    unit's own subtree can see it, plus any ancestor with hierarchy
    authority, unless `is_public_within_party` makes it visible to every
    member regardless of unit.
    """

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    category = StringField(required=True, choices=DOCUMENT_CATEGORY_CHOICES)
    organizational_unit = ReferenceField(OrganizationalUnit, required=True)
    uploaded_by = ReferenceField(User, required=True)

    file_base64 = StringField(required=True)
    file_name = StringField(required=True, max_length=255)
    mime_type = StringField(required=True, max_length=100)

    is_public_within_party = BooleanField(default=False)
    is_active = BooleanField(default=True)

    meta = {
        "collection": "party_documents",
        "indexes": [
            "organizational_unit",
            "category",
            "is_public_within_party",
            "-created_at",
        ],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"{self.title} ({self.category})"
