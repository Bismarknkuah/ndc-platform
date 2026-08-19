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
from apps.core.pagination import paginate_queryset
from apps.elections.documents import PollingAgentAssignment
from apps.elections.permissions import can_manage_election
from apps.elections.serializers import PollingAgentAssignmentSerializer


def _get_assignment_or_404(assignment_id):
    try:
        return PollingAgentAssignment.objects.get(id=assignment_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Polling agent assignment not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class PollingAgentAssignmentListCreateView(APIView):
    """
    GET  /api/v1/elections/agents/?election_id=&branch_unit_id=
    POST /api/v1/elections/agents/ - assign an agent to a branch for an
         election. Requires election-management authority over that
         branch (same authority as organizing the election / verifying
         its results).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: PollingAgentAssignmentSerializer(many=True)}, tags=["elections"]
    )
    def get(self, request):
        qs = PollingAgentAssignment.objects.all()
        election_id = request.query_params.get("election_id")
        if election_id:
            qs = qs.filter(election=election_id)
        branch_unit_id = request.query_params.get("branch_unit_id")
        if branch_unit_id:
            qs = qs.filter(branch_unit=branch_unit_id)
        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            PollingAgentAssignmentSerializer(page, many=True).data
        )

    @extend_schema(
        request=PollingAgentAssignmentSerializer,
        responses={201: PollingAgentAssignmentSerializer},
        tags=["elections"],
    )
    def post(self, request):
        serializer = PollingAgentAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branch_unit = serializer.validated_data["branch_unit_id"]

        if not can_manage_election(request.user, branch_unit):
            raise APIError(
                "You do not have authority to assign a polling agent for this branch.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        try:
            assignment = PollingAgentAssignment.objects.create(
                election=serializer.validated_data["election_id"],
                branch_unit=branch_unit,
                agent=serializer.validated_data["agent_id"],
                role=serializer.validated_data["role"],
                assigned_by=request.user,
                notes=serializer.validated_data.get("notes", ""),
            )
        except NotUniqueError as exc:
            raise APIError(
                "This agent is already assigned to this branch for this election.",
                code="conflict",
                http_status=status.HTTP_409_CONFLICT,
            ) from exc

        log_action(
            request.user,
            "elections.agent.assign",
            request=request,
            target=assignment,
            description=f"{assignment.agent.full_name} -> {branch_unit.name}",
        )
        return Response(
            PollingAgentAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class PollingAgentCheckInView(APIView):
    """POST /api/v1/elections/agents/<id>/check-in/ - the assigned agent checks in (self-service)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: PollingAgentAssignmentSerializer},
        tags=["elections"],
    )
    def post(self, request, assignment_id):
        assignment = _get_assignment_or_404(assignment_id)
        if assignment.agent.id != request.user.id and not request.user.is_superadmin:
            raise APIError(
                "Only the assigned agent can check themselves in.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        assignment.check_in()
        if "materials_confirmed" in request.data:
            assignment.materials_confirmed = bool(request.data["materials_confirmed"])
        if "notes" in request.data:
            assignment.notes = request.data["notes"]
        assignment.save()

        log_action(
            request.user, "elections.agent.check_in", request=request, target=assignment
        )
        return Response(PollingAgentAssignmentSerializer(assignment).data)
