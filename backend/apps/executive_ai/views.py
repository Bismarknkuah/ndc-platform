from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.documents import User
from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.executive_ai.services import (
    draft_broadcast,
    generate_meeting_agenda,
    generate_official_report,
    generate_speech,
    ground_situation_briefing,
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


def _require_leader(user):
    """Assigning a directive to any executive across the party, outside
    the normal chain of command, is national-leadership authority -
    same gate as Ground Intelligence and the Leader Dashboard, not the
    broader hierarchy.manage every jurisdiction chairman carries."""
    is_leader = bool(
        user.is_superadmin
        or (
            user.role
            and "analytics.ground_intelligence" in (user.role.permissions or [])
        )
    )
    if not is_leader:
        raise APIError(
            "Assigning directives is only available to the party's national "
            "leadership.",
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


class GroundBriefingView(APIView):
    """POST /api/v1/executive-ai/ground-briefing/<unit_id>/ - fetches
    real complaint/welfare/report data for the given unit server-side
    (never trusts a client-supplied summary for this one, unlike
    summarize-pending-items, since a fabricated or edited "ground
    situation" would be a genuinely serious problem for a national
    leader to act on) and asks for a briefing."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: OpenApiTypes.OBJECT}, tags=["executive-ai"]
    )
    def post(self, request, unit_id):
        from apps.analytics.permissions import can_access_ground_intelligence_for_unit
        from apps.analytics.services import compute_ground_intelligence
        from apps.hierarchy.documents import OrganizationalUnit

        from mongoengine.errors import DoesNotExist
        from mongoengine.errors import ValidationError as MongoValidationError

        try:
            unit = OrganizationalUnit.objects.get(id=unit_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Organizational unit not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

        if not can_access_ground_intelligence_for_unit(request.user, unit):
            raise APIError(
                "You don't have Ground Intelligence authority over this unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        ground_intelligence = compute_ground_intelligence(unit)
        briefing = ground_situation_briefing(unit.name, ground_intelligence)
        if briefing is None:
            raise APIError(
                "The AI assistant isn't available right now.",
                code="ai_unavailable",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        log_action(request.user, "executive_ai.ground_briefing", request=request)
        return Response(
            {"briefing": briefing, "ground_intelligence": ground_intelligence}
        )


# --------------------------------------------------------------------------
# Leader directives: the party's national leadership assigning a task
# directly to any executive at National, Regional, or Constituency /
# District Co-ordinating Committee level, outside department structure.
# --------------------------------------------------------------------------

DIRECTIVE_ASSIGNABLE_UNIT_TYPES = [
    "NATIONAL",
    "REGIONAL",
    "CONSTITUENCY",
    "DISTRICT_COORDINATING_COMMITTEE",
]


class DirectiveSerializer(serializers.Serializer):
    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "assigned_to": {
                "id": str(instance.assigned_to.id),
                "full_name": instance.assigned_to.full_name,
                "role": (
                    instance.assigned_to.role.name
                    if instance.assigned_to.role
                    else None
                ),
                "organizational_unit": (
                    instance.assigned_to.organizational_unit.name
                    if instance.assigned_to.organizational_unit
                    else None
                ),
            },
            "assigned_by": {
                "id": str(instance.assigned_by.id),
                "full_name": instance.assigned_by.full_name,
            },
            "title": instance.title,
            "description": instance.description,
            "due_at": instance.due_at.isoformat() if instance.due_at else None,
            "status": instance.status,
            "acknowledged_at": (
                instance.acknowledged_at.isoformat()
                if instance.acknowledged_at
                else None
            ),
            "completed_at": (
                instance.completed_at.isoformat() if instance.completed_at else None
            ),
            "created_at": instance.created_at.isoformat(),
        }


class CreateDirectiveRequestSerializer(serializers.Serializer):
    assigned_to_id = serializers.CharField()
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    due_at = serializers.DateTimeField(required=False, allow_null=True)


class DirectiveListCreateView(APIView):
    """
    GET  /api/v1/executive-ai/directives/ - the caller's own directives
         (assigned to them by leadership).
    POST /api/v1/executive-ai/directives/ - leadership assigns a new
         directive to any National, Regional, or Constituency/District
         executive. Branch level is deliberately excluded - directives
         from national leadership are for the officers running a
         region, constituency, or the party nationally, not grassroots
         volunteers.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DirectiveSerializer(many=True)}, tags=["executive-ai"]
    )
    def get(self, request):
        from apps.executive_ai.documents import LeaderDirective

        qs = LeaderDirective.objects(assigned_to=request.user).order_by("-created_at")
        paginator, page = paginate_queryset(qs, request, self)
        return paginator.get_paginated_response(
            DirectiveSerializer(page, many=True).data
        )

    @extend_schema(
        request=CreateDirectiveRequestSerializer,
        responses={200: DirectiveSerializer},
        tags=["executive-ai"],
    )
    def post(self, request):
        from mongoengine.errors import DoesNotExist
        from mongoengine.errors import ValidationError as MongoValidationError

        from apps.executive_ai.documents import LeaderDirective

        _require_leader(request.user)

        serializer = CreateDirectiveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            assigned_to = User.objects.get(id=data["assigned_to_id"], is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "That member was not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

        if not (assigned_to.role and assigned_to.role.is_executive):
            raise APIError(
                "Directives can only be assigned to an executive, not an "
                "ordinary member.",
                code="invalid_input",
                http_status=status.HTTP_400_BAD_REQUEST,
            )
        unit = assigned_to.organizational_unit
        if unit is None or unit.unit_type not in DIRECTIVE_ASSIGNABLE_UNIT_TYPES:
            raise APIError(
                "Directives can only be assigned to National, Regional, or "
                "Constituency/District-level executives, not Branch level.",
                code="invalid_input",
                http_status=status.HTTP_400_BAD_REQUEST,
            )

        directive = LeaderDirective.objects.create(
            assigned_to=assigned_to,
            assigned_by=request.user,
            title=data["title"],
            description=data.get("description", ""),
            due_at=data.get("due_at"),
        )
        log_action(request.user, "executive_ai.directive.create", request=request)
        return Response(DirectiveSerializer(directive).data)


class IssuedDirectivesView(APIView):
    """GET /api/v1/executive-ai/directives/issued/ - directives the
    caller (as a leader) has assigned to others, so they can track
    follow-through - distinct from the "my own directives" list above."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: DirectiveSerializer(many=True)}, tags=["executive-ai"]
    )
    def get(self, request):
        from apps.executive_ai.documents import LeaderDirective

        _require_leader(request.user)
        qs = LeaderDirective.objects(assigned_by=request.user).order_by("-created_at")
        paginator, page = paginate_queryset(qs, request, self)
        return paginator.get_paginated_response(
            DirectiveSerializer(page, many=True).data
        )


def _get_own_directive_or_404(directive_id, user):
    from mongoengine.errors import DoesNotExist
    from mongoengine.errors import ValidationError as MongoValidationError

    from apps.executive_ai.documents import LeaderDirective

    try:
        directive = LeaderDirective.objects.get(id=directive_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Directive not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc
    if str(directive.assigned_to.id) != str(user.id):
        raise APIError(
            "You can only update your own directives.",
            code="forbidden",
            http_status=status.HTTP_403_FORBIDDEN,
        )
    return directive


class AcknowledgeDirectiveView(APIView):
    """POST /api/v1/executive-ai/directives/<id>/acknowledge/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: DirectiveSerializer}, tags=["executive-ai"]
    )
    def post(self, request, directive_id):
        directive = _get_own_directive_or_404(directive_id, request.user)
        directive.mark_acknowledged()
        directive.save()
        return Response(DirectiveSerializer(directive).data)


