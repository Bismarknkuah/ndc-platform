from drf_spectacular.utils import extend_schema
from mongoengine.errors import DoesNotExist, ValidationError as MongoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_action
from apps.core.exceptions import APIError
from apps.core.pagination import paginate_queryset
from apps.elections.documents import Candidate, Election
from apps.elections.permissions import can_manage_election
from apps.elections.serializers import CandidateSerializer, ElectionSerializer


def _get_election_or_404(election_id):
    try:
        return Election.objects.get(id=election_id)
    except (DoesNotExist, MongoValidationError) as exc:
        raise APIError(
            "Election not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
        ) from exc


class ElectionListCreateView(APIView):
    """
    GET  /api/v1/elections/?election_type=&status=&scope_unit_id=
         List elections. Every authenticated member can see elections
         scoped at or above their own unit (so a Branch member can see the
         National General Election they're voting/reporting in).

    POST /api/v1/elections/
         Organize an election: a national general election, an internal
         party election (possibly with multiple contested positions), or
         a poll. Requires "elections.manage" plus authority over
         scope_unit - see apps.elections.permissions.can_manage_election.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ElectionSerializer(many=True)}, tags=["elections"])
    def get(self, request):
        qs = Election.objects.all()

        election_type = request.query_params.get("election_type")
        if election_type:
            qs = qs.filter(election_type=election_type)

        election_status = request.query_params.get("status")
        if election_status:
            qs = qs.filter(status=election_status)

        scope_unit_id = request.query_params.get("scope_unit_id")
        if scope_unit_id:
            qs = qs.filter(scope_unit=scope_unit_id)

        paginator, page = paginate_queryset(qs.order_by("-created_at"), request, self)
        return paginator.get_paginated_response(
            ElectionSerializer(page, many=True).data
        )

    @extend_schema(
        request=ElectionSerializer,
        responses={201: ElectionSerializer},
        tags=["elections"],
    )
    def post(self, request):
        serializer = ElectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scope_unit = serializer.validated_data["scope_unit_id"]

        if not can_manage_election(request.user, scope_unit):
            raise APIError(
                "You do not have authority to organize an election for this scope.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        election = Election.objects.create(
            title=serializer.validated_data["title"],
            description=serializer.validated_data.get("description", ""),
            election_type=serializer.validated_data["election_type"],
            scope_unit=scope_unit,
            organized_by=request.user,
            start_date=serializer.validated_data["start_date"],
            end_date=serializer.validated_data["end_date"],
        )
        log_action(
            request.user,
            "elections.election.create",
            request=request,
            target=election,
            description=f"{election.election_type} '{election.title}' scoped to {scope_unit.name}",
        )
        return Response(
            ElectionSerializer(election).data, status=status.HTTP_201_CREATED
        )


class ElectionDetailView(APIView):
    """GET/PATCH /api/v1/elections/<id>/ - view or update status/dates/title (organizer/authority only for PATCH)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: ElectionSerializer}, tags=["elections"])
    def get(self, request, election_id):
        election = _get_election_or_404(election_id)
        return Response(ElectionSerializer(election).data)

    @extend_schema(
        request=ElectionSerializer,
        responses={200: ElectionSerializer},
        tags=["elections"],
    )
    def patch(self, request, election_id):
        election = _get_election_or_404(election_id)
        if not can_manage_election(request.user, election.scope_unit):
            raise APIError(
                "You do not have authority to modify this election.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )

        new_status = request.data.get("status")
        if new_status in ("OPEN", "COLLATION", "COMPLETED", "CANCELLED"):
            election.status = new_status

        for field in ("title", "description", "start_date", "end_date"):
            if field in request.data:
                setattr(election, field, request.data[field])

        election.save()
        log_action(
            request.user,
            "elections.election.update",
            request=request,
            target=election,
            description=f"status={election.status}",
        )
        return Response(ElectionSerializer(election).data)


class CandidateListCreateView(APIView):
    """GET/POST /api/v1/elections/<election_id>/candidates/?position= - manage candidates/options for an election."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: CandidateSerializer(many=True)}, tags=["elections"])
    def get(self, request, election_id):
        election = _get_election_or_404(election_id)
        qs = Candidate.objects(election=election)
        position = request.query_params.get("position")
        if position:
            qs = qs.filter(position=position)
        return Response(CandidateSerializer(qs, many=True).data)

    @extend_schema(
        request=CandidateSerializer,
        responses={201: CandidateSerializer},
        tags=["elections"],
    )
    def post(self, request, election_id):
        election = _get_election_or_404(election_id)
        if not can_manage_election(request.user, election.scope_unit):
            raise APIError(
                "You do not have authority to manage candidates for this election.",
                code="forbidden",
                http_status=status.HTTP_403_FORBIDDEN,
            )
        serializer = CandidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = Candidate.objects.create(
            election=election,
            name=serializer.validated_data["name"],
            description=serializer.validated_data.get("description", ""),
            position=serializer.validated_data.get("position"),
            party=serializer.validated_data.get("party"),
            display_order=serializer.validated_data.get("display_order", 0),
            photo_base64=serializer.validated_data.get("photo_base64"),
        )
        log_action(
            request.user,
            "elections.candidate.create",
            request=request,
            target=candidate,
            description=f"{candidate.name} for {election.title}",
        )
        return Response(
            CandidateSerializer(candidate).data, status=status.HTTP_201_CREATED
        )
