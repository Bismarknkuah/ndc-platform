from mongoengine import BooleanField, DateTimeField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.complaints.constants import COMPLAINT_STATUS_CHOICES, COMPLAINT_TYPE_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


class Complaint(TimestampedDocument):
    """
    A member's complaint, petition, or accountability report about a
    specific executive, addressed to their own unit or an ancestor of
    it (same rule as upward Reports - Branch can address Constituency
    directly, or go straight to National). A PETITION additionally
    accumulates co-signers via PetitionSupport.

    is_anonymous never means the submitter's identity is discarded -
    submitted_by is always stored, since silently-untraceable reports
    are themselves an abuse vector and real accountability requires
    being able to investigate bad-faith reports. What is_anonymous
    actually controls is display: reporter_display_name() below
    returns "Anonymous" unless the caller specifically holds reveal
    authority, regardless of what is technically stored in the
    database.
    """

    submitted_by = ReferenceField(User, required=True)
    submitting_unit = ReferenceField(OrganizationalUnit, required=True)
    target_unit = ReferenceField(OrganizationalUnit, required=True)

    # Who this complaint is *about*, when it is an ACCOUNTABILITY_REPORT
    # against a specific executive - separate from submitted_by, who
    # filed it. Null for an ordinary COMPLAINT/PETITION not about a
    # specific person.
    reported_user = ReferenceField(User, null=True)
    is_anonymous = BooleanField(default=False)

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
            "reported_user",
            "status",
            "complaint_type",
            "-created_at",
        ],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return f"[{self.complaint_type}] {self.subject}"

    def reporter_display_name(self, viewer) -> str:
        """The one place that decides whether a viewer sees the real
        reporter's name or "Anonymous" - callers must always go through
        this rather than reading submitted_by.full_name directly, so
        the anonymity rule can never be accidentally bypassed by a new
        serializer or report forgetting to check it."""
        from apps.complaints.permissions import can_reveal_reporter_identity

        if not self.is_anonymous or can_reveal_reporter_identity(viewer, self):
            return self.submitted_by.full_name
        return "Anonymous"


class PetitionSupport(TimestampedDocument):
    complaint = ReferenceField(Complaint, required=True)
    user = ReferenceField(User, required=True)

    meta = {
        "collection": "petition_supporters",
        "indexes": [{"fields": ["complaint", "user"], "unique": True}],
    }
