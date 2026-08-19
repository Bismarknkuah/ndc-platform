from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.documents.constants import DOCUMENT_CATEGORY_CHOICES
from apps.hierarchy.documents import OrganizationalUnit


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class PartyDocumentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=DOCUMENT_CATEGORY_CHOICES)
    organizational_unit_id = serializers.CharField(write_only=True)
    file_base64 = serializers.CharField()
    file_name = serializers.CharField(max_length=255)
    mime_type = serializers.CharField(max_length=100)
    is_public_within_party = serializers.BooleanField(required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_file_base64(self, value):
        max_encoded_length = 7_000_000  # ~5MB of raw file data after base64 expansion
        if len(value) > max_encoded_length:
            raise serializers.ValidationError(
                "File is too large (max ~5MB). Use external storage for larger files."
            )
        return value

    def validate_organizational_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "title": instance.title,
            "description": instance.description,
            "category": instance.category,
            "organizational_unit": _unit_summary(instance.organizational_unit),
            "uploaded_by": _user_summary(instance.uploaded_by),
            "file_base64": instance.file_base64,
            "file_name": instance.file_name,
            "mime_type": instance.mime_type,
            "is_public_within_party": instance.is_public_within_party,
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat(),
        }


class PartyDocumentListItemSerializer(PartyDocumentSerializer):
    """Same as PartyDocumentSerializer but omits the (potentially large)
    file payload for list views - callers fetch the detail view to
    download."""

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data.pop("file_base64", None)
        return data
