from decimal import Decimal

from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.accounts.documents import User
from apps.donations.constants import CAMPAIGN_STATUS_CHOICES, PLEDGE_STATUS_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class FundraisingCampaignSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    target_unit_id = serializers.CharField(write_only=True)
    goal_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )
    currency = serializers.CharField(max_length=8, required=False)
    status = serializers.ChoiceField(choices=CAMPAIGN_STATUS_CHOICES, required=False)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    created_at = serializers.DateTimeField(read_only=True)

    def validate_target_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end <= start:
            raise serializers.ValidationError({"end_date": "Must be after start_date."})
        return attrs

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "title": instance.title,
            "description": instance.description,
            "target_unit": _unit_summary(instance.target_unit),
            "organized_by": _user_summary(instance.organized_by),
            "goal_amount": str(instance.goal_amount),
            "currency": instance.currency,
            "status": instance.status,
            "start_date": instance.start_date.isoformat(),
            "end_date": instance.end_date.isoformat(),
            "created_at": instance.created_at.isoformat(),
        }


class PledgeSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    campaign_id = serializers.CharField(write_only=True)
    donor_user_id = serializers.CharField(
        required=False, allow_null=True, write_only=True
    )
    donor_name = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=200
    )
    donor_contact = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, max_length=100
    )
    pledged_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )
    status = serializers.ChoiceField(choices=PLEDGE_STATUS_CHOICES, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_campaign_id(self, value):
        from apps.donations.documents import FundraisingCampaign

        try:
            return FundraisingCampaign.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Campaign not found.") from exc

    def validate_donor_user_id(self, value):
        if not value:
            return None
        try:
            return User.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Donor user not found.") from exc

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "campaign_id": str(instance.campaign.id),
            "donor_display_name": instance.donor_display_name,
            "donor_user": (
                _user_summary(instance.donor_user) if instance.donor_user else None
            ),
            "donor_name": instance.donor_name,
            "donor_contact": instance.donor_contact,
            "pledged_amount": str(instance.pledged_amount),
            "fulfilled_amount": str(instance.fulfilled_amount),
            "status": instance.status,
            "recorded_by": _user_summary(instance.recorded_by),
            "finance_record_ids": [str(r.id) for r in instance.finance_records],
            "created_at": instance.created_at.isoformat(),
        }


class FulfillPledgeSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0.01")
    )
