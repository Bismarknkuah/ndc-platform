import datetime

from rest_framework import serializers

from apps.discipline.constants import (
    APPEAL_WINDOW_DAYS,
    CASE_CONCLUDE_DEADLINE_DAYS,
    CASE_CONVENE_DEADLINE_DAYS,
    DISCIPLINARY_MEASURE_CHOICES,
    DISCIPLINE_GROUND_CHOICES,
    SUSPENSION_REFERRAL_DEADLINE_DAYS,
)


def _unit_summary(unit):
    return {"id": str(unit.id), "name": unit.name, "unit_type": unit.unit_type}


def _user_summary(user):
    if user is None:
        return None
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "membership_id": user.membership_id,
    }


class DisciplinaryCommitteeSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "organizational_unit": _unit_summary(instance.organizational_unit),
            "members": [_user_summary(m) for m in instance.members],
            "elected_at": instance.elected_at.isoformat(),
            "is_active": instance.is_active,
        }


class DisciplinaryCaseSerializer(serializers.Serializer):
    def to_representation(self, instance):
        now = datetime.datetime.utcnow()
        convene_deadline = instance.reported_at + datetime.timedelta(
            days=CASE_CONVENE_DEADLINE_DAYS
        )
        conclude_deadline = (
            instance.convened_at + datetime.timedelta(days=CASE_CONCLUDE_DEADLINE_DAYS)
            if instance.convened_at
            else None
        )
        appeal_deadline = (
            instance.decided_at + datetime.timedelta(days=APPEAL_WINDOW_DAYS)
            if instance.decided_at
            else None
        )
        return {
            "id": str(instance.id),
            "organizational_unit": _unit_summary(instance.organizational_unit),
            "committee_id": str(instance.committee.id) if instance.committee else None,
            "respondent": _user_summary(instance.respondent),
            "reported_by": _user_summary(instance.reported_by),
            "grounds": instance.grounds,
            "description": instance.description,
            "status": instance.status,
            "reported_at": instance.reported_at.isoformat(),
            "convened_at": (
                instance.convened_at.isoformat() if instance.convened_at else None
            ),
            "convene_deadline": convene_deadline.isoformat(),
            "convene_overdue": instance.convened_at is None and now > convene_deadline,
            "conclude_deadline": (
                conclude_deadline.isoformat() if conclude_deadline else None
            ),
            "conclude_overdue": bool(
                conclude_deadline
                and instance.recommended_at is None
                and now > conclude_deadline
            ),
            "recommendation": instance.recommendation,
            "recommended_measure": instance.recommended_measure,
            "recommended_at": (
                instance.recommended_at.isoformat() if instance.recommended_at else None
            ),
            "final_decision": instance.final_decision,
            "final_measure": instance.final_measure,
            "decided_at": (
                instance.decided_at.isoformat() if instance.decided_at else None
            ),
            "decided_by": _user_summary(instance.decided_by),
            "varied_from_recommendation": instance.varied_from_recommendation,
            "appeal_deadline": appeal_deadline.isoformat() if appeal_deadline else None,
            "parent_case_id": (
                str(instance.parent_case.id) if instance.parent_case else None
            ),
            "created_at": instance.created_at.isoformat(),
        }


class CreateDisciplinaryCaseSerializer(serializers.Serializer):
    respondent_id = serializers.CharField()
    organizational_unit_id = serializers.CharField()
    grounds = serializers.ChoiceField(choices=DISCIPLINE_GROUND_CHOICES)
    description = serializers.CharField()


class RecommendationSerializer(serializers.Serializer):
    recommendation = serializers.CharField()
    recommended_measure = serializers.ChoiceField(choices=DISCIPLINARY_MEASURE_CHOICES)


class ExecutiveDecisionSerializer(serializers.Serializer):
    final_decision = serializers.CharField()
    final_measure = serializers.ChoiceField(choices=DISCIPLINARY_MEASURE_CHOICES)


class MemberSuspensionSerializer(serializers.Serializer):
    def to_representation(self, instance):
        referral_deadline = instance.suspended_at + datetime.timedelta(
            days=SUSPENSION_REFERRAL_DEADLINE_DAYS
        )
        now = datetime.datetime.utcnow()
        return {
            "id": str(instance.id),
            "user": _user_summary(instance.user),
            "organizational_unit": _unit_summary(instance.organizational_unit),
            "suspended_by": _user_summary(instance.suspended_by),
            "reason": instance.reason,
            "status": instance.status,
            "suspended_at": instance.suspended_at.isoformat(),
            "referred_at": (
                instance.referred_at.isoformat() if instance.referred_at else None
            ),
            "referral_deadline": referral_deadline.isoformat(),
            "referral_overdue": bool(
                instance.status == "ACTIVE"
                and instance.referred_at is None
                and now > referral_deadline
            ),
            "renewed_at": (
                instance.renewed_at.isoformat() if instance.renewed_at else None
            ),
            "renewal_count": instance.renewal_count,
            "related_case_id": (
                str(instance.related_case.id) if instance.related_case else None
            ),
            "created_at": instance.created_at.isoformat(),
        }


class CreateMemberSuspensionSerializer(serializers.Serializer):
    user_id = serializers.CharField()
    reason = serializers.CharField()
