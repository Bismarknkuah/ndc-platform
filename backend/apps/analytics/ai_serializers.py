from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.analytics.documents import REPORT_TYPE_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class GenerateAIReportSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=REPORT_TYPE_CHOICES)
    organizational_unit_id = serializers.CharField()
    department_id = serializers.CharField(required=False, allow_null=True)

    def validate_organizational_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc


class AIGeneratedReportSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "report_type": instance.report_type,
            "organizational_unit": _unit_summary(instance.organizational_unit),
            "generated_by": _user_summary(instance.generated_by),
            "source_data": instance.source_data,
            "summary_text": instance.summary_text,
            "model_used": instance.model_used,
            "created_at": instance.created_at.isoformat(),
        }
