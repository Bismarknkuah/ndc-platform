from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.accounts.documents import User
from apps.departments.documents import Department
from apps.hierarchy.documents import OrganizationalUnit
from apps.messaging.constants import (
    BROADCAST_KIND_CHOICES,
    MEETING_STATUS_CHOICES,
    MEETING_TYPE_CHOICES,
    NOTIFICATION_TYPE_CHOICES,
    PRIORITY_CHOICES,
    REPORT_STATUS_CHOICES,
    RSVP_STATUS_CHOICES,
)
from apps.messaging.documents import DiscussionGroup
from drf_spectacular.utils import extend_schema_field


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


class BroadcastSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    kind = serializers.ChoiceField(choices=BROADCAST_KIND_CHOICES)
    priority = serializers.ChoiceField(choices=PRIORITY_CHOICES, required=False)
    target_unit_id = serializers.CharField(write_only=True)
    requires_acknowledgement = serializers.BooleanField(required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_target_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "title": instance.title,
            "body": instance.body,
            "kind": instance.kind,
            "priority": instance.priority,
            "issued_by": _user_summary(instance.issued_by),
            "target_unit": _unit_summary(instance.target_unit),
            "requires_acknowledgement": instance.requires_acknowledgement,
            "created_at": instance.created_at.isoformat(),
        }


class UserSummarySerializer(serializers.Serializer):
    id = serializers.CharField()
    full_name = serializers.CharField()
    membership_id = serializers.CharField()


class GroupMemberActionSerializer(serializers.Serializer):
    user_id = serializers.CharField()


class BroadcastAcknowledgementSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    acknowledged_at = serializers.DateTimeField()

    @extend_schema_field(UserSummarySerializer)
    def get_user(self, obj):
        return _user_summary(obj.user)


class ReportSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    body = serializers.CharField()
    target_unit_id = serializers.CharField(write_only=True)
    status = serializers.ChoiceField(choices=REPORT_STATUS_CHOICES, read_only=True)
    resolution_notes = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_target_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "title": instance.title,
            "body": instance.body,
            "submitted_by": _user_summary(instance.submitted_by),
            "submitting_unit": _unit_summary(instance.submitting_unit),
            "target_unit": _unit_summary(instance.target_unit),
            "status": instance.status,
            "resolved_by": (
                _user_summary(instance.resolved_by) if instance.resolved_by else None
            ),
            "resolution_notes": instance.resolution_notes,
            "created_at": instance.created_at.isoformat(),
        }


class DiscussionGroupSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=150)
    description = serializers.CharField(required=False, allow_blank=True)
    organizational_unit_id = serializers.CharField(
        required=False, allow_null=True, write_only=True
    )
    member_ids = serializers.ListField(
        child=serializers.CharField(), required=False, write_only=True
    )
    created_at = serializers.DateTimeField(read_only=True)

    def validate_organizational_unit_id(self, value):
        if not value:
            return None
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def validate_member_ids(self, value):
        users = []
        for user_id in value:
            try:
                users.append(User.objects.get(id=user_id, is_active=True))
            except (DoesNotExist, MongoValidationError) as exc:
                raise serializers.ValidationError(f"User {user_id} not found.") from exc
        return users

    def to_representation(self, instance: DiscussionGroup):
        return {
            "id": str(instance.id),
            "name": instance.name,
            "description": instance.description,
            "organizational_unit": (
                _unit_summary(instance.organizational_unit)
                if instance.organizational_unit
                else None
            ),
            "created_by": _user_summary(instance.created_by),
            "members": [_user_summary(m) for m in instance.members],
            "is_active": instance.is_active,
            "created_at": instance.created_at.isoformat(),
        }


class GroupMessageSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    body = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "sender": _user_summary(instance.sender),
            "body": instance.body,
            "created_at": instance.created_at.isoformat(),
        }


class DirectMessageSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    recipient_id = serializers.CharField(write_only=True)
    body = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)

    def validate_recipient_id(self, value):
        try:
            return User.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Recipient not found.") from exc

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "sender": _user_summary(instance.sender),
            "recipient": _user_summary(instance.recipient),
            "body": instance.body,
            "read_at": instance.read_at.isoformat() if instance.read_at else None,
            "created_at": instance.created_at.isoformat(),
        }


class NotificationSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    notification_type = serializers.ChoiceField(
        choices=NOTIFICATION_TYPE_CHOICES, read_only=True
    )
    title = serializers.CharField(read_only=True)
    body = serializers.CharField(read_only=True)
    target_type = serializers.CharField(read_only=True)
    target_id = serializers.CharField(read_only=True)
    is_read = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)


class MeetingSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    meeting_type = serializers.ChoiceField(choices=MEETING_TYPE_CHOICES)
    department_id = serializers.CharField(
        required=False, allow_null=True, write_only=True
    )
    target_unit_id = serializers.CharField(write_only=True)
    scheduled_start = serializers.DateTimeField()
    scheduled_end = serializers.DateTimeField()
    status = serializers.ChoiceField(choices=MEETING_STATUS_CHOICES, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_department_id(self, value):
        if not value:
            return None
        try:
            return Department.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Department not found.") from exc

    def validate_target_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def validate(self, attrs):
        if attrs["scheduled_end"] <= attrs["scheduled_start"]:
            raise serializers.ValidationError(
                {"scheduled_end": "Must be after scheduled_start."}
            )
        return attrs

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "title": instance.title,
            "description": instance.description,
            "meeting_type": instance.meeting_type,
            "department": (
                {"id": str(instance.department.id), "name": instance.department.name}
                if instance.department
                else None
            ),
            "target_unit": _unit_summary(instance.target_unit),
            "host": _user_summary(instance.host),
            "scheduled_start": instance.scheduled_start.isoformat(),
            "scheduled_end": instance.scheduled_end.isoformat(),
            "meeting_url": instance.meeting_url,
            "status": instance.status,
            "created_at": instance.created_at.isoformat(),
        }


class MeetingRSVPSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=RSVP_STATUS_CHOICES)


class MeetingRSVPRecordSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    status = serializers.CharField()
    responded_at = serializers.DateTimeField()

    @extend_schema_field(UserSummarySerializer)
    def get_user(self, obj):
        return _user_summary(obj.user)


class ActionItemSerializer(serializers.Serializer):
    description = serializers.CharField()
    assigned_to_id = serializers.CharField(required=False, allow_null=True)
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    is_done = serializers.BooleanField(required=False)

    def validate_assigned_to_id(self, value):
        if not value:
            return None
        from apps.accounts.documents import User

        try:
            return User.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("User not found.") from exc


class MeetingMinutesSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    summary = serializers.CharField(required=False, allow_blank=True)
    decisions = serializers.CharField(required=False, allow_blank=True)
    attendee_ids = serializers.ListField(child=serializers.CharField(), required=False)
    action_items = ActionItemSerializer(many=True, required=False)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_attendee_ids(self, value):
        from apps.accounts.documents import User

        users = []
        for user_id in value:
            try:
                users.append(User.objects.get(id=user_id, is_active=True))
            except (DoesNotExist, MongoValidationError) as exc:
                raise serializers.ValidationError(f"User {user_id} not found.") from exc
        return users

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "meeting_id": str(instance.meeting.id),
            "recorded_by": _user_summary(instance.recorded_by),
            "summary": instance.summary,
            "decisions": instance.decisions,
            "attendees": [_user_summary(a) for a in instance.attendees],
            "action_items": [
                {
                    "description": item.description,
                    "assigned_to": (
                        _user_summary(item.assigned_to) if item.assigned_to else None
                    ),
                    "due_date": item.due_date.isoformat() if item.due_date else None,
                    "is_done": item.is_done,
                }
                for item in instance.action_items
            ],
            "created_at": instance.created_at.isoformat(),
        }


class NotificationPreferenceSerializer(serializers.Serializer):
    email_enabled = serializers.BooleanField(required=False)
    sms_enabled = serializers.BooleanField(required=False)
    push_enabled = serializers.BooleanField(required=False)
    push_token = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    def to_representation(self, instance):
        return {
            "email_enabled": instance.email_enabled,
            "sms_enabled": instance.sms_enabled,
            "push_enabled": instance.push_enabled,
            "push_token": instance.push_token,
        }
