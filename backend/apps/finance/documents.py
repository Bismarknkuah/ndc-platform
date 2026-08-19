import datetime

from mongoengine import DateTimeField, DecimalField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.finance.constants import RECORD_STATUS_CHOICES, RECORD_TYPE_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


class FinanceRecord(TimestampedDocument):
    """
    One income or expense entry, attributed to a specific organizational
    unit (a Branch's dues collection, a Region's rally costs, National's
    fundraising gala). `status` gives a lightweight approval workflow:
    anyone with finance authority at a unit can record a PENDING entry,
    but only finance authority at that unit or an ancestor of it can
    APPROVE/REJECT it (mirroring the collation verification pattern).
    """

    record_type = StringField(required=True, choices=RECORD_TYPE_CHOICES)
    category = StringField(required=True, max_length=100)
    amount = DecimalField(required=True, min_value=0, precision=2)
    currency = StringField(default="GHS", max_length=8)
    description = StringField(default="")
    organizational_unit = ReferenceField(OrganizationalUnit, required=True)

    recorded_by = ReferenceField(User, required=True)
    record_date = DateTimeField(default=datetime.datetime.utcnow)

    status = StringField(choices=RECORD_STATUS_CHOICES, default="PENDING")
    approved_by = ReferenceField(User, null=True)
    approved_at = DateTimeField(null=True)

    # Photographic evidence of a receipt/invoice - same base64-in-Mongo
    # pattern used for candidate photos and collation sheets.
    receipt_photo_base64 = StringField(null=True)

    meta = {
        "collection": "finance_records",
        "indexes": ["organizational_unit", "record_type", "status", "-record_date"],
        "ordering": ["-record_date"],
    }

    def mark_approved(self, by_user):
        self.status = "APPROVED"
        self.approved_by = by_user
        self.approved_at = datetime.datetime.utcnow()

    def mark_rejected(self, by_user):
        self.status = "REJECTED"
        self.approved_by = by_user
        self.approved_at = datetime.datetime.utcnow()

    def __str__(self):
        return f"{self.record_type} {self.currency}{self.amount} - {self.category} @ {self.organizational_unit.name}"
