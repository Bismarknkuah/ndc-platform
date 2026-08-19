from mongoengine import DateTimeField, DecimalField, ReferenceField, StringField

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.dues.constants import DUES_PAYMENT_STATUS_CHOICES


class DuesPayment(TimestampedDocument):
    """
    One membership dues payment attempt, initiated by the member
    themselves through their own portal. `paystack_reference` is
    created locally (not by Paystack) and passed to Paystack's
    initialize call, so it's known and unique before any external call
    is even made. `finance_record` is only set once the payment is
    confirmed SUCCESS - same "external payment confirmation creates a
    real FinanceRecord income entry" pattern already used for donation
    pledge fulfillment.
    """

    user = ReferenceField(User, required=True)
    amount = DecimalField(required=True, min_value=0, precision=2)
    currency = StringField(default="GHS", max_length=8)
    period = StringField(
        required=True,
        max_length=20,
        help_text="Which period these dues cover, e.g. '2026-08' for August 2026.",
    )
    paystack_reference = StringField(required=True, unique=True)
    status = StringField(choices=DUES_PAYMENT_STATUS_CHOICES, default="PENDING")
    payment_method = StringField(null=True, max_length=30)
    paid_at = DateTimeField(null=True)
    finance_record = ReferenceField("FinanceRecord", null=True)

    meta = {
        "collection": "dues_payments",
        "indexes": [
            {"fields": ["paystack_reference"], "unique": True},
            "user",
            "-created_at",
        ],
        "ordering": ["-created_at"],
    }
