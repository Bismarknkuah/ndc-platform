from drf_spectacular.utils import extend_schema
from mongoengine.errors import (
    DoesNotExist,
    NotUniqueError,
    ValidationError as MongoValidationError,
)
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.messaging.documents import ActionItem, Meeting, MeetingMinutes, MeetingRSVP
from apps.messaging.serializers import MeetingMinutesSerializer


def _get_meeting_or_404(meeting_id):
    try:
        return Meeting.objects.get(id=meeting_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Meeting not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


def _can_manage_minutes(user, meeting) -> bool:
    return user.is_superadmin or meeting.host.id == user.id


def _can_view_minutes(user, meeting) -> bool:
    from apps.messaging.views_meetings import _can_view_meeting

    return _can_manage_minutes(user, meeting) or _can_view_meeting(user, meeting)


class MeetingMinutesView(APIView):
    """
    GET  /api/v1/messaging/meetings/<id>/minutes/  - view the minutes (any invitee)
    POST /api/v1/messaging/meetings/<id>/minutes/  - record minutes (host only). One
         set of minutes per meeting; a second POST amends the existing one.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: MeetingMinutesSerializer}, tags=["messaging"])
    def get(self, request, meeting_id):
        meeting = _get_meeting_or_404(meeting_id)
        if not _can_view_minutes(request.user, meeting):
            raise APIError(
                "You do not have access to this meeting's minutes.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        minutes = MeetingMinutes.objects(meeting=meeting).first()
        if minutes is None:
            raise APIError(
                "No minutes have been recorded for this meeting yet.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            )
        return Response(MeetingMinutesSerializer(minutes).data)

    @extend_schema(
        request=MeetingMinutesSerializer,
        responses={201: MeetingMinutesSerializer},
        tags=["messaging"],
    )
    def post(self, request, meeting_id):
        meeting = _get_meeting_or_404(meeting_id)
        if not _can_manage_minutes(request.user, meeting):
            raise APIError(
                "Only the host can record minutes for this meeting.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        serializer = MeetingMinutesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        attendees = serializer.validated_data.get("attendee_ids")
        if attendees is None:
            attendees = [
                r.user for r in MeetingRSVP.objects(meeting=meeting, status="ATTENDING")
            ]

        action_items = [
            ActionItem(
                description=item["description"],
                assigned_to=item.get("assigned_to_id"),
                due_date=item.get("due_date"),
                is_done=item.get("is_done", False),
            )
            for item in serializer.validated_data.get("action_items", [])
        ]

        existing = MeetingMinutes.objects(meeting=meeting).first()
        if existing:
            existing.summary = serializer.validated_data.get(
                "summary", existing.summary
            )
            existing.decisions = serializer.validated_data.get(
                "decisions", existing.decisions
            )
            existing.attendees = attendees
            existing.action_items = action_items
            existing.save()
            minutes = existing
            created = False
        else:
            try:
                minutes = MeetingMinutes.objects.create(
                    meeting=meeting,
                    recorded_by=request.user,
                    summary=serializer.validated_data.get("summary", ""),
                    decisions=serializer.validated_data.get("decisions", ""),
                    attendees=attendees,
                    action_items=action_items,
                )
                created = True
            except NotUniqueError as exc:
                raise APIError(
                    "Minutes already exist for this meeting.",
                    code="conflict",
                    http_status=status.HTTP_409_CONFLICT,
                ) from exc

        log_action(
            request.user,
            "messaging.meeting.minutes.record",
            request=request,
            target=meeting,
        )
        return Response(
            MeetingMinutesSerializer(minutes).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
