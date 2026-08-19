from decimal import Decimal

from rest_framework import serializers

from apps.welfare.constants import WELFARE_CATEGORY_CHOICES, WELFARE_STATUS_CHOICES


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class WelfareRequestSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    category = serializers.ChoiceField(choices=WELFARE_CATEGORY_CHOICES)
    description = serializers.CharField()
    amount_requested = serializers.DecimalField(
        max_digits=14, decimal_places=2, min_value=Decimal("0")
    )
    supporting_document_base64 = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    status = serializers.ChoiceField(choices=WELFARE_STATUS_CHOICES, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_supporting_document_base64(self, value):
        max_encoded_length = 2_800_000
        if value and len(value) > max_encoded_length:
            raise serializers.ValidationError(
                "Supporting document is too large (max ~2MB)."
            )
        return value

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "requester": _user_summary(instance.requester),
            "organizational_unit": _unit_summary(instance.organizational_unit),
            "category": instance.category,
            "description": instance.description,
            "amount_requested": str(instance.amount_requested),
            "supporting_document_base64": instance.supporting_document_base64,
            "status": instance.status,
            "reviewed_by": (
                _user_summary(instance.reviewed_by) if instance.reviewed_by else None
            ),
            "reviewed_at": (
                instance.reviewed_at.isoformat() if instance.reviewed_at else None
            ),
            "resolution_notes": instance.resolution_notes,
            "finance_record_id": (
                str(instance.finance_record.id) if instance.finance_record else None
            ),
            "created_at": instance.created_at.isoformat(),
        }
