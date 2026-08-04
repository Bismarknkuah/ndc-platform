import datetime

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import UserSerializer
from apps.analytics.services import compute_membership_analytics
from apps.complaints.documents import Complaint
from apps.departments.documents import DepartmentAssignment, TaskAssignment
from apps.discipline.documents import DisciplinaryCase
from apps.elections.documents import Election
from apps.elections.permissions import can_manage_election
from apps.elections.serializers import ElectionSerializer
from apps.events.documents import Event
from apps.events.permissions import can_manage_events
from apps.events.serializers import EventSerializer
from apps.finance.permissions import can_view_finance
from apps.finance.services import summarize_finance
from apps.messaging.documents import Broadcast, Meeting, Notification
from apps.messaging.serializers import BroadcastSerializer, MeetingSerializer
from apps.messaging.services import units_in_subtree
from apps.welfare.documents import WelfareRequest


def _department_leadership(user):
    """Every team this user leads (HEAD/DEPUTY_HEAD), with a quick pending-task count."""
    leadership = []
    for assignment in DepartmentAssignment.objects(
        user=user, position__in=["HEAD", "DEPUTY_HEAD"], is_active=True
    ):
        team_members = DepartmentAssignment.objects(
            department=assignment.department,
            organizational_unit=assignment.organizational_unit,
            is_active=True,
        )
        team_user_ids = [member.user.id for member in team_members]
        pending_tasks = TaskAssignment.objects(
            department=assignment.department,
            assigned_to__in=team_user_ids,
            status__in=["PENDING", "ACKNOWLEDGED"],
        ).count()
        leadership.append(
            {
                "department": {
                    "id": str(assignment.department.id),
                    "name": assignment.department.name,
                },
                "organizational_unit": {
                    "id": str(assignment.organizational_unit.id),
                    "name": assignment.organizational_unit.name,
                },
                "position": assignment.position,
                "team_size": len(team_user_ids),
                "pending_tasks": pending_tasks,
            }
        )
    return leadership


def _manageable_elections(user, limit=5):
    elections = []
    for election in Election.objects(status__in=["OPEN", "COLLATION"]).order_by(
        "-created_at"
    )[:50]:
        if can_manage_election(user, election.scope_unit):
            elections.append(election)
        if len(elections) >= limit:
            break
    return elections


def _manageable_events(user, limit=5):
    now = datetime.datetime.utcnow()
    events = []
    for event in Event.objects(status="SCHEDULED", scheduled_start__gte=now).order_by(
        "scheduled_start"
    )[:50]:
        if can_manage_events(user, event.target_unit) or event.organizer.id == user.id:
            events.append(event)
        if len(events) >= limit:
            break
    return events


def _has_hierarchy_authority(user) -> bool:
    """Same gate used throughout the platform (complaints, discipline,
    welfare, etc.) for "this person is a real executive with authority
    over their own unit's jurisdiction" - reused here to decide whether
    to compute the (moderately expensive) jurisdiction-wide rollup at
    all, not just for a single permission check."""
    return bool(
        user.is_superadmin
        or (user.role and "hierarchy.manage" in (user.role.permissions or []))
    )


def _jurisdiction_summary(user):
    """
    The "follows up the hierarchy" rollup: for a real executive, a
    single scoped view of their entire jurisdiction (their unit plus
    every descendant unit beneath it) - not just their own unit's raw
    numbers. A Branch Chairman's jurisdiction is just their branch; a
    Regional Chairman's is every constituency and branch in the region;
    a National officer's is the whole party. Same underlying query
    (`units_in_subtree`) at every level - the rollup naturally scales
    with however broad the caller's actual authority is.
    """
    unit = user.organizational_unit
    if unit is None or not _has_hierarchy_authority(user):
        return None

    membership = compute_membership_analytics(unit)
    subtree_ids = [u.id for u in units_in_subtree(unit)]

    pending_complaints = Complaint.objects(
        target_unit__in=subtree_ids, status__in=["SUBMITTED", "UNDER_REVIEW"]
    ).count()
    pending_discipline_cases = DisciplinaryCase.objects(
        organizational_unit__in=subtree_ids,
        is_active=True,
        status__nin=["DECIDED", "CLOSED"],
    ).count()
    pending_welfare_requests = WelfareRequest.objects(
        organizational_unit__in=subtree_ids, status__in=["SUBMITTED", "UNDER_REVIEW"]
    ).count()

    return {
        "organizational_unit": membership["organizational_unit"],
        "total_members": membership["total_members"],
        "executive_count": membership["executive_count"],
        "gender_breakdown": membership["gender_breakdown"],
        "growth_last_12_months": membership["growth_last_12_months"],
        "pending_complaints": pending_complaints,
        "pending_discipline_cases": pending_discipline_cases,
        "pending_welfare_requests": pending_welfare_requests,
        "requires_attention": (
            pending_complaints + pending_discipline_cases + pending_welfare_requests
        ),
    }


