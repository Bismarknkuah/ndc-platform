from mongoengine import DateTimeField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.complaints.constants import COMPLAINT_STATUS_CHOICES, COMPLAINT_TYPE_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


class Complaint(TimestampedDocument):
    """
    A member's complaint or petition, addressed to their own unit or an
    ancestor of it (same rule as upward Reports - Branch can address
    Constituency directly, or go straight to National). A PETITION
    additionally accumulates co-signers via PetitionSupport.
    """

    submitted_by = ReferenceField(User, required=True)
    submitting_unit = ReferenceField(OrganizationalUnit, required=True)
    target_unit = ReferenceField(OrganizationalUnit, required=True)

    complaint_type = StringField(required=True, choices=COMPLAINT_TYPE_CHOICES)
    subject = StringField(required=True, max_length=200)
    description = StringField(required=True)

    status = StringField(choices=COMPLAINT_STATUS_CHOICES, default="SUBMITTED")
    assigned_to = ReferenceField(User, null=True)
    resolved_by = ReferenceField(User, null=True)
    resolved_at = DateTimeField(null=True)
    resolution_notes = StringField(default="")

    meta = {
        "collection": "complaints",
        "indexes": [
            "submitting_unit",
            "target_unit",
            "status",
            "complaint_type",
            "-created_at",
        ],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"[{self.complaint_type}] {self.subject}"


class PetitionSupport(TimestampedDocument):
    complaint = ReferenceField(Complaint, required=True)
    user = ReferenceField(User, required=True)

    meta = {
        "collection": "petition_supporters",
        "indexes": [{"fields": ["complaint", "user"], "unique": True}],
    }