class CompleteDirectiveView(APIView):
    """POST /api/v1/executive-ai/directives/<id>/complete/"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: DirectiveSerializer}, tags=["executive-ai"]
    )
    def post(self, request, directive_id):
        directive = _get_own_directive_or_404(directive_id, request.user)
        directive.mark_completed()
        directive.save()
        return Response(DirectiveSerializer(directive).data)


class OfficialReportView(APIView):
    """POST /api/v1/executive-ai/official-report/<unit_id>/?include_names=true|false

    Two genuinely distinct outputs: with include_names=false (the
    default), reporter identity never reaches the model at all. With
    include_names=true, real names are included - gated separately on
    can_reveal_reporter_identity, the same authority required to see
    an individual reporter's name on a single complaint."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None, responses={200: OpenApiTypes.OBJECT}, tags=["executive-ai"]
    )
    def post(self, request, unit_id):
        from apps.analytics.permissions import can_access_ground_intelligence_for_unit
        from apps.analytics.services import compute_ground_intelligence
        from apps.complaints.permissions import can_reveal_reporter_identity
        from apps.hierarchy.documents import OrganizationalUnit

        from mongoengine.errors import DoesNotExist
        from mongoengine.errors import ValidationError as MongoValidationError

        try:
            unit = OrganizationalUnit.objects.get(id=unit_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Organizational unit not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

        if not can_access_ground_intelligence_for_unit(request.user, unit):
            raise APIError(
                "You don't have Ground Intelligence authority over this unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        include_names = request.query_params.get("include_names") == "true"
        if include_names and not can_reveal_reporter_identity(request.user, None):
            raise APIError(
                "You do not have authority to generate a report with reporter "
                "names included.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        ground_intelligence = compute_ground_intelligence(unit)
        report = generate_official_report(unit.name, ground_intelligence, include_names)
        if report is None:
            raise APIError(
                "The AI assistant isn't available right now.",
                code="ai_unavailable",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        log_action(
            request.user,
            "executive_ai.official_report.generate",
            request=request,
            description=f"include_names={include_names}",
        )
        return Response({"report": report, "include_names": include_names})


class SpeechRequestSerializer(serializers.Serializer):
    style_instructions = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class SpeechView(APIView):
    """POST /api/v1/executive-ai/speech/<unit_id>/
    Body: {"style_instructions": "..."} (optional)"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=SpeechRequestSerializer,
        responses={200: OpenApiTypes.OBJECT},
        tags=["executive-ai"],
    )
    def post(self, request, unit_id):
        from apps.analytics.permissions import can_access_ground_intelligence_for_unit
        from apps.analytics.services import compute_ground_intelligence
        from apps.hierarchy.documents import OrganizationalUnit

        from mongoengine.errors import DoesNotExist
        from mongoengine.errors import ValidationError as MongoValidationError

        try:
            unit = OrganizationalUnit.objects.get(id=unit_id, is_active=True)
        except (DoesNotExist, MongoValidationError) as exc:
            raise APIError(
                "Organizational unit not found.",
                code="not_found",
                http_status=status.HTTP_404_NOT_FOUND,
            ) from exc

        if not can_access_ground_intelligence_for_unit(request.user, unit):
            raise APIError(
                "You don't have Ground Intelligence authority over this unit.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        style_instructions = request.data.get("style_instructions", "")
        ground_intelligence = compute_ground_intelligence(unit)
        speech = generate_speech(unit.name, ground_intelligence, style_instructions)
        if speech is None:
            raise APIError(
                "The AI assistant isn't available right now.",
                code="ai_unavailable",
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        log_action(request.user, "executive_ai.speech.generate", request=request)
        return Response({"speech": speech})
