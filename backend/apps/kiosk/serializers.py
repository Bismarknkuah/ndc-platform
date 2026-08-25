import re

from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.hierarchy.documents import OrganizationalUnit


class SetKioskPinSerializer(serializers.Serializer):
    """Setting a Kiosk PIN requires the member's real account password -
    the same "prove who you are with something you already know before
    creating a new secondary credential" pattern as ChangePasswordSerializer,
    so a stolen membership ID alone can never be used to set a PIN on
    someone else's account."""

    current_password = serializers.CharField(write_only=True)
    pin = serializers.CharField(write_only=True)

    def validate_pin(self, value):
        if not re.fullmatch(r"\d{4,6}", value):
            raise serializers.ValidationError("PIN must be 4 to 6 digits.")
        return value


class KioskRegistrationSerializer(serializers.Serializer):
    unit_id = serializers.CharField(write_only=True)
    label = serializers.CharField(max_length=150)

    def validate_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def to_representation(self, instance):
        data = {
            "id": str(instance.id),
            "label": instance.label,
            "unit": {"id": str(instance.unit.id), "name": instance.unit.name},
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat(),
        }
        # kiosk_code is only ever included right after creation - see
        # the view - never on subsequent reads, matching how an API key
        # is shown once and never displayed again.
        if getattr(instance, "_show_kiosk_code", False):
            data["kiosk_code"] = instance.kiosk_code
        return data


class KioskVerifySerializer(serializers.Serializer):
    kiosk_code = serializers.CharField()
    membership_id = serializers.CharField()
    pin = serializers.CharField()


class KioskCastVoteSerializer(serializers.Serializer):
    """Documents the real request body for KioskCastVoteView - actual
    validation of candidate_id/position still goes through
    CastVoteSerializer in the view itself; this exists purely so the
    generated API schema accurately shows all three fields together,
    including kiosk_vote_token, rather than a mismatched or empty
    schema."""

    kiosk_vote_token = serializers.CharField()
    candidate_id = serializers.CharField()
    position = serializers.CharField(required=False, allow_null=True)
