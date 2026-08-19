from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.events.documents import Event
from apps.hierarchy.documents import OrganizationalUnit
from apps.volunteers.constants import OPPORTUNITY_STATUS_CHOICES, SIGNUP_STATUS_CHOICES


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class VolunteerProfileSerializer(serializers.Serializer):
    skills = serializers.ListField(
        child=serializers.CharField(max_length=100), required=False
    )
    availability_notes = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)

    def to_representation(self, instance):
        return {
            "user": _user_summary(instance.user),
            "skills": instance.skills,
            "availability_notes": instance.availability_notes,
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat(),
        }


class VolunteerOpportunitySerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    event_id = serializers.CharField(required=False, allow_null=True, write_only=True)
    target_unit_id = serializers.CharField(write_only=True)
    needed_count = serializers.IntegerField(min_value=1)
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=OPPORTUNITY_STATUS_CHOICES, required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_event_id(self, value):
        if not value:
            return None
        try:
            return Event.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Event not found.") from exc

    def validate_target_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def validate(self, attrs):
        start = attrs.get(
            "scheduled_start", getattr(self.instance, "scheduled_start", None)
        )
        end = attrs.get("scheduled_end", getattr(self.instance, "scheduled_end", None))
        if start and end and end <= start:
            raise serializers.ValidationError(
                {"scheduled_end": "Must be after scheduled_start."}
            )
        return attrs

    def to_representation(self, instance):
        from apps.volunteers.documents import VolunteerSignup

        filled_count = VolunteerSignup.objects(
            opportunity=instance, status__in=["SIGNED_UP", "CONFIRMED"]
        ).count()
        return {
            "id": str(instance.id),
            "title": instance.title,
            "description": instance.description,
            "event": (
                {"id": str(instance.event.id), "title": instance.event.title}
                if instance.event
                else None
            ),
            "target_unit": _unit_summary(instance.target_unit),
            "organizer": _user_summary(instance.organizer),
            "needed_count": instance.needed_count,
            "filled_count": filled_count,
            "location": instance.location,
            "scheduled_start": instance.scheduled_start.isoformat(),
            "scheduled_end": instance.scheduled_end.isoformat(),
            "status": instance.status,
            "created_at": instance.created_at.isoformat(),
        }


class VolunteerSignupSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    status = serializers.ChoiceField(choices=SIGNUP_STATUS_CHOICES, required=False)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "volunteer": _user_summary(instance.volunteer),
            "status": instance.status,
            "signed_up_at": instance.signed_up_at.isoformat(),
        }
