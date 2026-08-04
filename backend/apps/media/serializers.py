from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.events.documents import Event
from apps.hierarchy.documents import OrganizationalUnit
from apps.media.constants import MEDIA_TYPE_CHOICES


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class MediaAssetSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    media_type = serializers.ChoiceField(choices=MEDIA_TYPE_CHOICES)
    tags = serializers.ListField(
        child=serializers.CharField(max_length=50), required=False
    )
    organizational_unit_id = serializers.CharField(write_only=True)
    event_id = serializers.CharField(required=False, allow_null=True, write_only=True)
    file_base64 = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )
    external_url = serializers.URLField(
        required=False, allow_null=True, allow_blank=True
    )
    is_public_within_party = serializers.BooleanField(required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_file_base64(self, value):
        max_encoded_length = 7_000_000  # ~5MB after base64 expansion
        if value and len(value) > max_encoded_length:
            raise serializers.ValidationError(
                "File is too large (max ~5MB) - use external_url for larger media."
            )
        return value

    def validate_organizational_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def validate_event_id(self, value):
        if not value:
            return None
        try:
            return Event.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Event not found.") from exc

    def validate(self, attrs):
        if not attrs.get("file_base64") and not attrs.get("external_url"):
            raise serializers.ValidationError(
                {
                    "external_url": "Provide either file_base64 (small media) or external_url (large media)."
                }
            )
        return attrs

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "title": instance.title,
            "description": instance.description,
            "media_type": instance.media_type,
            "tags": instance.tags,
            "organizational_unit": _unit_summary(instance.organizational_unit),
            "uploaded_by": _user_summary(instance.uploaded_by),
            "event": (
                {"id": str(instance.event.id), "title": instance.event.title}
                if instance.event
                else None
            ),
            "file_base64": instance.file_base64,
            "external_url": instance.external_url,
            "is_public_within_party": instance.is_public_within_party,
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat(),
        }


class MediaAssetListItemSerializer(MediaAssetSerializer):
    """List view omits the (potentially large) file payload."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("file_base64", None)
        return data
