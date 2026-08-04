from mongoengine import (
    DateTimeField,
    DecimalField,
    ListField,
    ReferenceField,
    StringField,
)

from apps.accounts.documents import User
from apps.core.documents import TimestampedDocument
from apps.donations.constants import CAMPAIGN_STATUS_CHOICES, PLEDGE_STATUS_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


class FundraisingCampaign(TimestampedDocument):
    """A dedicated fundraising drive with a monetary goal - distinct from
    general one-off donations, which the Finance app's INCOME records
    already handle. Progress is computed from its Pledges, not stored."""

    title = StringField(required=True, max_length=200)
    description = StringField(default="")
    target_unit = ReferenceField(OrganizationalUnit, required=True)
    organized_by = ReferenceField(User, required=True)
    goal_amount = DecimalField(required=True, min_value=0, precision=2)
    currency = StringField(default="GHS", max_length=8)
    status = StringField(choices=CAMPAIGN_STATUS_CHOICES, default="PLANNING")
    start_date = DateTimeField(required=True)
    end_date = DateTimeField(required=True)

    meta = {
        "collection": "fundraising_campaigns",
        "indexes": ["target_unit", "status", "-created_at"],
        "ordering": ["-created_at"],
    }

    def __str__(self):
        return self.title


class Pledge(TimestampedDocument):
    """
    A commitment to donate toward a FundraisingCampaign - from a member
    (donor_user) or an external supporter (donor_name/donor_contact).
    Fulfilling a pledge (in full or in part) automatically creates a
    matching FinanceRecord income entry, same integration pattern as
    welfare disbursements.
    """

    campaign = ReferenceField(FundraisingCampaign, required=True)
    donor_user = ReferenceField(User, null=True)
    donor_name = StringField(null=True, max_length=200)
    donor_contact = StringField(null=True, max_length=100)

    pledged_amount = DecimalField(required=True, min_value=0, precision=2)
    fulfilled_amount = DecimalField(default=0, min_value=0, precision=2)
    status = StringField(choices=PLEDGE_STATUS_CHOICES, default="PLEDGED")

    recorded_by = ReferenceField(User, required=True)
    finance_records = ListField(ReferenceField("FinanceRecord"))

    meta = {
        "collection": "pledges",
        "indexes": ["campaign", "donor_user", "status", "-created_at"],
        "ordering": ["-created_at"],
    }

    @property
    def donor_display_name(self):
        return (
            self.donor_user.full_name
            if self.donor_user
            else (self.donor_name or "Anonymous")
        )

    def __str__(self):
        return f"{self.donor_display_name} pledged {self.currency_amount()}"

    def currency_amount(self):
        return f"{self.campaign.currency}{self.pledged_amount}"
