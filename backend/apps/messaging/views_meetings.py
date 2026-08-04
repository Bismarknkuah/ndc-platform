from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.departments.documents import DepartmentAssignment
from apps.messaging.documents import Meeting, MeetingRSVP
from apps.messaging.permissions import can_call_meeting
from apps.messaging.serializers import (
    MeetingRSVPRecordSerializer,
    MeetingRSVPSerializer,
    MeetingSerializer,
)
from apps.messaging.services import (
    generate_meeting_room_url,
    notify_many,
    units_in_subtree,
)


def _get_meeting_or_404(meeting_id):
    try:
        return Meeting.objects.get(id=meeting_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Meeting not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


def _resolve_audience(meeting):
    """The concrete list of Users invited to a meeting."""
    if meeting.department is not None:
        unit_ids = [u.id for u in units_in_subtree(meeting.target_unit)]
        assignments = DepartmentAssignment.objects(
            department=meeting.department,
            organizational_unit__in=unit_ids,
            is_active=True,
        )
        return list({a.user.id: a.user for a in assignments}.values())

    from apps.messaging.services import users_in_subtree

    return users_in_subtree(meeting.target_unit)


def _can_view_meeting(user, meeting) -> bool:
    if user.is_superadmin or meeting.host.id == user.id:
        return True
    return any(attendee.id == user.id for attendee in _resolve_audience(meeting))


class MeetingListCreateView(APIView):
    """
    GET  /api/v1/messaging/meetings/?department_id=&target_unit_id=&status=&upcoming=true
         Meetings visible to the caller: hosted by them, or where they're
         part of the computed audience.

    POST /api/v1/messaging/meetings/
         Schedule a meeting or training workshop. A real Jitsi Meet video
         room is generated automatically (no external account/API key
         needed). department + target_unit determine both who may call the
         meeting and who gets invited - see apps.messaging.permissions.
         can_call_meeting for the full "chain of channels" rule, including
         the Chairman/Secretary-only party-wide meeting.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MeetingSerializer(many=True)}, tags=["messaging"])
    def get(self, request):
        user = request.user
        if user.is_superadmin:
            qs = Meeting.objects.all()
        else:
            qs = Meeting.objects(host=user.id)
            # Union in anything the caller is part of the audience for.
            # Computing full audience per-meeting is expensive at list
            # scale, so we approximate with unit/department membership:
            # visible if hosted by them OR their unit is in the target
            # subtree (general/most department meetings) - exact access is
            # still enforced on the detail view via _can_view_meeting.
            if user.organizational_unit:
                ancestor_ids = [
                    a.id
                    for a in (
                        [user.organizational_unit]
                        + user.organizational_unit.get_ancestors()
                    )
                ]
                qs = Meeting.objects(
                    __raw__={
                        "$or": [
                            {"host": user.id},
                            {"target_unit": {"$in": ancestor_ids}},
                        ]
                    }
                )

        meeting_status = request.query_params.get("status")
        if meeting_status:
            qs = qs.filter(status=meeting_status)

        department_id = request.query_params.get("department_id")
        if department_id:
            qs = qs.filter(department=department_id)

        target_unit_id = request.query_params.get("target_unit_id")
        if target_unit_id:
            qs = qs.filter(target_unit=target_unit_id)

        if request.query_params.get("upcoming") == "true":
            import datetime

            qs = qs.filter(
                scheduled_start__gte=datetime.datetime.utcnow(), status="SCHEDULED"
            )

        paginator, page = paginate_queryset(
            qs.order_by("scheduled_start"), request, self
        )
        return paginator.get_paginated_response(MeetingSerializer(page, many=True).data)

    @extend_schema(
        request=MeetingSerializer,
        responses={201: MeetingSerializer},
        tags=["messaging"],
    )
    def post(self, request):
        serializer = MeetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_unit = serializer.validated_data["target_unit_id"]
        department = serializer.validated_data.get("department_id")

        if not can_call_meeting(request.user, target_unit, department=department):
            raise APIError(
                "You do not have authority to call a meeting for this audience.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        meeting = Meeting.objects.create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            meeting_type=serializer.validated_data["meeting_type"],
            department=department,
            target_unit=target_unit,
            host=request.user,
            scheduled_start=serializer.validated_data["scheduled_start"],
            scheduled_end=serializer.validated_data["scheduled_end"],
            meeting_url=generate_meeting_room_url(serializer.validated_data["title"]),
        )

        audience = [u for u in _resolve_audience(meeting) if u.id != request.user.id]
        notify_many(
            audience,
            "MEETING",
            title=f"{'Workshop' if meeting.meeting_type == 'WORKSHOP' else 'Meeting'}: {meeting.title}",
            body=f"Scheduled {meeting.scheduled_start.isoformat()}",
            target=meeting,
        )

        log_action(
            request.user,
            "messaging.meeting.schedule",
            request=request,
            target=meeting,
            description=f"{meeting.meeting_type} '{meeting.title}' for {target_unit.name}",
            metadata={
                "department": department.code if department else None,
                "audience_count": len(audience),
            },
        )
        return Response(MeetingSerializer(meeting).data, status=status.HTTP_201_CREATED)


class MeetingDetailView(APIView):
    """
    GET   /api/v1/messaging/meetings/<id>/    - includes the join link (meeting_url) if you're invited
    PATCH /api/v1/messaging/meetings/<id>/    - host can reschedule or change status (LIVE/COMPLETED/CANCELLED)
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MeetingSerializer}, tags=["messaging"])
    def get(self, request, meeting_id):
        meeting = _get_meeting_or_404(meeting_id)
        if not _can_view_meeting(request.user, meeting):
            raise APIError(
                "This meeting was not called for you.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        return Response(MeetingSerializer(meeting).data)

    @extend_schema(
        request=MeetingSerializer,
        responses={200: MeetingSerializer},
        tags=["messaging"],
    )
    def patch(self, request, meeting_id):
        meeting = _get_meeting_or_404(meeting_id)
        if not (request.user.is_superadmin or meeting.host.id == request.user.id):
            raise APIError(
                "Only the host can modify this meeting.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        new_status = request.data.get("status")
        if new_status in ("LIVE", "COMPLETED", "CANCELLED"):
            meeting.status = new_status

        for field in ("title", "description", "scheduled_start", "scheduled_end"):
            if field in request.data:
                setattr(meeting, field, request.data[field])

        meeting.save()
        log_action(
            request.user,
            "messaging.meeting.update",
            request=request,
            target=meeting,
            description=f"status={meeting.status}",
        )
        return Response(MeetingSerializer(meeting).data)


class MeetingRSVPView(APIView):
    """POST /api/v1/messaging/meetings/<id>/rsvp/ {"status": "ATTENDING"|"DECLINED"}"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MeetingRSVPSerializer,
        responses={201: MeetingRSVPRecordSerializer},
        tags=["messaging"],
    )
    def post(self, request, meeting_id):
        meeting = _get_meeting_or_404(meeting_id)
        if not _can_view_meeting(request.user, meeting):
            raise APIError(
                "This meeting was not called for you.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MeetingRSVPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rsvp = MeetingRSVP.objects(meeting=meeting, user=request.user).first()
        if rsvp is None:
            rsvp = MeetingRSVP.objects.create(
                meeting=meeting,
                user=request.user,
                status=serializer.validated_data["status"],
            )
        else:
            rsvp.status = serializer.validated_data["status"]
            import datetime

            rsvp.responded_at = datetime.datetime.utcnow()
            rsvp.save()

        return Response(
            MeetingRSVPRecordSerializer(rsvp).data, status=status.HTTP_201_CREATED
        )


class MeetingRSVPListView(APIView):
    """GET /api/v1/messaging/meetings/<id>/rsvps/ - host-only attendance list."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: MeetingRSVPRecordSerializer(many=True)}, tags=["messaging"]
    )
    def get(self, request, meeting_id):
        meeting = _get_meeting_or_404(meeting_id)
        if not (request.user.is_superadmin or meeting.host.id == request.user.id):
            raise APIError(
                "Only the host can view the RSVP list.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        rsvps = MeetingRSVP.objects(meeting=meeting).order_by("-responded_at")
        audience = _resolve_audience(meeting)
        return Response(
            {
                "total_invited": len(audience),
                "attending_count": rsvps.filter(status="ATTENDING").count(),
                "declined_count": rsvps.filter(status="DECLINED").count(),
                "rsvps": MeetingRSVPRecordSerializer(rsvps, many=True).data,
            }
        )