class DashboardView(APIView):
    """
    GET /api/v1/dashboard/

    One unified home-screen endpoint, tailored to whatever roles/authority
    the caller actually holds - an Ordinary Member gets their profile,
    notifications, and upcoming meetings; a department HEAD additionally
    sees their team(s); an Election & IT Director sees active elections
    they can manage; someone with finance authority sees their unit's
    finance summary. No client-side role-branching needed - the payload
    only contains sections relevant to the caller.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT}, tags=["dashboard"])
    def get(self, request):
        user = request.user
        now = datetime.datetime.utcnow()

        payload = {
            "profile": UserSerializer(user).data,
            "unread_notification_count": Notification.objects(
                user=user, is_read=False
            ).count(),
        }

        # Upcoming meetings hosted by or visible to the user (approximate
        # via unit ancestry, same cheap heuristic the meetings list uses).
        if user.organizational_unit:
            ancestor_ids = [
                a.id
                for a in (
                    [user.organizational_unit]
                    + user.organizational_unit.get_ancestors()
                )
            ]
            upcoming_meetings = Meeting.objects(
                __raw__={
                    "$or": [{"host": user.id}, {"target_unit": {"$in": ancestor_ids}}],
                    "status": "SCHEDULED",
                    "scheduled_start": {"$gte": now},
                }
            ).order_by("scheduled_start")[:5]
        else:
            upcoming_meetings = Meeting.objects(
                host=user, status="SCHEDULED", scheduled_start__gte=now
            ).order_by("scheduled_start")[:5]
        payload["upcoming_meetings"] = MeetingSerializer(
            upcoming_meetings, many=True
        ).data

        # Recent broadcasts targeted at the caller's own unit or an ancestor of it.
        if user.organizational_unit:
            ancestor_ids = [
                a.id
                for a in (
                    [user.organizational_unit]
                    + user.organizational_unit.get_ancestors()
                )
            ]
            recent_broadcasts = Broadcast.objects(
                target_unit__in=ancestor_ids
            ).order_by("-created_at")[:5]
        else:
            recent_broadcasts = []
        payload["recent_broadcasts"] = BroadcastSerializer(
            recent_broadcasts, many=True
        ).data

        # Own pending department tasks.
        pending_tasks = TaskAssignment.objects(
            assigned_to=user, status__in=["PENDING", "ACKNOWLEDGED"]
        ).order_by("scheduled_at")[:5]
        payload["pending_tasks"] = [
            {
                "id": str(t.id),
                "title": t.title,
                "engagement_type": t.engagement_type,
                "platform_name": t.platform_name,
                "scheduled_at": t.scheduled_at.isoformat(),
                "status": t.status,
            }
            for t in pending_tasks
        ]

        # Teams the caller leads, if any.
        leadership = _department_leadership(user)
        if leadership:
            payload["teams_led"] = leadership

        # Elections the caller can manage, if any.
        manageable_elections = _manageable_elections(user)
        if manageable_elections:
            payload["active_elections"] = ElectionSerializer(
                manageable_elections, many=True
            ).data

        # Upcoming events the caller organizes or has authority over.
        manageable_events = _manageable_events(user)
        if manageable_events:
            payload["upcoming_events"] = EventSerializer(
                manageable_events, many=True
            ).data

        # Finance summary for the caller's own unit, if they have finance authority.
        if user.organizational_unit and can_view_finance(
            user, user.organizational_unit
        ):
            payload["finance_summary"] = summarize_finance(user.organizational_unit)

        # Jurisdiction-wide rollup (their unit + every descendant unit) -
        # only computed for real executives, since it's the one section
        # that scales with the whole subtree rather than just the
        # caller's immediate unit.
        jurisdiction_summary = _jurisdiction_summary(user)
        if jurisdiction_summary:
            payload["jurisdiction_summary"] = jurisdiction_summary

        return Response(payload)
