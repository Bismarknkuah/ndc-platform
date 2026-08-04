from decimal import Decimal

from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.finance.constants import RECORD_STATUS_CHOICES, RECORD_TYPE_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class FinanceRecordSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    record_type = serializers.ChoiceField(choices=RECORD_TYPE_CHOICES)
    category = serializers.CharField(max_length=100)
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )
    currency = serializers.CharField(max_length=8, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    organizational_unit_id = serializers.CharField(write_only=True)
    record_date = serializers.DateTimeField(required=False)
    receipt_photo_base64 = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    status = serializers.ChoiceField(choices=RECORD_STATUS_CHOICES, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_receipt_photo_base64(self, value):
        max_encoded_length = 2_800_000
        if value and len(value) > max_encoded_length:
            raise serializers.ValidationError("Receipt photo is too large (max ~2MB).")
        return value

    def validate_organizational_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "record_type": instance.record_type,
            "category": instance.category,
            "amount": str(instance.amount),
            "currency": instance.currency,
            "description": instance.description,
            "organizational_unit": _unit_summary(instance.organizational_unit),
            "recorded_by": _user_summary(instance.recorded_by),
            "record_date": instance.record_date.isoformat(),
            "receipt_photo_base64": instance.receipt_photo_base64,
            "status": instance.status,
            "approved_by": (
                _user_summary(instance.approved_by) if instance.approved_by else None
            ),
            "approved_at": (
                instance.approved_at.isoformat() if instance.approved_at else None
            ),
            "created_at": instance.created_at.isoformat(),
        }
