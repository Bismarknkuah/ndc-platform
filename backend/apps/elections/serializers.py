from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import serializers

from apps.accounts.documents import User
from apps.elections.constants import (
    ELECTION_REQUEST_STATUS_CHOICES,
    ELECTION_STATUS_CHOICES,
    ELECTION_TYPE_CHOICES,
    POLLING_AGENT_ROLE_CHOICES,
    RESULT_STATUS_CHOICES,
)
from apps.elections.documents import Candidate, Election
from apps.hierarchy.documents import OrganizationalUnit


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class ElectionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    election_type = serializers.ChoiceField(choices=ELECTION_TYPE_CHOICES)
    scope_unit_id = serializers.CharField(write_only=True)
    status = serializers.ChoiceField(choices=ELECTION_STATUS_CHOICES, required=False)
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    created_at = serializers.DateTimeField(read_only=True)

    def validate_scope_unit_id(self, value):
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
            "election_type": instance.election_type,
            "scope_unit": _unit_summary(instance.scope_unit),
            "status": instance.status,
            "organized_by": _user_summary(instance.organized_by),
            "start_date": instance.start_date.isoformat(),
            "end_date": instance.end_date.isoformat(),
            "created_at": instance.created_at.isoformat(),
        }


class ElectionRequestSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    target_unit_id = serializers.CharField(write_only=True)
    election_type = serializers.ChoiceField(choices=ELECTION_TYPE_CHOICES)
    title = serializers.CharField(max_length=200)
    reason = serializers.CharField()
    requested_start_date = serializers.DateTimeField(required=False, allow_null=True)
    requested_end_date = serializers.DateTimeField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=ELECTION_REQUEST_STATUS_CHOICES, read_only=True
    )
    review_notes = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_target_unit_id(self, value):
        try:
            return OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "requested_by": _user_summary(instance.requested_by),
            "target_unit": _unit_summary(instance.target_unit),
            "election_type": instance.election_type,
            "title": instance.title,
            "reason": instance.reason,
            "requested_start_date": (
                instance.requested_start_date.isoformat()
                if instance.requested_start_date
                else None
            ),
            "requested_end_date": (
                instance.requested_end_date.isoformat()
                if instance.requested_end_date
                else None
            ),
            "status": instance.status,
            "reviewed_by": (
                _user_summary(instance.reviewed_by) if instance.reviewed_by else None
            ),
            "review_notes": instance.review_notes,
            "reviewed_at": (
                instance.reviewed_at.isoformat() if instance.reviewed_at else None
            ),
            "fulfilled_election_id": (
                str(instance.fulfilled_election.id)
                if instance.fulfilled_election
                else None
            ),
            "created_at": instance.created_at.isoformat(),
        }


class ElectionRequestReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class CandidateSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    position = serializers.CharField(max_length=150, required=False, allow_null=True)
    party = serializers.CharField(
        max_length=100, required=False, allow_null=True, allow_blank=True
    )
    display_order = serializers.IntegerField(required=False)
    photo_base64 = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )

    def validate_photo_base64(self, value):
        # ~2MB of raw image data, after base64's ~1.37x expansion.
        max_encoded_length = 2_800_000
        if value and len(value) > max_encoded_length:
            raise serializers.ValidationError("Photo is too large (max ~2MB).")
        return value

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "name": instance.name,
            "description": instance.description,
            "position": instance.position,
            "party": instance.party,
            "display_order": instance.display_order,
            "photo_base64": instance.photo_base64,
        }


class CandidateTallyInputSerializer(serializers.Serializer):
    candidate_id = serializers.CharField()
    votes = serializers.IntegerField(min_value=0)

    def validate_candidate_id(self, value):
        try:
            return Candidate.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Candidate not found.") from exc


class ResultSubmissionSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    election_id = serializers.CharField(write_only=True)
    branch_unit_id = serializers.CharField(write_only=True)
    position = serializers.CharField(max_length=150, required=False, allow_null=True)
    tallies = CandidateTallyInputSerializer(many=True)
    collation_sheet_photo_base64 = serializers.CharField()
    total_registered_voters = serializers.IntegerField(required=False, min_value=0)
    total_valid_votes = serializers.IntegerField(required=False, min_value=0)
    total_rejected_votes = serializers.IntegerField(required=False, min_value=0)
    status = serializers.ChoiceField(choices=RESULT_STATUS_CHOICES, read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_collation_sheet_photo_base64(self, value):
        max_encoded_length = 2_800_000  # ~2MB of raw image data after base64 expansion
        if len(value) > max_encoded_length:
            raise serializers.ValidationError("Photo is too large (max ~2MB).")
        return value

    def validate_election_id(self, value):
        try:
            return Election.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Election not found.") from exc

    def validate_branch_unit_id(self, value):
        try:
            unit = OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc
        if unit.unit_type != "BRANCH":
            raise serializers.ValidationError(
                "Results may only be submitted for a BRANCH (polling station) unit."
            )
        return unit

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "election_id": str(instance.election.id),
            "branch_unit": _unit_summary(instance.branch_unit),
            "position": instance.position,
            "tallies": [
                {
                    "candidate_id": str(t.candidate.id),
                    "candidate_name": t.candidate.name,
                    "party": t.candidate.party,
                    "votes": t.votes,
                }
                for t in instance.tallies
            ],
            "collation_sheet_photo_base64": instance.collation_sheet_photo_base64,
            "total_registered_voters": instance.total_registered_voters,
            "total_valid_votes": instance.total_valid_votes,
            "total_rejected_votes": instance.total_rejected_votes,
            "submitted_by": _user_summary(instance.submitted_by),
            "status": instance.status,
            "verified_by": (
                _user_summary(instance.verified_by) if instance.verified_by else None
            ),
            "verified_at": (
                instance.verified_at.isoformat() if instance.verified_at else None
            ),
            "created_at": instance.created_at.isoformat(),
        }


class AddEligibleVotersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.CharField(), min_length=1)


class EligibleVoterSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "user": _user_summary(instance.user),
            "added_by": _user_summary(instance.added_by),
            "created_at": instance.created_at.isoformat(),
        }


class MyEligibilitySerializer(serializers.Serializer):
    eligible = serializers.BooleanField()
    has_voted = serializers.DictField(required=False)


class CastVoteSerializer(serializers.Serializer):
    candidate_id = serializers.CharField()
    position = serializers.CharField(max_length=150, required=False, allow_null=True)

    def validate_candidate_id(self, value):
        try:
            return Candidate.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Candidate not found.") from exc


class VoteReceiptSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "election_id": str(instance.election.id),
            "position": instance.position,
            "candidate": {
                "id": str(instance.candidate.id),
                "name": instance.candidate.name,
            },
            "cast_at": instance.cast_at.isoformat(),
        }


class PollingAgentAssignmentSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    election_id = serializers.CharField(write_only=True)
    branch_unit_id = serializers.CharField(write_only=True)
    agent_id = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(choices=POLLING_AGENT_ROLE_CHOICES)
    notes = serializers.CharField(required=False, allow_blank=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_election_id(self, value):
        try:
            return Election.objects.get(id=value)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Election not found.") from exc

    def validate_branch_unit_id(self, value):
        try:
            unit = OrganizationalUnit.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Organizational unit not found.") from exc
        if unit.unit_type != "BRANCH":
            raise serializers.ValidationError(
                "Polling agents are assigned to a BRANCH (polling station) unit."
            )
        return unit

    def validate_agent_id(self, value):
        try:
            return User.objects.get(id=value, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise serializers.ValidationError("Agent not found.") from exc

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "election_id": str(instance.election.id),
            "branch_unit": _unit_summary(instance.branch_unit),
            "agent": _user_summary(instance.agent),
            "role": instance.role,
            "assigned_by": _user_summary(instance.assigned_by),
            "checked_in_at": (
                instance.checked_in_at.isoformat() if instance.checked_in_at else None
            ),
            "materials_confirmed": instance.materials_confirmed,
            "notes": instance.notes,
            "created_at": instance.created_at.isoformat(),
        }
