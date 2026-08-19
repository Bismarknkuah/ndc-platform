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
    reported_user_id = serializers.CharField(
        write_only=True, required=False, allow_null=True
    )
    is_anonymous = serializers.BooleanField(required=False, default=False)
    status = serializers.ChoiceField(choices=COMPLAINT_STATUS_CHOICES, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_target_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def validate_reported_user_id(self, value):
        if not value:
            return None
        from apps.accounts.documents import User

        try:
            return User.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Reported member not found.") from exc

    def to_representation(self, instance):
        # Default to NOT revealing when no request context is supplied
        # (e.g. a call site that forgot to pass it) - erring toward
        # privacy is the safe failure mode here, never the reverse.
        request = self.context.get("request")
        viewer = request.user if request else None
        is_own_submission = viewer is not None and str(instance.submitted_by.id) == str(
            viewer.id
        )
        if is_own_submission:
            reporter_name = instance.submitted_by.full_name
        elif viewer is not None:
            reporter_name = instance.reporter_display_name(viewer)
        else:
            reporter_name = (
                "Anonymous"
                if instance.is_anonymous
                else instance.submitted_by.full_name
            )

        return {
            "id": str(instance.id),
            "complaint_type": instance.complaint_type,
            "subject": instance.subject,
            "description": instance.description,
            "submitted_by": {
                "full_name": reporter_name,
                # The submitter's own id is only ever exposed back to
                # themselves (so "my submissions" filtering still works
                # client-side) or to someone with reveal authority -
                # never to a general viewer of an anonymous report.
                "id": (
                    str(instance.submitted_by.id)
                    if (is_own_submission or reporter_name != "Anonymous")
                    else None
                ),
                "membership_id": (
                    instance.submitted_by.membership_id
                    if (is_own_submission or reporter_name != "Anonymous")
                    else None
                ),
            },
            "is_anonymous": instance.is_anonymous,
            "reported_user": (
                _user_summary(instance.reported_user)
                if instance.reported_user
                else None
            ),
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
