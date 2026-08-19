from drf_spectacular.utils import extend_schema_field
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.events.constants import (
    CAMPAIGN_STATUS_CHOICES,
    EVENT_STATUS_CHOICES,
    EVENT_TYPE_CHOICES,
    RSVP_STATUS_CHOICES,
)
from apps.events.documents import Campaign
from apps.hierarchy.documents import OrganizationalUnit


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class CampaignSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    goal_description = serializers.CharField(required=False, allow_blank=True)
    target_unit_id = serializers.CharField(write_only=True)
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
            "goal_description": instance.goal_description,
            "target_unit": _unit_summary(instance.target_unit),
            "organized_by": _user_summary(instance.organized_by),
            "status": instance.status,
            "start_date": instance.start_date.isoformat(),
            "end_date": instance.end_date.isoformat(),
            "created_at": instance.created_at.isoformat(),
        }


class EventSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    event_type = serializers.ChoiceField(choices=EVENT_TYPE_CHOICES)
    campaign_id = serializers.CharField(
        required=False, allow_null=True, write_only=True
    )
    target_unit_id = serializers.CharField(write_only=True)
    location = serializers.CharField(required=False, allow_blank=True, max_length=255)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=EVENT_STATUS_CHOICES, required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_campaign_id(self, value):
        if not value:
            return None
        try:
            return Campaign.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Campaign not found.") from exc

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
        return {
            "id": str(instance.id),
            "title": instance.title,
            "description": instance.description,
            "event_type": instance.event_type,
            "campaign": (
                {"id": str(instance.campaign.id), "title": instance.campaign.title}
                if instance.campaign
                else None
            ),
            "target_unit": _unit_summary(instance.target_unit),
            "organizer": _user_summary(instance.organizer),
            "location": instance.location,
            "scheduled_start": instance.scheduled_start.isoformat(),
            "scheduled_end": instance.scheduled_end.isoformat(),
            "status": instance.status,
            "created_at": instance.created_at.isoformat(),
        }


class EventUserSummarySerializer(serializers.Serializer):
    id = serializers.CharField()
    full_name = serializers.CharField()
    membership_id = serializers.CharField()


class EventRSVPSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=RSVP_STATUS_CHOICES)


class EventRSVPRecordSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    status = serializers.CharField()
    responded_at = serializers.DateTimeField()

    @extend_schema_field(EventUserSummarySerializer)
    def get_user(self, obj):
        return _user_summary(obj.user)
