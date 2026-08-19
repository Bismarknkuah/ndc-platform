import datetime

from mongoengine import DateTimeField, DecimalField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.hierarchy.documents import OrganizationalUnit
from apps.welfare.constants import WELFARE_CATEGORY_CHOICES, WELFARE_STATUS_CHOICES


class WelfareRequest(TimestampedDocument):
    """
    A member's request for party welfare support - bereavement, medical,
    educational, or emergency assistance. Filed at the requester's own
    unit; reviewed/approved by finance or hierarchy authority over that
    unit or an ancestor of it. Approving and marking DISBURSED
    automatically creates the corresponding FinanceRecord expense entry,
    so welfare payouts are never invisible to the books.
    """

    requester = ReferenceField(User, required=True)
    organizational_unit = ReferenceField(OrganizationalUnit, required=True)
    category = StringField(required=True, choices=WELFARE_CATEGORY_CHOICES)
    description = StringField(required=True)
    amount_requested = DecimalField(required=True, min_value=0, precision=2)

    status = StringField(choices=WELFARE_STATUS_CHOICES, default="SUBMITTED")
    reviewed_by = ReferenceField(User, null=True)
    reviewed_at = DateTimeField(null=True)
    resolution_notes = StringField(default="")

    # Evidence: death certificate, medical bill, etc. Same base64-in-Mongo
    # pattern used throughout, capped at ~2MB by the serializer.
    supporting_document_base64 = StringField(null=True)

    finance_record = ReferenceField("FinanceRecord", null=True)

    meta = {
        "collection": "welfare_requests",
        "indexes": ["organizational_unit", "status", "-created_at"],
        "ordering": ["-created_at"],
    }

    def mark_reviewed(self, by_user, new_status, notes=""):
        self.status = new_status
        self.reviewed_by = by_user
        self.reviewed_at = datetime.datetime.utcnow()
        if notes:
            self.resolution_notes = notes

    def __str__(self):
        return f"{self.category} request by {self.requester.full_name} - {self.status}"
