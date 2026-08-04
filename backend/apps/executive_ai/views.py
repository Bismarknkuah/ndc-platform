from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.executive_ai.services import (
    draft_broadcast,
    generate_meeting_agenda,
    summarize_pending_items,
)


def _require_executive(user):
    """Same authority gate as the dashboard's jurisdiction rollup - these
    tools are for real executives, not every member."""
    is_executive = bool(
        user.is_superadmin
        or (user.role and "hierarchy.manage" in (user.role.permissions or []))
    )
    if not is_executive:
        raise APIError(
            "The Executive AI Assistant is only available to officers with "
            "hierarchy management authority.",
            code="forbidden",
            http_status=status.HTTP_403_FORBIDDEN,
        )


class DraftBroadcastRequestSerializer(serializers.Serializer):
    topic = serializers.CharField()
    tone = serializers.ChoiceField(
        choices=["formal", "urgent", "celebratory", "informational"],
        default="formal",
        required=False,
    )


class DraftBroadcastView(APIView):
    """POST /api/v1/executive-ai/draft-broadcast/ - drafts broadcast text
    for the officer to review and send themselves via the real Broadcast
    feature; this endpoint never sends anything on its own."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=DraftBroadcastRequestSerializer,
        responses={200: OpenApiTypes.OBJECT},
        tags=["executive-ai"],
    )
    def post(self, request):
        _require_executive(request.user)
        serializer = DraftBroadcastRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        draft = draft_broadcast(request.user, data["topic"], data.get("tone", "formal"))
        if draft is None:
            raise APIError(
                "The AI assistant isn't available right now (not configured, "
                "or the request failed). Try again shortly, or draft the "
                "broadcast yourself.",
                code="ai_unavailable",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        log_action(request.user, "executive_ai.draft_broadcast", request=request)
        return Response({"draft": draft})


class SummarizePendingItemsView(APIView):
    """POST /api/v1/executive-ai/summarize-pending/ - takes the same
    jurisdiction_summary object the dashboard already returns and asks
    for a short, prioritized action summary."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT},
        tags=["executive-ai"],
    )
    def post(self, request):
        _require_executive(request.user)
        jurisdiction_summary = request.data.get("jurisdiction_summary")
        if not jurisdiction_summary:
            raise APIError("jurisdiction_summary is required.", code="invalid_input")

        summary = summarize_pending_items(request.user, jurisdiction_summary)
        if summary is None:
            raise APIError(
                "The AI assistant isn't available right now.",
                code="ai_unavailable",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        log_action(request.user, "executive_ai.summarize_pending", request=request)
        return Response({"summary": summary})


class MeetingAgendaRequestSerializer(serializers.Serializer):
    meeting_topic = serializers.CharField()
    context = serializers.CharField(required=False, allow_blank=True, default="")


class GenerateMeetingAgendaView(APIView):
    """POST /api/v1/executive-ai/meeting-agenda/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=MeetingAgendaRequestSerializer,
        responses={200: OpenApiTypes.OBJECT},
        tags=["executive-ai"],
    )
    def post(self, request):
        _require_executive(request.user)
        serializer = MeetingAgendaRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        agenda = generate_meeting_agenda(
            request.user, data["meeting_topic"], data.get("context", "")
        )
        if agenda is None:
            raise APIError(
                "The AI assistant isn't available right now.",
                code="ai_unavailable",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        log_action(request.user, "executive_ai.meeting_agenda", request=request)
        return Response({"agenda": agenda})
