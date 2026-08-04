from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.complaints.constants import COMPLAINT_STATUS_CHOICES, COMPLAINT_TYPE_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class ComplaintSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    complaint_type = serializers.ChoiceField(choices=COMPLAINT_TYPE_CHOICES)
    subject = serializers.CharField(max_length=200)
    description = serializers.CharField()
    target_unit_id = serializers.CharField(write_only=True)
    status = serializers.ChoiceField(choices=COMPLAINT_STATUS_CHOICES, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_target_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "complaint_type": instance.complaint_type,
            "subject": instance.subject,
            "description": instance.description,
            "submitted_by": _user_summary(instance.submitted_by),
            "submitting_unit": _unit_summary(instance.submitting_unit),
            "target_unit": _unit_summary(instance.target_unit),
            "status": instance.status,
            "assigned_to": (
                _user_summary(instance.assigned_to) if instance.assigned_to else None
            ),
            "resolved_by": (
                _user_summary(instance.resolved_by) if instance.resolved_by else None
            ),
            "resolved_at": (
                instance.resolved_at.isoformat() if instance.resolved_at else None
            ),
            "resolution_notes": instance.resolution_notes,
            "created_at": instance.created_at.isoformat(),
        }
